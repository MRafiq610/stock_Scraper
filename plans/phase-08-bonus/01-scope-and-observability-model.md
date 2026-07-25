# Bonus Phase 08 - Provenance, Freshness, and Pipeline Health

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this bonus phase. The agent must prepare the checklist and leave execution to the reviewer.

## Why this bonus exists

V2 combines daily prices, occasional filings, manually maintained portfolio snapshots, dated news, and analyst reports. A single final score can look current even when one input is old or failed to refresh. This phase makes the evidence timeline visible and makes partial pipeline failures harder to overlook.

This phase is optional and must not delay priorities 01–07.

## Objectives

- Record when each selected input was effective and when it was collected.
- Label stale/unknown inputs without fabricating neutral values.
- Produce a compact run manifest with row counts, failures, source dates, and output paths.
- Protect last-known-good outputs from empty/partial overwrites.
- Give the LLM summary enough provenance to explain uncertainty.

## Common provenance contract

Use consistent concepts across sources:

- `effective_date`: date the fact applies to (market date, fiscal end, portfolio as-of, report date).
- `available_date`: earliest date the pipeline could legitimately know the fact.
- `collected_at`: timestamp the pipeline obtained it.
- `source_name`: stable source identifier.
- `freshness`: `current`, `stale`, `expired`, or `unknown`.

Do not force every CSV to use identical columns if semantics differ, but map each source to these concepts in documentation.

## Freshness policy

Define freshness thresholds centrally by source type, not scattered magic numbers. Suggested review defaults:

- Daily market snapshot: stale when it is not the expected latest trading session.
- Quarterly fundamentals: show age and stale after a human-approved number of days; fiscal schedules vary.
- Portfolio: stale based on the owner's update cadence.
- AKD rating: use Phase 05's approved threshold/expiry.
- News: preserve its own date and never present an old item as current.

Labels inform review and do not automatically alter scores unless a later, separately approved policy says so.

## Scope boundaries

- No external monitoring vendor is required.
- No automatic remediation that deletes or rewrites history.
- No claim that "fresh" means correct.
- No secret or private portfolio values in manifests, logs, or notifications.
