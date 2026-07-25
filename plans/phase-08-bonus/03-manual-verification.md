# Bonus Phase 08 - Provenance, Freshness, and Pipeline Health: Manual Verification

## Mandatory testing policy

Manual testing will be performed by the human reviewer. These checks are exclusively for that reviewer. AI coding agents must not execute them and must not create, modify, or run unit tests or other automated feature tests for this bonus phase.

## Manual checks

- [ ] Run a normal pipeline and confirm manifest dates, counts, paths, schema version, and model version match actual outputs.
- [ ] Review a successful no-op quarterly run and confirm it differs clearly from failure.
- [ ] Make an optional input unavailable and confirm scoring continues with an explicit warning.
- [ ] Reproduce a required-input failure and confirm last-known-good rankings are preserved.
- [ ] Reproduce an empty/malformed source response and confirm it cannot erase a non-empty history file.
- [ ] Review a partial-symbol failure and confirm threshold/status/failed count are visible.
- [ ] Confirm stale market, quarterly, portfolio, and rating dates receive their configured labels.
- [ ] Confirm no future effective/availability date is selected for a historical `as_of`.
- [ ] Inspect manifests, notifications, logs, commits, and artifacts for credentials, raw payloads, portfolio values, or licensed content.
- [ ] Confirm LLM evidence warnings are concise and do not change scores silently.
- [ ] Confirm dated-manifest retention is documented and behaves as approved.

## Human acceptance

Because this phase is optional, approve it only when it improves auditability without delaying or changing the seven roadmap features. Then instruct the AI agent to rename the folder to `✅phase-08-bonus` according to `../instructions.md`.
