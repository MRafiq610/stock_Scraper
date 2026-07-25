# Phase 03 - Quarterly Fundamentals and Quality Axis: Scoring Integration

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Prepare the quality-axis manual cases but do not execute them.

## As-of lookup

Add a dedicated `quarterly_lookup(rows, as_of)` pattern in `src/sector_score_pipeline.py`. It should:

- normalize symbols;
- exclude rows unavailable after `as_of`;
- choose the latest eligible row per symbol deterministically;
- expose the chosen fiscal period, fiscal end, availability date, and age in days;
- return no row rather than a synthetic neutral row when a symbol has no eligible filing.

Read `data/quarterly_ratios_history.csv` as an optional input. The latest snapshot is for inspection and current quick lookup only; do not use it for historical `--as-of` scoring.

## Initial quality metrics

Use these approved directions when valid source fields exist:

| Metric | Direction |
| --- | --- |
| Debt-to-equity | Lower is better |
| ROE | Higher is better |
| Current ratio | Higher is better |
| Revenue/sales growth | Higher is better |
| PAT/net-profit growth | Higher is better |

Calculate percentiles within the stock's sector, as V1 does for other axes. Do not compare banks and industrial-company balance-sheet ratios blindly. If a metric is structurally non-comparable for a sector, define an explicit sector applicability rule and document it; do not quietly penalize the sector.

For each row:

- Compute a metric percentile only when the row has a valid value and the sector has at least two valid comparable observations for that metric.
- Average only the eligible metric percentiles.
- Set `quality_score` blank/`None` when no quality metric is eligible.
- Record `quality_metric_count`, `quality_metric_total`, `quality_completeness_pct`, selected fiscal period, and quarterly age.
- Feed `quality_score` into Phase 02's available-axis weighted helper. When absent, remaining axis weights renormalize automatically.

Avoid mechanical caps unless approved from domain evidence. In particular, negative equity can make debt-to-equity misleading; flag it as non-comparable/needs review rather than treating the numerical ratio as excellent.

## Growth semantics

Prefer source-provided like-for-like year-over-year growth. If growth must be calculated from P&L:

- compare the same fiscal period against the prior year;
- never compare cumulative 9M values against a standalone quarter;
- retain the raw numerator/denominator fields;
- leave growth missing when the comparison period is unavailable or the base is unsuitable.

## Output additions

Add to full ranking/history and relevant LLM output:

- `quality_score`
- `quality_metric_count`
- `quality_metric_total`
- `quality_completeness_pct`
- `quarterly_fiscal_period`
- `quarterly_fiscal_end_date`
- `quarterly_available_date`
- `quarterly_age_days`
- selected raw quality metrics needed to explain the score

Update `key_reason()` to surface strong/weak quality evidence only when coverage is sufficient, and keep Phase 01's limited-data warning prominent.

## Historical integrity

Do not overwrite older rows with today's newly published filing unless explicitly recalculating that older date under the documented as-of availability rules. Record `scoring_model_version` so Phase 02-only and Phase 03-integrated outputs remain distinguishable.
