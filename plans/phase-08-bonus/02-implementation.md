# Bonus Phase 08 - Provenance, Freshness, and Pipeline Health: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this bonus phase. Prepare manual scenarios only.

## Run manifest

Add a machine-readable manifest such as `data/manifests/latest_pipeline_run.json` and, if useful, a dated archive. Include:

- run ID, start/end timestamp, status, and scoring as-of date;
- source name, selected/effective date, collected timestamp, input row count, invalid row count, and failed symbol count;
- output path, row count, and schema/model version;
- warnings for missing optional inputs, stale inputs, low coverage, and partial fetches;
- no credentials, raw payloads, owner-level portfolio values, or licensed report text.

Write the manifest atomically. A failed run may write a failure manifest but must not replace valid ranking files with empty outputs.

## Pipeline safeguards

1. Before replacing a non-empty output, validate required headers, non-empty row expectations, unique business keys, and plausible as-of date.
2. Write to a same-directory temporary file and replace only after successful close/validation.
3. Distinguish:
   - required-source failure: stop scoring and preserve last-known-good outputs;
   - optional-source absence: continue with explicit unknown context;
   - partial symbol failure: continue only within an approved threshold and flag the run prominently.
4. Include manifest status and warning summary in existing notifications.
5. Keep dated manifests within an explicit retention policy; do not grow artifacts without bound.

## Summary provenance

Add only compact, decision-relevant fields to `latest_sector_summary.csv`, for example:

- `market_data_date`
- `quarterly_age_days`
- `portfolio_as_of_date`
- `akd_rating_age_days`
- `evidence_freshness`
- `evidence_warning`

Compute overall evidence freshness from documented precedence: any required source failure is critical; otherwise stale/unknown optional evidence creates a warning, not a false failure.

## Documentation and operations

Update `README.md` with manifest location, freshness thresholds, last-known-good behavior, partial-failure policy, and operator response. Document how to distinguish:

- no new source data;
- source fetch failure;
- successful no-op;
- successful partial run;
- complete successful run.

## Completion deliverables

- Central freshness policy.
- Atomic, privacy-safe run manifest.
- Output validation/last-known-good safeguards.
- Compact provenance in review output.
- Notification and operator documentation.
- Human manual checklist ready.
