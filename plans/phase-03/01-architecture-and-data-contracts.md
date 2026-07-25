# Phase 03 - Quarterly Fundamentals and Quality Axis: Architecture

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Prepare the checks in `04-manual-verification.md` and leave execution to the human reviewer.

## Objective

Add filing-based fundamentals on their natural cadence and join them into daily sector scoring without future-data leakage. Keep retrieval, normalized storage, latest-snapshot export, and scoring responsibilities separate.

## Required components

- `src/quarterly_fundamentals_scraper.py`: fetch, parse, checkpoint/upsert, and export.
- `data/quarterly_ratios_history.csv`: normalized ratio observations.
- `data/quarterly_pnl_history.csv`: normalized raw P&L observations.
- `data/latest_quarterly_ratios.csv`: most recent known ratio row per symbol for inspection; historical scoring must use history rather than blindly reading this file.
- `src/sector_score_pipeline.py`: as-of quarterly lookup and quality axis.
- A monthly scheduled entry point, separate from the weekday daily scraper.

## Source discovery gate

The PDF does not provide a stable endpoint or exact source field codes. Before writing the scraper:

1. Inspect the existing `api.txt`, `api2.txt`, browser/API behavior, and any approved Sarmaaya-style ratio source.
2. Record endpoint/method, response envelope, authentication requirements, rate limits, metric identifiers, fiscal-period fields, units, null markers, and pagination.
3. Save only a small redacted example in documentation if needed; do not commit credentials, cookies, or huge raw responses.
4. If the source contract cannot distinguish fiscal period or publication availability, stop and request human review. Do not infer quarters from array order.

## Normalized identity and dates

At minimum, each normalized row needs:

- `symbol`
- `fiscal_year`
- `fiscal_period` (source value such as `Q1`, `HY`, `9M`, `FY`; do not falsely label cumulative periods as standalone quarters)
- `fiscal_end_date`
- `available_date` (filing/publication date when known)
- `scraped_at`
- `source`

Use `(symbol, fiscal_year, fiscal_period, fiscal_end_date)` as the business key. If the source republishes a restatement for that key, update the normalized row and retain traceable `scraped_at`; do not append identical duplicates. If the source exposes a stable filing/revision ID, store it.

## Metric families

Ratios should cover, when the source supplies them:

- Per-share: EPS, DPS, book value per share.
- Valuation: P/E, P/B, PEG or source equivalents.
- Margins/returns: gross/operating/net margin, ROA, ROE.
- Health: debt-to-equity, current ratio, quick ratio or close equivalents.
- Growth: sales/revenue growth, operating-profit growth, PAT/net-profit growth, EPS growth.

P&L should cover source-native values for net sales/revenue, cost of sales, gross profit, operating profit, financial charges, profit before tax, tax, profit after tax, EPS, and DPS. Preserve units/currency metadata and never combine percentages with ratios or rupee values.

## As-of rule

For a score dated `D`, select the latest row for the symbol where:

- `available_date <= D`, when a reliable availability date exists; otherwise
- `scraped_at` date `<= D`, with an explicit lower-confidence provenance flag.

Then order by fiscal end and period. Never use a later filing merely because `latest_quarterly_ratios.csv` contains it today.
