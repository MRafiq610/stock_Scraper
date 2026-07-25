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
import uuid
from datetime import date, datetime
from pathlib import Path

import get_stocks
import notifier
import psx_sector_mapper
import sector_score_pipeline
import stock_details_scraper
from safe_io import atomic_write_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily_pipeline")
MANIFEST_PATH = Path("data/manifests/latest_pipeline_run.json")


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_manifest(
    run_id: str,
    started_at: str,
    status: str,
    details: dict | None = None,
    scores: dict | None = None,
    error_type: str = "",
) -> None:
    warnings = list((scores or {}).get("warnings", []))
    if details and details.get("failed"):
        warnings.insert(
            0,
            f"daily details failed for {details['failed']}/{details['requested']} symbols",
        )
    atomic_write_json(
        MANIFEST_PATH,
        {
            "run_id": run_id,
            "status": status,
            "started_at": started_at,
            "finished_at": timestamp(),
            "scoring_as_of": (scores or {}).get("as_of", ""),
            "scoring_model_version": (scores or {}).get(
                "scoring_model_version", ""
            ),
            "sources": {
                "daily_fetch": {
                    key: details.get(key)
                    for key in ("requested", "fetched", "failed", "new", "updated")
                } if details else {},
                **(scores or {}).get("sources", {}),
            },
            "outputs": [
                {
                    "path": (scores or {}).get("latest_rankings", ""),
                    "rows": (scores or {}).get("latest_rows", 0),
                },
                {
                    "path": (scores or {}).get("monthly_file", ""),
                    "rows": (scores or {}).get("monthly_rows", 0),
                },
                {
                    "path": (scores or {}).get("llm_summary", ""),
                    "rows": (scores or {}).get("llm_rows", 0),
                },
            ] if scores else [],
            "warnings": warnings,
            "error_type": error_type,
        },
    )


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
    run_id = uuid.uuid4().hex
    started_at = timestamp()

    if is_weekend(today) and not args.force:
        message = f"Market closed on weekend ({today.isoformat()}); pipeline skipped."
        log.info(message)
        write_manifest(run_id, started_at, "skipped")
        notifier.send_notification("Stock pipeline skipped", message)
        return

    details_summary = None
    score_summary = None
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
        if not details_summary["fetched"]:
            raise RuntimeError("daily details fetch returned no usable rows")

        log.info("building sector-relative scores and LLM exports")
        score_summary = sector_score_pipeline.run(
            lookback_days=args.score_lookback_days,
            top_per_sector=args.top_per_sector,
        )
        write_manifest(
            run_id,
            started_at,
            "success_with_warnings" if (
                details_summary["failed"] or score_summary["warnings"]
            ) else "success",
            details_summary,
            score_summary,
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
            f"Manifest: {MANIFEST_PATH}",
        ])
        if details_summary["failed_symbols"]:
            message += "\nFailed symbols: " + ", ".join(details_summary["failed_symbols"])
        if score_summary["warnings"]:
            message += "\nWarnings: " + "; ".join(score_summary["warnings"])
        notifier.send_notification("Stock pipeline success", message)
        log.info("pipeline complete")
    except Exception as e:
        try:
            write_manifest(
                run_id,
                started_at,
                "failed",
                details_summary,
                score_summary,
                type(e).__name__,
            )
        except Exception:
            log.exception("failed to write pipeline manifest")
        notifier.send_notification("Stock pipeline failed", f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
