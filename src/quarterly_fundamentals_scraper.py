"""Manually refresh AskAnalyst quarterly results and ratios."""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import math
import re
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path("data")
SYMBOLS_CSV = DATA_DIR / "kmiallshr_companies.csv"
RESULTS_JSON = DATA_DIR / "quarterly_results.json"
RATIOS_JSON = DATA_DIR / "quarterly_ratios.json"
SYMBOL_RE = re.compile(r"^[A-Z0-9]+$")

DATASETS = {
    "results": {
        "url": "https://api.askanalyst.com.pk/api/result/{}",
        "path": RESULTS_JSON,
    },
    "ratios": {
        "url": "https://api.askanalyst.com.pk/api/rationew",
        "path": RATIOS_JSON,
    },
}

QUALITY_METRICS = {
    "debt_to_equity": (("Health", "Debt To Equity"),),
    "roe": (("Returns", "ROE"), ("Profitability", "ROE")),
    "current_ratio": (("Active Ratios", "Current Ratio"),),
    "revenue_growth": (("Growth", "Revenue Growth"), ("Profitability", "Revenue Growth")),
    "net_profit_growth": (("Growth", "Net Profit Growth"), ("Profitability", "PAT Growth")),
}


def read_symbols(path: Path = SYMBOLS_CSV) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        symbols = [row["symbol"].strip().upper() for row in csv.DictReader(file)]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("symbol source must contain unique symbols")
    invalid = [symbol for symbol in symbols if not SYMBOL_RE.fullmatch(symbol)]
    if invalid:
        raise ValueError(f"invalid symbols: {', '.join(invalid)}")
    return symbols


def valid_rows(rows: object) -> bool:
    return (
        isinstance(rows, list)
        and bool(rows)
        and all(
            isinstance(row, dict)
            and isinstance(row.get("label"), str)
            and isinstance(row.get("data"), list)
            for row in rows
        )
    )


def valid_data(data: object, dataset: str) -> bool:
    if dataset == "results":
        return valid_rows(data)
    return (
        isinstance(data, dict)
        and bool(data)
        and all(isinstance(section, str) and valid_rows(rows) for section, rows in data.items())
    )


def read_store(path: Path, dataset: str) -> dict[str, dict]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")

    fallback_scraped_at = datetime.fromtimestamp(
        path.stat().st_mtime,
        timezone.utc,
    ).isoformat()
    store = {}
    for symbol, value in raw.items():
        if symbol == "_meta":
            continue
        record = value if isinstance(value, dict) and "data" in value else {
            "scraped_at": fallback_scraped_at,
            "data": value,
        }
        symbol = symbol.strip().upper()
        if SYMBOL_RE.fullmatch(symbol) and valid_data(record.get("data"), dataset):
            store[symbol] = record
    return store


def write_store(path: Path, dataset: str, store: dict[str, dict], run_summary: dict) -> None:
    output = {
        "_meta": {
            "dataset": dataset,
            "source": DATASETS[dataset]["url"],
            **run_summary,
        },
        **{symbol: store[symbol] for symbol in sorted(store)},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def fetch(symbol: str, dataset: str, retries: int, timeout: int) -> object:
    config = DATASETS[dataset]
    body = None
    headers = {"Accept": "application/json", "User-Agent": "stock-scraper/quarterly"}
    if dataset == "ratios":
        body = json.dumps({"company_id": symbol, "period": "quarter"}).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(config["url"].format(symbol), data=body, headers=headers)

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            if not valid_data(data, dataset):
                raise ValueError(f"API returned no {dataset} data")
            return data
        except (OSError, ValueError, json.JSONDecodeError) as error:
            if attempt == retries:
                raise RuntimeError(str(error)) from error
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def scrape_dataset(
    dataset: str,
    symbols: list[str],
    retries: int,
    timeout: int,
    delay: float,
) -> dict:
    path = DATASETS[dataset]["path"]
    store = read_store(path, dataset)
    unavailable = {}
    updated = 0

    for number, symbol in enumerate(symbols, 1):
        try:
            data = fetch(symbol, dataset, retries, timeout)
            store[symbol] = {
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            updated += 1
            print(f"[{number:03}/{len(symbols)}] {dataset} {symbol}: updated")
        except RuntimeError as error:
            unavailable[symbol] = str(error)
            print(f"[{number:03}/{len(symbols)}] {dataset} {symbol}: unavailable")
        if delay and number < len(symbols):
            time.sleep(delay)

    write_store(
        path,
        dataset,
        store,
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "requested": len(symbols),
            "updated": updated,
            "unavailable": unavailable,
            "symbol_count": len(store),
        },
    )
    return {
        "dataset": dataset,
        "requested": len(symbols),
        "updated": updated,
        "unavailable": len(unavailable),
        "saved": len(store),
        "path": str(path),
    }


def parse_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "null", "N/A"}:
        return None
    try:
        parsed = float(text)
        return parsed if math.isfinite(parsed) else None
    except ValueError:
        return None


def period_end(value: str) -> Optional[date]:
    try:
        parsed = datetime.strptime(value, "%b-%y")
    except (TypeError, ValueError):
        return None
    return date(parsed.year, parsed.month, calendar.monthrange(parsed.year, parsed.month)[1])


def quality_periods(payload: dict) -> list[dict]:
    periods: dict[str, dict] = {}
    for metric, candidates in QUALITY_METRICS.items():
        for section, label in candidates:
            row = next(
                (
                    item
                    for item in payload.get(section, [])
                    if item.get("label") == label
                ),
                None,
            )
            if not row:
                continue
            for point in row["data"]:
                fiscal_end = period_end(point.get("year"))
                value = parse_value(point.get("value"))
                if fiscal_end and value is not None:
                    periods.setdefault(
                        point["year"],
                        {
                            "fiscal_period": point["year"],
                            "fiscal_end_date": fiscal_end.isoformat(),
                        },
                    ).setdefault(metric, value)
            break
    return sorted(periods.values(), key=lambda row: row["fiscal_end_date"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manually refresh quarterly fundamentals.")
    parser.add_argument("--dataset", choices=["all", *DATASETS], default="all")
    parser.add_argument("--symbol", action="append", help="refresh one symbol; repeatable")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="try all 290 symbols instead of only currently supported symbols",
    )
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay", type=float, default=0.1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = list(DATASETS) if args.dataset == "all" else [args.dataset]
    requested = None
    if args.symbol:
        requested = list(dict.fromkeys(symbol.strip().upper() for symbol in args.symbol))
        invalid = [symbol for symbol in requested if not SYMBOL_RE.fullmatch(symbol)]
        if invalid:
            raise ValueError(f"invalid symbols: {', '.join(invalid)}")

    summaries = []
    for dataset in selected:
        existing = read_store(DATASETS[dataset]["path"], dataset)
        symbols = requested or (read_symbols() if args.discover or not existing else sorted(existing))
        summaries.append(
            scrape_dataset(dataset, symbols, args.retries, args.timeout, args.delay)
        )

    for summary in summaries:
        print(
            f"{summary['dataset']}: updated {summary['updated']}/"
            f"{summary['requested']}, unavailable {summary['unavailable']}, "
            f"saved {summary['saved']} -> {summary['path']}"
        )
    return int(
        any(summary["unavailable"] > summary["requested"] / 2 for summary in summaries)
    )


if __name__ == "__main__":
    raise SystemExit(main())
