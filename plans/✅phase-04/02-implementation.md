# Phase 04 - Portfolio Awareness: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Prepare the handoff and let the human execute it.

## Implementation steps

1. Add a safe committed `data/portfolio.example.csv` and ignore the real portfolio path.
2. Add an optional path constant/environment override in `src/sector_score_pipeline.py` or a small input configuration module.
3. Implement `portfolio_lookup(rows, as_of)` that validates fields, excludes future snapshots, aggregates duplicate owner/symbol rows, and returns unmatched/invalid-row diagnostics.
4. Join portfolio context after score calculation or in output enrichment. Keep portfolio data out of sector percentile input.
5. Use `price_close` from the matching daily as-of row to calculate cost return. Leave status `unknown` when close/cost/as-of data is unavailable.
6. Add the approved context fields to `SCORE_FIELDS` and a privacy-reviewed subset to `LLM_FIELDS`.
7. Do not write the real input into generated output archives unless the human explicitly approves those files as private.
8. Add concise run-summary counts: held symbols matched, held symbols unmatched, invalid rows, and stale portfolio snapshot count. Do not log values.

## Historical behavior

If portfolio history is not maintained, current holdings must not be injected into an old `--as-of` ranking. Require `as_of_date <= scoring date` and choose the latest eligible snapshot per owner/symbol. If the file represents current state only, document that historical portfolio enrichment is unavailable and emit `unknown` for older scoring dates.

## Repository and workflow updates

- Update `.gitignore` for the private file while keeping the example tracked.
- Update `README.md` with schema, path override, local usage, privacy warning, aggregation, and status meanings.
- Review `.github/workflows/daily-stock-pipeline.yml`: confirm `git add data` cannot stage the ignored private input.
- If a cloud secret mechanism is approved, materialize the file only for the job, keep it out of artifacts/commits, and remove it during cleanup.

## Completion deliverables

- Safe example and private-file policy.
- Validated, as-of-aware portfolio lookup.
- Non-scoring enrichment fields.
- Privacy-safe logs and exports.
- README/workflow documentation.
- Human manual checklist ready.
