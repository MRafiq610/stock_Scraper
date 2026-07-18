"""
PSX sector mapper — fetches the full PSX symbol/sector list from
dps.psx.com.pk and joins it against the KMIALLSHR symbols already scraped
into data/kmiallshr_companies.csv, producing
data/kmiallshr_by_sector.csv (columns: sector, symbol, name).

This is a full recompute each run (both sources are small, single-request
lists, not paginated) rather than an incremental append.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

import requests
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("psx_sector_mapper")

PSX_SYMBOLS_URL = "https://dps.psx.com.pk/symbols"
DATA_DIR = Path("data")
KMIALLSHR_CSV = DATA_DIR / "kmiallshr_companies.csv"
OUTPUT_CSV = DATA_DIR / "kmiallshr_by_sector.csv"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Referer": "https://dps.psx.com.pk/sector-summary",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


class PsxSymbol(BaseModel):
    symbol: str
    name: str
    sectorName: str
    isETF: bool = False
    isDebt: bool = False
    isGEM: Optional[bool] = None


def fetch_psx_symbols(session: requests.Session) -> list[PsxSymbol]:
    resp = session.get(PSX_SYMBOLS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    symbols = [PsxSymbol(**row) for row in rows]
    log.info("fetched %d PSX symbols", len(symbols))
    return symbols


def load_kmiallshr_symbols(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run the KMIALLSHR scraper first")
    with path.open(newline="", encoding="utf-8") as f:
        return [row["symbol"] for row in csv.DictReader(f)]


def build_sector_mapping(
    kmiallshr_symbols: list[str], psx_symbols: list[PsxSymbol]
) -> tuple[list[dict], list[str]]:
    """Join KMIALLSHR symbols against PSX sector data. Returns (rows, unmatched)."""
    psx_by_symbol = {s.symbol: s for s in psx_symbols}
    rows = []
    unmatched = []
    for symbol in kmiallshr_symbols:
        psx = psx_by_symbol.get(symbol)
        if psx is None:
            unmatched.append(symbol)
            continue
        rows.append({
            "sector": psx.sectorName or "UNKNOWN",
            "symbol": psx.symbol,
            "name": psx.name,
        })
    rows.sort(key=lambda r: (r["sector"], r["symbol"]))
    return rows, unmatched


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sector", "symbol", "name"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    session = requests.Session()
    kmiallshr_symbols = load_kmiallshr_symbols(KMIALLSHR_CSV)
    log.info("loaded %d KMIALLSHR symbols", len(kmiallshr_symbols))

    psx_symbols = fetch_psx_symbols(session)
    rows, unmatched = build_sector_mapping(kmiallshr_symbols, psx_symbols)

    write_csv(OUTPUT_CSV, rows)
    log.info("wrote %d rows -> %s", len(rows), OUTPUT_CSV)
    if unmatched:
        log.warning("%d KMIALLSHR symbols had no PSX match: %s", len(unmatched), unmatched)


if __name__ == "__main__":
    main()