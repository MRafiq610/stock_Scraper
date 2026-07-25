# Phase 05 - AKD Rating Join: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are for that reviewer. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Manual checks

- [ ] Enter clearly marked review data containing current, stale, expired, future, and unknown ratings.
- [ ] Confirm the newest eligible report on/before `as_of` is chosen.
- [ ] Confirm a future report cannot appear in an older score.
- [ ] Confirm stale and expired states match approved thresholds/dates.
- [ ] Confirm stance variants normalize correctly and an unrecognized stance is flagged rather than guessed.
- [ ] Manually calculate one target-upside value from the same-day close.
- [ ] Confirm missing/zero target produces blank upside.
- [ ] Confirm duplicate same-day reports produce a visible diagnostic.
- [ ] Confirm AKD fields appear in full and LLM outputs but do not change any score or rank.
- [ ] Confirm source references are useful and no full licensed report text is copied.
- [ ] Remove/rename the optional file temporarily and confirm daily scoring still succeeds.

## Human acceptance

Approve only after date selection, freshness, and non-scoring behavior are correct. Then request the completion rename described in `../instructions.md`.
