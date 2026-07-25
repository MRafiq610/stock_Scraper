# Phase 02 - Configurable Scoring Weights: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are exclusively for that reviewer. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Manual checks

- [ ] Inspect `src/scoring_config.py` and confirm the six weights match the approved table and total 1.0.
- [ ] Run scoring for a known as-of date and manually recompute at least one stock's quantitative score using the five currently available axes and a 0.90 denominator.
- [ ] Confirm the result emphasizes valuation/income more and trend less than V1.
- [ ] Confirm `quality` is absent, not neutral `50`, before Phase 03.
- [ ] Confirm a numeric axis score of `0` participates rather than being treated as missing.
- [ ] Temporarily use an invalid copied configuration and confirm the command fails with a clear configuration message; restore the approved configuration afterward.
- [ ] Confirm no-news rows equal their quantitative score.
- [ ] Confirm a valid news row still uses the documented 85/15 overlay.
- [ ] Confirm model version and active-axis coverage appear in full and LLM outputs.
- [ ] Re-run the same as-of date and confirm score-history keys are not duplicated.
- [ ] Confirm old historical rows were not relabeled as V2 without being recalculated.

## Human acceptance

Approve only after arithmetic, metadata, and backward compatibility are visibly correct. Then ask the AI agent to apply the completed-folder rename described in `../instructions.md`.
