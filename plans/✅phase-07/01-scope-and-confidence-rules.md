# Phase 07 - Sector-Size Confidence: Scope and Rules

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The reviewer will execute `03-manual-verification.md`.

## Objective

Make the statistical limitation of small sector peer groups explicit without altering scores or ranks.

## Confidence contract

Resolve the roadmap's overlapping boundary with these unambiguous defaults:

- `low`: fewer than 5 scored sector members.
- `moderate`: 5 through 14 scored sector members.
- `high`: 15 or more scored sector members.

Expose:

- `sector_count`: existing number of stocks scored in the sector for the as-of run.
- `sector_confidence`: `low`, `moderate`, or `high`.
- `sector_confidence_note`: compact explanatory text, primarily for the LLM summary.

Define constants once, validate their ordering, and make labels a presentation/evidence property. Do not boost or penalize `final_score`.

## Count meaning

The existing `sector_count = len(rows)` counts daily rows entering `score_sector()`, including stocks with sparse metrics. Preserve this for compatibility, but document it as "scored members," not total exchange listings or valid observations for every metric.

Where useful, also expose metric-specific peer counts introduced by later phases. Do not imply that a high sector count guarantees every percentile used all those peers.

## Scope boundaries

- No minimum-sector exclusion.
- No score shrinkage toward 50.
- No cross-sector comparison fallback.
- No claim of statistical significance.
- No hidden threshold changes based on sector name.
