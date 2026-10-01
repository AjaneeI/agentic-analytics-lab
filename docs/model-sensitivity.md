# Model sensitivity study

The frozen architecture comparison uses `qwen2.5:7b`. Model reliability is a
known limitation, but silently replacing that model would erase the comparison
anchor.

This lane measures model sensitivity separately.

## Runner

`scripts/run_model_sensitivity.py` requires exact model identifiers:

```bash
python3 scripts/run_model_sensitivity.py \
  --models qwen2.5:7b another-local-model
```

The default repeat count is three per model. The script runs the existing
ClickHouse preflight first, uses the frozen Q1-Q6 cases and deterministic scorer,
and writes separate ignored artifacts per model plus an aggregate summary.

## What to compare

- task-success rate and repeatability
- recurring failure cases
- failure-stage distribution after the diagnostic sidecar lands
- tool and model call counts
- tokens
- latency

## Claim boundary

This is a sensitivity study, not a model-selection shortcut. `qwen2.5:7b`
remains the frozen baseline unless the core architecture experiment is complete
and a separate benchmark-version change is explicitly approved.

Do not tune the prompt independently for each model inside a sensitivity study;
that would confound model effects with prompt effects.
