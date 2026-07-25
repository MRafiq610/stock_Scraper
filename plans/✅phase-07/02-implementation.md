# Phase 07 - Sector-Size Confidence: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Prepare the phase for human inspection only.

## Implementation steps

1. Add named threshold constants in the scoring policy/configuration area.
2. Add a pure label helper that receives an integer count and returns the documented label; invalid/non-positive counts should fail clearly or return `unknown` before export.
3. Populate confidence once per sector result alongside the existing `sector_count`.
4. Add `sector_confidence` to `SCORE_FIELDS` and `LLM_FIELDS`; add a short note to the compact summary if token budget remains reasonable.
5. Update `key_reason()` only if needed to prioritize a low-confidence warning. Do not crowd out Phase 01's limited-data warning; combine compactly when both apply.
6. Update `README.md` with exact boundaries and the distinction between sector count and metric peer count.

## Backward compatibility

- This is additive and must not change scoring arithmetic or rank order.
- Recalculated dates receive confidence labels; old history rows remain blank unless correctly recomputed.
- Preserve stable schema ordering beside `sector_count`.
- Ensure sectors named `UNKNOWN` receive the same count rules but also retain their existing mapping limitation.

## Completion deliverables

- Validated thresholds and label helper.
- Confidence fields in full and LLM outputs.
- Low-confidence explanatory context.
- No score/rank changes.
- README update and manual checklist.
