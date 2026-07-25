# Phase 01 - Missing-Data Completeness: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Only prepare the documented manual verification handoff.

## Primary code path

Modify `src/sector_score_pipeline.py`:

1. Define an ordered `CORE_COMPLETENESS_FIELDS` mapping from output labels to the six existing row keys.
2. Add a finite-number helper or harden `parse_number()` so NaN/infinity cannot count as populated. Do not break compact values such as `1.2B`.
3. In `add_calculated_fields()`, calculate private completeness values once per row. Avoid reparsing the same six fields in `score_sector()`.
4. In `score_sector()`, emit the four public completeness fields and add them to the named schemas.
5. Update `key_reason()` so low coverage produces a compact warning such as `limited data 2/6`; retain the four-reason cap but make the warning take precedence over ordinary metrics.
6. Keep `final_score`, sector rank, and existing five axis values unchanged for the same input. This phase provides context, not a new score.

## CSV migration behavior

`upsert_csv()` reads older rows using their old header. Writing with the expanded `SCORE_FIELDS` should produce blank completeness cells for historical dates that were not recalculated. Do not backfill old dates from today's values. If a historical backfill is later desired, it must calculate completeness from the matching historical daily row.

Ensure:

- Re-running the same `as_of` date updates that date's rows idempotently.
- Existing extra fields are not silently discarded if the repository schema has evolved since this plan was written.
- Column order remains stable and completeness appears near the score/evidence fields, not buried after free-text notes.
- The compact LLM export contains `count`, `total`, `pct`, and `label` so consumers do not have to infer the denominator.

## Documentation changes

Update `README.md` to explain:

- Completeness describes evidence coverage, not score quality.
- `complete` means all six daily fundamental fields were present.
- A sparse high score should be reviewed cautiously.
- Missing values may still use V1's neutral percentile behavior until a later scoring-policy change is explicitly approved.

## Completion deliverables

- Updated scoring field contracts.
- Completeness calculation and labels.
- Additive CSV export support.
- Low-coverage `key_reason` warning.
- README schema/interpretation update.
- Human-facing checklist ready in `03-manual-verification.md`.
