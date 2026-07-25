# Phase 05 - AKD Rating Join: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Prepare the manual checklist and stop before it is run.

## Implementation steps

1. Add a header-only or clearly fictional sample `data/akd_ratings.csv`; never invent a real stance or target.
2. Implement an as-of-aware `akd_rating_lookup()` using the established news lookup shape while adding date parsing, stance normalization, expiry, age, and deterministic duplicate handling.
3. Read the file as optional so its absence does not break daily scoring.
4. Join the selected row after quantitative/final scoring. Calculate target upside against the same as-of `price_close`, not today's price.
5. Add the context fields to full score schemas and the compact LLM schema.
6. Report invalid rows, duplicate keys, unmatched symbols, current/stale/expired counts without logging licensed report text.
7. Update `README.md` with schema, manual update workflow, freshness threshold, source-reference practice, and non-scoring status.

## Data quality rules

- Blank stance and blank target may be allowed only when the row still carries useful report metadata; label it `unknown`.
- Do not interpret target price `0` as a valid target.
- If multiple reports have the same symbol/date, choose by an explicit stable tie-breaker and warn; preferred resolution is manual cleanup.
- When a rating is stale, retain the historical values for context but label them prominently.
- Historical reruns must never select a future report.

## Completion deliverables

- Maintained rating CSV contract.
- Latest-eligible lookup with freshness.
- Target-upside calculation and provenance.
- Additive full/LLM outputs.
- README update and diagnostics.
- Manual verification checklist ready for human review.
