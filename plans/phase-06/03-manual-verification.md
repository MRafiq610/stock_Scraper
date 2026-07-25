# Phase 06 - Volatility and Risk Measure: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are for that reviewer to run manually. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Manual checks

- [ ] Confirm representative symbols meet the 20-return minimum before accepting the feature.
- [ ] Hand-calculate returns and sample standard deviation for a small copied price sequence and compare with displayed behavior.
- [ ] Confirm the window uses trading observations, not 30 calendar days.
- [ ] Confirm no price after `as_of` participates.
- [ ] Confirm duplicate dates do not add observations.
- [ ] Confirm zero, negative, blank, and invalid closes do not create fake zero returns.
- [ ] Confirm insufficient history produces `unknown` and shows its observation count.
- [ ] Compare a visibly steady and visibly erratic stock path with similar period returns; the erratic path should show higher volatility/lower stability.
- [ ] Confirm sector percentile direction is lower volatility = higher score.
- [ ] Confirm final scores and ranks are unchanged in the informational release.
- [ ] Confirm the README states limitations and does not equate volatility with all risk.

## Human acceptance

Approve only after numerical behavior and the no-look-ahead window are understood. Then instruct the AI agent to rename the folder according to `../instructions.md`.
