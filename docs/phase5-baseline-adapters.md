# Inactive baseline adapters

The October 17 development branch adds two explicitly selected,
runner-compatible adapters in `src/evals/system_benchmark/baselines.py`.
Importing this module does not start a model, database query or trial. Existing
Treatment A defaults, the seven active fixtures and deterministic scoring are
unchanged. This work does not accept Phase 5 entry or qualify a comparison.

`StrongSingleExecutor` requires an explicit model instance and `model_id`.
It consumes `build_strong_single_invocation` and reuses the complete bounded
local runtime, prompt, response parsing, tool schemas, budgets and observations.
It records a constant local/multi-source decision, with no route classifier.
Both safe tool schemas are visible to the model; execution separately checks
the task allowlist and forbidlist. G has no executable tools even if a caller
constructs a malformed wider task. The existing hard G/H response checks run
after response parsing. No fixture/reference metadata is added to model input.

This affordance/permission distinction preserves the existing strong-single
invocation contract without letting a document-only or unsupported-source task
execute a forbidden analytical query. A forbidden attempted call fails before
either tool function runs. Scoring remains an additional unchanged boundary.

The adapter never chooses the comparison model. `qwen2.5:7b` remains the v1
comparison anchor; `hermes-local:qwen3.5-9b` remains the separate Treatment A
runtime default. Caller-supplied model settings, runtime/provider identity and
accepted anchor must be preserved in any future run manifest. No live model
run or database run was performed for this implementation.

`DeterministicSimpleExecutor` reuses the existing fixed-query
`BLOCKER_RATE_LEADER` handler for the current A01 all-item request. Selection
uses an exact normalized user-text operation allowlist. It does not select by
case ID, family, oracle route or reference/expected values. It reports observed
query rows and the actual fixed SQL through `TrialExecution`. Every other
request, including D01's active-work/multi-source scope, raises
`DeterministicBaselineDeclined` before tool execution. Do not count this
non-applicability as task success or use it as a fallback for another scope.

Offline regression command:

```sh
python3 -m unittest tests.system_benchmark.test_baseline_adapters tests.system_benchmark.test_local_worker -v
```

The scripted-model tests establish implementation behavior only. Future
comparisons remain blocked until the approved schema-context activation is
integrated here and schema/prompt/tool parity is independently verified across
the exact compared architectures, with accepted evaluator and provenance
controls. Strong-single adapter readiness is not a prerequisite for standalone
Treatment A acceptance.
