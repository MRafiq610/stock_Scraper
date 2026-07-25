# PSX Stock Scraper V2 - Implementation Plan

This directory converts the seven priorities in `psx_scraper_v2_roadmap.pdf` into implementation phases for the existing V1 repository. The phases refine the current pipeline; they do not replace its daily symbol, sector, detail, scoring, history, notification, or export flows.

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for these phases. Agents must implement the requested scope, prepare the phase's manual verification checklist, and stop so the human reviewer can execute it. Read-only inspection and non-test static checks are allowed, but they do not replace human acceptance.

## Phase map

| Phase | Roadmap priority | Outcome | Depends on |
| --- | --- | --- | --- |
| [✅phase-01](✅phase-01/01-scope-and-contract.md) | Priority 1 | Missing-data completeness is explicit in ranking and LLM outputs | V1 |
| [✅phase-02](✅phase-02/01-scope-and-weight-model.md) | Priority 2 | Scoring weights are configurable, normalized, and value/income oriented | Phase 01 |
| [✅phase-03](✅phase-03/01-architecture-and-data-contracts.md) | Priority 3 | Quarterly ratios and P&L history feed a new quality axis without look-ahead | Phases 01-02 |
| [✅phase-04](✅phase-04/01-scope-privacy-and-contract.md) | Priority 4 | Portfolio context is joined safely into decision-review outputs | Phase 01 |
| [phase-05 — skipped](phase-05/01-scope-and-rating-contract.md) | Priority 5 | Skipped: no reliable automated AKD source | Phase 01 |
| [✅phase-06](✅phase-06/01-scope-and-risk-model.md) | Priority 6 | Rolling close-to-close volatility makes risk visible | Sufficient daily history |
| [✅phase-07](✅phase-07/01-scope-and-confidence-rules.md) | Priority 7 | Sector sample size has an unambiguous confidence label | Phase 01 |
| [phase-08-bonus](phase-08-bonus/01-scope-and-observability-model.md) | Bonus | Provenance, freshness, and pipeline-health signals make mixed-cadence data auditable | Phases 03-05 |

## Recommended delivery order

Implement phases 01 and 02 first. Treat phase 03 as the main V2 capability and complete its scraper/data-contract work before connecting its quality axis. Phases 04 and 05 may then be implemented independently. Start phase 06 only after the history-depth gate in its plan is satisfied. Phase 07 is safe to pull forward after phase 01 because it changes presentation rather than the underlying score. Phase 08 is optional and must never block the seven roadmap priorities.

## Definition of phase completion

A phase is complete only when:

1. Every Markdown file in that phase has been followed.
2. All listed deliverables and documentation updates exist.
3. The AI agent has not created, modified, or run automated feature tests.
4. The human reviewer has executed and approved the manual verification checklist.
5. Any migration or backward-compatibility notes have been resolved.
6. The phase folder is renamed according to [instructions.md](instructions.md).

The roadmap concerns screening and review support, not automatic trading. Outputs must remain descriptive and must not place orders or present rankings as guaranteed investment advice.
