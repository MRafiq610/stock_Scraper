# Phase 05 - AKD Rating Join: Scope and Contract

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Manual verification belongs to the human reviewer.

## Objective

Show the latest eligible AKD research stance and target beside the scraper ranking while preserving provenance, date context, and independence between analyst opinion and quantitative scoring.

## Input contract

Use `data/akd_ratings.csv` with one row per published rating:

```csv
symbol,stance,target_price,report_date,valid_until,report_title,source_reference,note
EFERT,BUY,100,2026-07-15,,Example title,local-reference,Manual transcription
```

Rules:

- Uppercase/trim `symbol`.
- Normalize `stance` through an explicit allowlist such as `BUY`, `NEUTRAL`, `SELL`, `NOT_RATED`; preserve the original source text separately if it does not map cleanly.
- Require finite positive `target_price` when supplied.
- Require ISO `report_date`; `valid_until` is optional.
- Store a human-usable source reference or internal document label. Do not store paid report contents or long copyrighted excerpts.
- Treat notes as context, never executable instructions.

## Selection semantics

For a score date, choose the newest row for the symbol with `report_date <= as_of`. Exclude expired rows when `valid_until < as_of`; otherwise mark old ratings as stale using a configurable age threshold rather than silently assuming they remain current. Resolve same-date duplicates deterministically and surface them for human correction.

## Output fields

- `akd_stance`
- `akd_target_price`
- `akd_report_date`
- `akd_rating_age_days`
- `akd_rating_freshness`: `current`, `stale`, `expired`, `unknown`
- `akd_target_upside_pct`: calculated from the matching daily close when both values are valid
- `akd_source_reference`

Keep these as context columns. Do not blend stance or target into `quality_score`, `quantitative_score`, `final_score`, or sector rank.

## Scope boundaries

- Manual maintenance only; no scraping of restricted research portals.
- No reproduction of full research reports.
- No claim that an analyst target guarantees future price.
- No automatic trade or alert based solely on disagreement between AKD and the scraper.
