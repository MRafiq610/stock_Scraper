"""
Daily stock data pipeline.

Default behavior:
- skip Saturday/Sunday
- refresh KMIALLSHR symbols
- refresh PSX sector mapping
- fetch Sarmaaya stock details
- build sector-relative score files and LLM summaries
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

import get_stocks
import notifier
import psx_sector_mapper
import sector_score_pipeline
import stock_details_scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily_pipeline")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the complete daily stock pipeline.")
    parser.add_argument("--force", action="store_true", help="run even on Saturday/Sunday")
    parser.add_argument("--skip-symbols", action="store_true", help="do not refresh KMIALLSHR symbols")
    parser.add_argument("--skip-sectors", action="store_true", help="do not refresh PSX sector mapping")
    parser.add_argument("--details-delay", type=float, default=stock_details_scraper.REQUEST_DELAY_SECONDS)
    parser.add_argument("--details-limit", type=int, help="fetch only first N symbols for testing")
    parser.add_argument("--score-lookback-days", type=int, default=30)
    parser.add_argument("--top-per-sector", type=int, default=5)
    parser.add_argument("--simulate-failure", action="store_true", help="raise a test error after weekend check")
    return parser.parse_args()


def is_weekend(today: date) -> bool:
    return today.weekday() >= 5


def main() -> None:
    args = parse_args()
    today = date.today()

    if is_weekend(today) and not args.force:
        message = f"Market closed on weekend ({today.isoformat()}); pipeline skipped."
        log.info(message)
        notifier.send_notification("Stock pipeline skipped", message)
        return

    try:
        if args.simulate_failure:
            raise RuntimeError("simulated pipeline failure for notification testing")

        if not args.skip_symbols:
            log.info("refreshing KMIALLSHR symbols")
            get_stocks.main()

        if not args.skip_sectors:
            log.info("refreshing sector mapping")
            psx_sector_mapper.main()

        log.info("fetching daily stock details")
        details_summary = stock_details_scraper.run(
            delay=args.details_delay,
            limit=args.details_limit,
        )

        log.info("building sector-relative scores and LLM exports")
        score_summary = sector_score_pipeline.run(
            lookback_days=args.score_lookback_days,
            top_per_sector=args.top_per_sector,
        )

        message = "\n".join([
            f"Date: {score_summary['as_of']}",
            f"Fetched: {details_summary['fetched']}/{details_summary['requested']}",
            f"Failed: {details_summary['failed']}",
            f"New rows: {details_summary['new']}",
            f"Updated rows: {details_summary['updated']}",
            f"Scored: {score_summary['scored']}",
            f"Rankings: {score_summary['latest_rankings']}",
            f"Monthly: {score_summary['monthly_file']}",
            f"LLM summary: {score_summary['llm_summary']}",
        ])
        if details_summary["failed_symbols"]:
            message += "\nFailed symbols: " + ", ".join(details_summary["failed_symbols"])
        notifier.send_notification("Stock pipeline success", message)
        log.info("pipeline complete")
    except Exception as e:
        notifier.send_notification("Stock pipeline failed", f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
