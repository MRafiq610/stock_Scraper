"""
KMIALLSHR company names scraper — fetches Shariah index constituents from
Sarmaaya and upserts their symbols into data/kmiallshr_companies.csv.

Checkpointing: existing symbols are loaded first; only new symbols get
appended on each run, so re-running doesn't recreate the file or duplicate rows.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import requests
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kmiallshr_scraper")

API_URL = "https://beta-restapi.sarmaaya.pk/api/indices/KMIALLSHR/companies"
DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "kmiallshr_companies.csv"
PAGE_LIMIT = 100

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


class Company(BaseModel):
    symbol: str


def fetch_all_symbols(session: requests.Session) -> list[str]:
    """Paginate through the companies endpoint until a short page is hit."""
    symbols: list[str] = []
    page = 1
    while True:
        resp = session.get(
            API_URL,
            headers=HEADERS,
            params={"page": page, "limit": PAGE_LIMIT},
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("response", {}).get("data", [])
        if not rows:
            break
        symbols.extend(Company(**row).symbol for row in rows)
        log.info("page %d: +%d symbols", page, len(rows))
        if len(rows) < PAGE_LIMIT:
            break
        page += 1
    return symbols


def load_existing(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return set()
        if "symbol" not in reader.fieldnames:
            raise ValueError(
                f"invalid CSV header in {path}: expected a 'symbol' column, "
                f"found {reader.fieldnames}"
            )
        return {
            symbol
            for row in reader
            if (symbol := (row.get("symbol") or "").strip())
        }


def upsert(path: Path, symbols: list[str]) -> int:
    """Append any symbols not already in the CSV. Returns count added."""
    existing = load_existing(path)
    new_symbols = sorted(set(symbols) - existing)
    if not new_symbols:
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["symbol"])
        writer.writerows([s] for s in new_symbols)

    return len(new_symbols)


def main() -> None:
    session = requests.Session()
    symbols = fetch_all_symbols(session)
    if not symbols:
        log.warning("no symbols fetched (empty response) — leaving existing CSV untouched")
        return
    added = upsert(CSV_PATH, symbols)
    log.info("done: %d fetched, %d new -> %s", len(symbols), added, CSV_PATH)


if __name__ == "__main__":
    main()
