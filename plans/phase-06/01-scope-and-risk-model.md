# Phase 06 - Volatility and Risk Measure: Scope and Model

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The history gate and checklist must be reviewed manually.

## Objective

Distinguish a steady price path from a volatile one by adding a reproducible rolling risk measure from existing daily close history.

## History-depth gate

Do not implement or enable score integration until representative symbols have enough valid daily closes. Default model:

- Window: latest 30 valid trading observations on or before `as_of`.
- Minimum observations: 20 valid close-to-close returns.
- Return: `(close_t / close_t-1) - 1`.
- Volatility: sample standard deviation of those daily returns.
- Display: daily percent and, optionally, annualized percent using `sqrt(252)`.

Calendar days are not trading observations. Sort by date, deduplicate `(date, symbol)`, require positive closes, and never bridge a missing/invalid close as if it were a zero return.

## Risk score

Within each sector, percentile-rank volatility with lower being better only when at least two members have eligible values. Add:

- `volatility_daily_pct`
- `volatility_annualized_pct`
- `volatility_observations`
- `volatility_window`
- `volatility_score` (higher means more stable)
- `volatility_label`: `low`, `moderate`, `high`, or `unknown`

Labels should be percentile-relative or based on documented constants, not intuitive arbitrary cutoffs hidden in code.

## Score integration decision

First release the measure as informational. Do not change `final_score` in the same change unless the human explicitly approves an integration rule after reviewing real output. If approved later, prefer combining stability with the existing trend axis or adding a named risk axis through Phase 02's normalized configuration—never subtract raw volatility directly from a 0-100 score.

## Scope boundaries

- Price volatility is not total investment risk.
- Do not infer beta, drawdown, liquidity risk, or fundamental risk from this measure.
- Do not backfill missing market days.
- Do not calculate using future closes.
