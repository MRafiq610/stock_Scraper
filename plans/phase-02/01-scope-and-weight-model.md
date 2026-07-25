# Phase 02 - Configurable Scoring Weights: Scope and Model

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The agent prepares, but does not execute, `03-manual-verification.md`.

## Objective

Shift the quantitative screen toward undervaluation and dividend income, move scoring policy out of inline arithmetic, and safely support the quality axis that arrives in Phase 03.

## Canonical V2 axis weights

Use one named configuration object:

| Axis | Base weight |
| --- | ---: |
| Valuation | 0.25 |
| Profitability | 0.20 |
| Income | 0.20 |
| Trend | 0.15 |
| Liquidity | 0.10 |
| Quality | 0.10 |

The configured base weights must be finite, non-negative, and sum to 1.0 within a small tolerance. Fail fast with a clear error when the configuration is invalid.

## Available-axis normalization

Before Phase 03, `quality_score` is unavailable. Calculate the quantitative result as a weighted mean over available axes:

```text
sum(axis_score * base_weight for available axes)
------------------------------------------------
sum(base_weight for available axes)
```

This avoids treating an unavailable quality axis as 50 or silently reducing the score to a 0-90 range. Once Phase 03 provides per-stock quality, apply the same rule per row: include quality only when eligible quarterly evidence exists. This behavior must be centralized in a reusable weighted-score helper.

The optional news blend remains outside the quantitative axis weights: use the existing 85% quantitative / 15% news behavior when valid news exists, and 100% quantitative otherwise.

## Configuration location

Prefer a small Python configuration module such as `src/scoring_config.py` because the project has no general configuration dependency. It should contain policy constants only; scoring functions remain in `sector_score_pipeline.py`. Do not add YAML/TOML parsing merely for six values.

## In scope

- Named V2 axis weights.
- Configuration validation.
- Available-axis normalization.
- Explicit score-policy/version label in outputs, such as `v2_value_income`.
- README explanation of weights and missing-axis behavior.

## Out of scope

- Creating the quality axis (Phase 03).
- Changing percentile formulas or metric composition inside each existing axis.
- Volatility integration (Phase 06).
- Tuning weights from historical performance or claiming the weights are optimal.
