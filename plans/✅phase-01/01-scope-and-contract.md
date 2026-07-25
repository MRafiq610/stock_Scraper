5# Phase 01 - Missing-Data Completeness: Scope and Contract

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. The agent must prepare the manual cases in `03-manual-verification.md` and stop before executing them.

## Objective

Make "unknown" visibly different from "average" without changing the V1 score formula in this phase. A high score based on sparse fundamentals must carry its evidence coverage in full rankings, history, monthly exports, and the compact LLM summary.

## Core field contract

Use these six roadmap fields from the existing daily snapshot as the completeness denominator:

| Logical field | Existing CSV key | Populated rule |
| --- | --- | --- |
| P/E | `price_to_earnings` | Parses to a finite number |
| P/B | `price_to_book` | Parses to a finite number |
| PEG | `peg_ratio` | Parses to a finite number |
| EPS | `eps` | Parses to a finite number |
| Net margin | `net_income_margin` | Parses to a finite number |
| Dividend yield | `dividend_yield` | Parses to a finite number |

Zero and negative values may be economically unsuitable for a particular percentile calculation, but they are still populated observations for completeness. Blank, `-`, `null`, non-numeric, NaN, and infinity are missing. Keep completeness parsing separate from `positive_number()`.

Add these additive output fields:

- `data_completeness_count`: integer from 0 to 6.
- `data_completeness_total`: always `6` for this schema version.
- `data_completeness_pct`: `(count / total) * 100`, formatted consistently with other scores.
- `data_completeness_label`: `low`, `partial`, or `complete`.

Default label thresholds:

- `low`: fewer than 3 populated fields.
- `partial`: 3 through 5 populated fields.
- `complete`: all 6 populated fields.

Place threshold constants beside the core-field definition so the rules are auditable. Do not describe an incomplete stock as neutral and do not use completeness itself to reward or punish `final_score` in this phase.

## In scope

- Calculate completeness from each as-of daily row.
- Add the four fields to `SCORE_FIELDS` and `LLM_FIELDS`.
- Persist them in score history, latest rankings, monthly score files, and the LLM summary.
- Include a short completeness warning in `key_reason` when the label is `low`.
- Document the fields and interpretation in `README.md`.
- Preserve compatibility when older history rows lack the new columns.

## Out of scope

- Rebalancing weights (Phase 02).
- Removing neutral percentile fallback behavior.
- Quarterly completeness (Phase 03).
- Dropping stocks from rankings because they are incomplete.
- Any automated trading or buy/sell rule.
