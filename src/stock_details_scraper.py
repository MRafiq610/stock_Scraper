"""
Stock details scraper - fetches a daily price + fundamentals snapshot for
each KMIALLSHR symbol from Sarmaaya and stores it in
data/stock_details_history.csv (one row per symbol per calendar day).

Re-running on the same day updates that day's rows in place instead of
duplicating them; running on a new day adds a fresh set of rows, building
up a daily history over time.
"""
from __future__ import annotations

import argparse
import csv
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stock_details_scraper")

API_URL_TMPL = "https://beta-restapi.sarmaaya.pk/api/stocks/details/{symbol}"
DATA_DIR = Path("data")
KMIALLSHR_CSV = DATA_DIR / "kmiallshr_companies.csv"
OUTPUT_CSV = DATA_DIR / "stock_details_history.csv"
REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://sarmaaya.pk",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}

METRIC_FIELD_MAP = {
    "FF_PRICE_OPEN": "price_open",
    "FF_PRICE_CLOSE": "price_close",
    "FF_PRICE_HIGH": "price_high",
    "FF_PRICE_LOW": "price_low",
    "FF_PRICE_HIGH_52WK": "high_52wk",
    "FF_PRICE_LOW_52WK": "low_52wk",
    "FF_MKT_CAP": "market_cap",
    "FF_COM_SHS_OUT": "shares_outstanding",
    "FF_SHS_FLOAT": "float_shares",
    "FF_VOLUME_WK_AVG": "weekly_avg_volume",
    "FF_SHS_FLOAT_PERCENT": "free_float_pct",
    "FF_DIV_YLD": "dividend_yield",
    "FF_EPS": "eps",
    "FF_NET_MGN": "net_income_margin",
    "FF_PBK": "price_to_book",
    "FF_PE": "price_to_earnings",
    "FF_PEG": "peg_ratio",
}
FIELDNAMES = ["date", "symbol"] + list(dict.fromkeys(METRIC_FIELD_MAP.values()))
COMPACT_NUMBER_FIELDS = {"market_cap", "shares_outstanding", "float_shares", "weekly_avg_volume"}


def parse_value(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw in ("", "-", "null"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def trim_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def compact_number(value: float) -> str:
    units = ((1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K"))
    for threshold, suffix in units:
        if abs(value) >= threshold:
            return trim_number(value / threshold) + suffix
    return trim_number(value)


def format_value(field: str, raw: Any) -> Optional[str]:
    value = parse_value(raw)
    if value is None:
        return None
    if field in COMPACT_NUMBER_FIELDS:
        return compact_number(value)
    return trim_number(value)


def normalize_response(payload: Any) -> list[dict]:
    response = payload.get("response", []) if isinstance(payload, dict) else []
    if isinstance(response, dict):
        response = response.get("data", [])
    if not isinstance(response, list):
        return []
    return [row for row in response if isinstance(row, dict)]


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def metric_sort_key(row: dict) -> tuple[int, int, str]:
    end_date = str(row.get("afFiscalEndDate") or "")
    if end_date == "null":
        end_date = ""
    return (int_or_zero(row.get("afFiscalYear")), int_or_zero(row.get("afFiscalPeriod")), end_date)


def fetch_stock_details(symbol: str, as_of: str) -> dict:
    """Fetch one symbol's latest details snapshot."""
    url = API_URL_TMPL.format(symbol=symbol)
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            rows = normalize_response(resp.json())
            break
        except Exception as e:
            last_error = e
            if attempt == MAX_RETRIES:
                raise
            sleep_for = attempt * 2
            log.info("retrying %s after %s (%d/%d)", symbol, e, attempt, MAX_RETRIES)
            time.sleep(sleep_for)
    else:
        raise RuntimeError(f"failed to fetch {symbol}") from last_error

    latest: dict[str, tuple[tuple[int, int, str], Optional[str]]] = {}
    for metric in rows:
        field = METRIC_FIELD_MAP.get(str(metric.get("metricMetric", "")))
        if field is None:
            continue

        sort_key = metric_sort_key(metric)
        current = latest.get(field)
        if current is None or sort_key >= current[0]:
            latest[field] = (sort_key, format_value(field, metric.get("afValue")))

    row: dict = {"date": as_of, "symbol": symbol}
    for field in METRIC_FIELD_MAP.values():
        row[field] = None
    for field, (_, value) in latest.items():
        row[field] = value
    return row


def load_symbols(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run the KMIALLSHR scraper first")
    with path.open(newline="", encoding="utf-8") as f:
        return [r["symbol"] for r in csv.DictReader(f)]


def load_existing(path: Path) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {(r["date"], r["symbol"]): r for r in csv.DictReader(f)}


def upsert(path: Path, new_rows: list[dict]) -> tuple[int, int]:
    """Merge today's rows into the history file, keyed on (date, symbol)."""
    existing = load_existing(path)
    added = updated = 0
    for row in new_rows:
        key = (row["date"], row["symbol"])
        str_row = {k: ("" if v is None else str(v)) for k, v in row.items()}
        if key not in existing:
            added += 1
        elif existing[key] != str_row:
            updated += 1
        existing[key] = str_row

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return added, updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Sarmaaya stock detail snapshots.")
    parser.add_argument("--limit", type=int, help="fetch only the first N symbols for a quick test")
    parser.add_argument("--symbol", action="append", help="fetch one symbol; can be passed multiple times")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SECONDS, help="seconds between requests")
    return parser.parse_args()


def run(delay: float = REQUEST_DELAY_SECONDS, limit: Optional[int] = None, symbols_filter: Optional[list[str]] = None) -> dict:
    symbols = load_symbols(KMIALLSHR_CSV)

    if symbols_filter:
        requested = {symbol.upper() for symbol in symbols_filter}
        symbols = [symbol for symbol in symbols if symbol.upper() in requested]
        missing = sorted(requested - {symbol.upper() for symbol in symbols})
        if missing:
            log.warning("requested symbols not found in %s: %s", KMIALLSHR_CSV, missing)

    if limit is not None:
        symbols = symbols[:limit]

    today = date.today().isoformat()
    log.info("fetching details for %d symbols (as_of=%s)", len(symbols), today)

    rows, failed = [], []
    for i, symbol in enumerate(symbols, 1):
        log.info("fetching %s (%d/%d)", symbol, i, len(symbols))
        try:
            rows.append(fetch_stock_details(symbol, today))
        except Exception as e:
            log.warning("failed to fetch %s: %s", symbol, e)
            failed.append(symbol)
        if i < len(symbols) and delay > 0:
            time.sleep(delay)

    added, updated = upsert(OUTPUT_CSV, rows)
    log.info("done: %d fetched, %d new, %d updated -> %s", len(rows), added, updated, OUTPUT_CSV)
    if failed:
        log.warning("%d symbols failed: %s", len(failed), failed)
    return {
        "requested": len(symbols),
        "fetched": len(rows),
        "failed": len(failed),
        "new": added,
        "updated": updated,
        "failed_symbols": failed,
        "output": str(OUTPUT_CSV),
    }


def main() -> None:
    args = parse_args()
    run(delay=args.delay, limit=args.limit, symbols_filter=args.symbol)


if __name__ == "__main__":
    main()
