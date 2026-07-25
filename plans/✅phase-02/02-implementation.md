# Phase 02 - Configurable Scoring Weights: Implementation

## Mandatory testing policy

Manual testing will be performed by the human reviewer. AI coding agents must not create, modify, or run unit tests or other automated feature tests for this phase. Only implementation, documentation, and manual-checklist preparation are permitted.

## Implementation steps

1. Add `src/scoring_config.py` with the ordered `AXIS_WEIGHTS`, `SCORING_MODEL_VERSION`, news weight, and validation tolerances.
2. Import policy into `src/sector_score_pipeline.py`; remove inline `0.30`, `0.25`, and similar quantitative constants.
3. Add a helper that accepts `{axis_name: Optional[float]}` and the configured weights. It must:
   - reject unknown configured axes and invalid values;
   - ignore `None`, not numeric zero;
   - reject an empty available set rather than fabricate a neutral final score;
   - normalize by the sum of available weights;
   - return both the score and enough metadata to report which axes contributed.
4. Build the current five-axis mapping in `score_sector()`. Pass `quality=None` until Phase 03 is complete.
5. Add `scoring_model_version` and `active_axis_weight_pct` (or an equally explicit coverage field) to `SCORE_FIELDS` and `LLM_FIELDS`.
6. Retain score clamping at the final formatting boundary. Do not hide a configuration error by clamping bad weights.
7. Keep news combination in a separate helper or clearly separate block so axis and overlay policy cannot be confused.

## Backward compatibility

- Historical output rows keep their old values and have a blank model version unless explicitly recalculated for their own date.
- The same as-of run should replace only matching history keys.
- Column additions must not delete existing Phase 01 completeness fields.
- Downstream readers should address columns by name, never position.

## Operational documentation

Update `README.md` with:

- The V2 table of weights.
- Why quality is excluded and remaining axes renormalized when quarterly evidence is missing.
- The continued news overlay behavior.
- A warning that changing weights changes ranking semantics and requires a new `SCORING_MODEL_VERSION`.

## Completion deliverables

- Validated policy module.
- Normalized weighted-score helper.
- V2 scoring calculation and model metadata.
- Additive CSV schemas and README update.
- Manual verification checklist ready for the human reviewer.
