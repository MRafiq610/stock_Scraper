# Phase 04 - Portfolio Awareness: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are exclusively for that reviewer. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Manual checks

- [ ] Confirm the real `data/portfolio.csv` is ignored and the example remains tracked.
- [ ] Enter disposable rows for held above cost, held below cost, held near cost, and not held.
- [ ] Confirm duplicate lots use a share-weighted average cost.
- [ ] Confirm future-dated portfolio rows are excluded from an older score.
- [ ] Confirm missing close/cost produces `unknown`, not a fabricated return.
- [ ] Confirm unmatched symbols are reported without stopping valid joins.
- [ ] Confirm portfolio context does not change any score or sector rank.
- [ ] Inspect LLM, history, monthly, notification, artifact, and log outputs for unapproved owner/share/cost exposure.
- [ ] Run without the real portfolio file and confirm the normal scoring pipeline still succeeds.
- [ ] Confirm `held_below_cost` is worded as context, not an automatic averaging-down recommendation.

## Human acceptance

Approve only when calculations and privacy behavior match the chosen deployment model. Then ask the AI agent to follow the folder-renaming process in `../instructions.md`.
