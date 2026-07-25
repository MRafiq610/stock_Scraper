# Instructions for AI Coding Agents

Use this file whenever starting, continuing, or completing a phase.

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for these phases. Do not add test files, test fixtures, mocks, coverage tooling, or CI test steps. Do not run the repository's existing unit-test command as phase validation. Read-only inspection and non-test static checks are allowed. Prepare the documented manual checklist and hand it to the human reviewer.

## Before implementation

1. Read this file, `index.md`, and every Markdown file inside the selected phase.
2. Inspect the current implementation before editing. File names and schemas in these plans describe the V1 repository as reviewed; preserve user changes made later.
3. Confirm required predecessor phases are completed. A completed folder begins with `✅`, for example `✅phase-01`.
4. Keep the phase narrowly scoped. Do not silently implement later phases.
5. Preserve existing CSV history and same-day upsert behavior. Schema changes must be additive unless the phase explicitly documents a migration.
6. Treat symbols as trimmed uppercase identifiers, dates as ISO `YYYY-MM-DD`, missing values as empty CSV cells/`None`, and numeric parsing as centralized behavior.
7. Never use future-dated quarterly, news, portfolio, or analyst data when producing an as-of historical score.

## During implementation

- Reuse the existing `Path`, CSV, logging, lookup, and orchestration patterns where they remain appropriate.
- Keep data-source fetching separate from scoring and presentation.
- Use named schemas/field lists and a single source of truth for configurable thresholds and weights.
- Make optional inputs degrade gracefully: absence should produce explicit `unknown`/blank context, not a fabricated neutral fact.
- Preserve deterministic ordering and idempotent writes.
- Avoid logging portfolio values, credentials, full third-party payloads, or other sensitive data.
- Update `README.md` and sample CSV documentation when user-facing commands or schemas change.
- Do not reinterpret missing or stale data as a buy, sell, or averaging-down recommendation.

## Human review handoff

When code work is ready:

1. Do not execute the phase's manual verification cases yourself.
2. Report changed files, schema changes, migration needs, assumptions, and known limitations.
3. Point the human reviewer to the phase's `03-manual-verification.md` file (phase 03 uses `04-manual-verification.md`).
4. Wait for explicit human confirmation that manual testing passed.
5. If testing finds a defect, fix only the active phase, refresh the checklist if behavior changed, and return it for another human run.

## Completion and folder rename

Only after the human reviewer explicitly approves the phase, rename the folder by prefixing its existing name with `✅`:

```text
phase-01       -> ✅phase-01
phase-08-bonus -> ✅phase-08-bonus
```

Use a normal filesystem or `git mv` rename that preserves all files. Update links in `plans/index.md` so they point to the renamed folder. Do not rename future phases, and do not use the checkmark to mean "code written but not manually approved."

If a completed phase needs later correction, keep its checkmark, document the corrective change in the handoff, and require human manual re-verification. Remove the checkmark only if the human reviewer explicitly reopens the entire phase.
