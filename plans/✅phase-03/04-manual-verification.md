# Phase 03 - Quarterly Fundamentals and Quality Axis: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are for that reviewer to execute manually. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this phase.

## Scraper checks

- [ ] Run a single-symbol fetch for EFERT and compare fiscal periods and several ratio/P&L values with the approved source.
- [ ] Confirm percentages, ratios, currency values, negatives, zeros, and blanks retain correct meaning.
- [ ] Re-run the symbol and confirm unchanged filings create no duplicate business keys.
- [ ] Use a source symbol with a newer filing and confirm one normalized period is added or restated correctly.
- [ ] Simulate/reproduce an empty or malformed response and confirm existing history is not erased.
- [ ] Confirm ratios history, P&L history, and latest ratios contain deterministic headers/order.
- [ ] Confirm logs and committed files contain no cookie, credential, or oversized raw response.

## As-of and scoring checks

- [ ] Pick dates immediately before and after a known filing's availability date.
- [ ] Confirm the earlier score cannot see the filing and the later score can.
- [ ] Confirm the latest snapshot is not used to leak future data into the earlier score.
- [ ] Manually recompute one sector's debt-to-equity and ROE percentile directions.
- [ ] Confirm a stock with no quarterly row has blank quality—not `50`—and its other axes renormalize.
- [ ] Confirm a stock with only some valid quality metrics reports matching count/completeness.
- [ ] Inspect a negative-equity or structurally non-comparable case and confirm it is flagged rather than rewarded.
- [ ] Confirm the quality fields appear in ranking, history, monthly, and LLM outputs.
- [ ] Confirm the daily scraper still runs without invoking the quarterly fetcher.
- [ ] Manually dispatch the monthly workflow and verify artifacts/commit/no-op reporting.

## Human acceptance

Approve only after source fidelity, idempotency, fiscal-period semantics, and no-look-ahead behavior are demonstrated. Then direct the AI agent to rename the folder using `../instructions.md`.
