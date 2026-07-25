# Phase 01 - Missing-Data Completeness: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are for that reviewer to perform manually. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Human setup

Use disposable copies of the input/output CSV files or a temporary branch so production history is not damaged. Select:

- One stock with all six core fields.
- One stock with three to five core fields.
- One stock with fewer than three core fields.
- One field containing zero or a negative numeric value.
- One truly invalid/missing value.

## Manual checks

- [ ] Run the scoring command for a known `--as-of` date.
- [ ] Confirm the complete row reports `6`, `6`, `100`, and `complete`.
- [ ] Confirm partial and low rows use the documented boundaries.
- [ ] Confirm numeric zero/negative counts as populated while blank/invalid does not.
- [ ] Confirm `data_completeness_*` appears in score history, latest ranking, monthly output, and LLM summary.
- [ ] Confirm a low-completeness row includes a prominent limited-data reason.
- [ ] Compare scores and ranks with the pre-phase output; they must not change solely because completeness was added.
- [ ] Re-run the same date and confirm there are no duplicate `(date, sector, symbol)` rows.
- [ ] Inspect an older score-history row and confirm it was not backfilled using current data.
- [ ] Confirm README wording does not imply that completeness is a quality score or recommendation.

## Human acceptance

Approve the phase only when all checks pass and the outputs remain readable. Then instruct the AI agent to follow the rename procedure in `../instructions.md`. Record any accepted schema deviations in the review message before the folder is renamed.
