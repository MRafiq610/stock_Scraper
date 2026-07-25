# Phase 07 - Sector-Size Confidence: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are exclusively for that reviewer. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Manual checks

- [ ] Inspect sectors with counts 3, 5, 14, and 15 (or disposable copied data representing them).
- [ ] Confirm boundaries produce low, moderate, moderate, and high respectively.
- [ ] Confirm `sector_count` remains the number of scored daily rows.
- [ ] Confirm confidence appears beside sector count in full and LLM outputs.
- [ ] Confirm low-confidence wording is prominent but does not claim the stock itself is low quality.
- [ ] Confirm sparse metric peer counts are not misrepresented as equal to sector count.
- [ ] Confirm the `UNKNOWN` sector remains identifiable.
- [ ] Compare pre/post outputs and confirm scores and ranks are unchanged.
- [ ] Re-run the same date and confirm no history duplicates.
- [ ] Confirm README boundaries do not contain the roadmap's original overlap at 15.

## Human acceptance

Approve only when the boundary behavior and non-scoring presentation are correct. Then ask the AI agent to use the completion rename in `../instructions.md`.
