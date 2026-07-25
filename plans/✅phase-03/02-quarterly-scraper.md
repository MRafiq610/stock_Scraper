# Phase 03 - Quarterly Fundamentals and Quality Axis: Scraper

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The implementation agent must not perform the live manual cases listed later.

## Fetch and parse design

Follow the proven shape of `src/stock_details_scraper.py`, but do not duplicate parsing utilities unnecessarily:

1. Load uppercase symbols from `data/kmiallshr_companies.csv`.
2. Use a shared `requests.Session`, explicit timeout, bounded retry with backoff, descriptive user agent, and respectful configurable delay.
3. Support `--symbol` (repeatable), `--limit`, `--delay`, and an inspection-friendly dry fetch mode that prints metadata rather than sensitive/full payloads.
4. Fetch both ratio and P&L tables for one symbol in the same symbol pass.
5. Normalize source labels through explicit mapping dictionaries. Unknown metric labels must be logged and skipped/preserved for review; never shift values into the wrong field by position.
6. Parse parentheses as negative only if the source contract confirms accounting formatting. Keep missing distinct from zero.
7. Return per-symbol failures without discarding successful symbols, then exit/report clearly if failure rate exceeds an approved threshold.

## Persistence rules

- Read existing files before fetching so known latest fiscal periods can guide no-op behavior.
- A monthly run may still make a lightweight request to discover whether a new filing exists; skip full processing when the newest business key and values are unchanged.
- Upsert history by the documented business key with deterministic sort order.
- Write ratios and P&L independently so failure in one table cannot corrupt the other.
- Prefer atomic replacement: write a sibling temporary file, flush/close it, then replace the destination.
- Build `latest_quarterly_ratios.csv` deterministically from normalized history after successful persistence.
- Never erase an existing non-empty output because a source returns an empty or malformed response.

## CLI and cadence

The module should be runnable directly, for example:

```powershell
uv run src/quarterly_fundamentals_scraper.py
uv run src/quarterly_fundamentals_scraper.py --symbol EFERT --delay 0
```

Add a separate monthly GitHub Actions workflow (recommended: the first day of each month) or a distinct monthly job. It must:

- allow manual dispatch and symbol/limit inputs;
- use the same Python setup conventions as the daily job;
- upload quarterly data artifacts;
- commit only successful normalized data changes;
- reuse failure notification behavior without exposing response payloads.

Do not add the quarterly scraper to every daily run. The daily scoring pipeline may consume the latest eligible stored quarterly data.

## Required run summary

Return/log requested symbols, successful symbols, failed symbols, new ratio rows, updated/restated ratio rows, new P&L rows, latest-file row count, and output paths. Keep logs concise and free of credentials.

## Documentation

Update `README.md` with commands, cadence, all output schemas, source caveats, fiscal-period semantics, and how a no-op run is identified.
