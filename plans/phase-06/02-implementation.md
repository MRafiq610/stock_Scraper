# Phase 06 - Volatility and Risk Measure: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Implement and document; leave execution of manual cases to the reviewer.

## Implementation steps

1. Extend the history index in `src/sector_score_pipeline.py` to retain ordered `(date, close)` observations suitable for close-to-close returns.
2. Add a focused rolling-volatility helper using Python's standard-library statistics/math facilities; avoid adding a heavy dataframe dependency for this calculation alone.
3. Select observations ending at `as_of`, compute returns only between consecutive valid observations, and enforce the minimum count.
4. Add private numeric volatility fields before sector grouping.
5. Compute a sector-relative stability percentile only among eligible sector members.
6. Emit the six documented public fields in `SCORE_FIELDS` and the most useful compact fields in `LLM_FIELDS`.
7. Keep V2 score arithmetic unchanged until a separate human-approved configuration change.
8. Add history depth/unknown counts to the run summary.

## Numerical and compatibility rules

- Use sample standard deviation consistently and document it.
- Guard against duplicate dates, zero/negative closes, non-finite results, and fewer than two returns.
- Do not round intermediate returns or volatility.
- Format only at CSV output.
- Historical `--as-of` runs use only rows dated on/before the target.
- Existing score-history rows remain untouched unless that exact date is recalculated.

## Documentation

Update `README.md` with formula, window, minimum observations, annualization, label meaning, informational-only status, and limitations. If the human later approves score integration, bump the scoring model version and update Phase 02's weight documentation.

## Completion deliverables

- Valid daily-close history handling.
- Rolling volatility and observation coverage.
- Sector-relative stability score/label.
- Additive outputs without rank changes.
- Human verification checklist ready.
