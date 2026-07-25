# Phase 04 - Portfolio Awareness: Scope, Privacy, and Contract

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The human reviewer owns the checklist in `03-manual-verification.md`.

## Objective

Add position context to the review summary without changing sector scores or exposing private holdings unintentionally.

## Input contract

Use one row per owner/position lot or one aggregated row per `(owner, symbol)`, with an explicit documented choice. Recommended minimum columns:

```csv
symbol,owner,shares,average_cost,as_of_date
EFERT,owner_1,100,76.50,2026-07-31
```

Rules:

- `symbol`: required, trimmed uppercase, present in the symbol universe or surfaced as unmatched.
- `owner`: required stable label; avoid real names if the repository is shared.
- `shares`: finite and greater than zero for an active position.
- `average_cost`: finite, greater than zero, in PKR per share.
- `as_of_date`: ISO date and not later than the scoring date for historical joins.

If multiple rows exist for the same owner/symbol, aggregate shares and use a share-weighted average cost. Never average costs without weighting.

## Privacy default

Portfolio data is sensitive. Commit `data/portfolio.example.csv`, but ignore the real `data/portfolio.csv` by default. Allow a `PORTFOLIO_CSV` path override for local/private use. If cloud scoring must use the real file, the human owner must choose and approve a secure secret/private-artifact delivery method; do not silently commit holdings through the workflow's `git add data`.

The pipeline must work when the real portfolio file is absent.

## Output semantics

For each stock, add context fields such as:

- `portfolio_status`: `not_held`, `held_above_cost`, `held_below_cost`, `held_at_cost`, or `unknown`.
- `portfolio_owners`: non-sensitive owner labels.
- `portfolio_shares`: aggregate shares, only in the private/full output approved by the owner.
- `portfolio_average_cost`: weighted cost.
- `portfolio_cost_return_pct`: `(current_close - cost) / cost * 100`.
- `portfolio_as_of_date`.

Use a small tolerance for `held_at_cost` to avoid floating-point noise. A below-cost position is a review flag, not automatically an "averaging-down candidate"; value traps and concentration risk require human judgment.

## Scope boundaries

- Do not change quantitative, news, quality, or final scores.
- Do not place trades, size purchases, or recommend averaging down.
- Do not calculate tax lots, realized P&L, dividends received, or currency conversion in this phase.
- Do not expose owner/share/cost details in public logs or notifications.
