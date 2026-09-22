# Benchmark Repeatability

The next gate for Agentic Analytics Lab is to characterize how the unchanged
single-agent baseline behaves across repeated runs before tuning prompts or
adding routing.

This layer is intentionally descriptive. It does not change the agent, prompt,
question set, evaluator, ClickHouse tool, or scorer.

## GitHub-hosted reproducibility lane

The recommended fully autonomous evidence lane is the manual-only GitHub Actions
workflow at `.github/workflows/repeatability-benchmark.yml`.

Run it from **Actions → GitHub repeatability benchmark → Run workflow** after the
workflow is present on the default branch. It accepts no user-supplied commands,
SQL, image names, or model identifiers.

The workflow:

1. checks out the exact commit being benchmarked;
2. starts an ephemeral ClickHouse instance;
3. regenerates and loads the deterministic seed-42 / 500-row dataset using the
   repository generator and SQL;
4. creates a separate ClickHouse user with SELECT-only access for the
   model-facing read-only tool;
5. starts pinned Ollama `0.34.2` and pulls the frozen `qwen2.5:7b` model;
6. runs the existing benchmark preflight;
7. calls the canonical `scripts/run_repeatability_pass.py` orchestration;
8. uploads the three raw runs, repeatability summary, environment manifest, and
   non-secret diagnostic logs as a GitHub Actions artifact.

Artifacts use the name
`single-agent-repeatability-github-runner-<commit-sha>` and are retained for
14 days.

If the default GitHub-hosted runner cannot practically support `qwen2.5:7b`,
treat the failed run and its diagnostic artifact as a measured environment
blocker. Do not substitute a smaller model and call it comparable evidence.

## Local reference lane

Run the commands below from the repository root with the benchmark environment
already loaded into the shell.

Recommended one-command path (runs preflight first, executes the unchanged
single-agent benchmark three times, preserves run1/run2/run3 JSON, and then
builds the repeatability summary):

```bash
python3 scripts/run_repeatability_pass.py
```

If preserved run files already exist, the command fails instead of overwriting
them silently. Use the explicit override only when you intentionally want to
replace the preserved runs:

```bash
python3 scripts/run_repeatability_pass.py --force
```

### Manual fallback/reference

If you need to run the same workflow step-by-step, use:

```bash
python3 scripts/preflight_benchmark_env.py

python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run1.json

python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run2.json

python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run3.json
```

Raw benchmark JSON remains ignored by git.

## Summarize repeatability

```bash
python3 scripts/summarize_repeatability.py \
  experiments/results/single_agent_qwen2.5_7b_run1.json \
  experiments/results/single_agent_qwen2.5_7b_run2.json \
  experiments/results/single_agent_qwen2.5_7b_run3.json
```

The default output is:

```text
docs/generated/single-agent-repeatability-summary.md
```

The summary includes:

- per-run execution, correctness, and task-success counts
- tool calls, model calls, tokens, and latency
- mean/range/stdev for observed task-success rate
- per-question recurrence across runs
- recurring failure-type counts
- a compatibility gate that rejects mismatched benchmark metadata or case order

## Comparison integrity

The repeatability summary requires matching:

- benchmark schema version
- architecture
- model
- provider
- dataset
- frozen question-set path
- question IDs and order

Fields that should vary between runs, such as run timestamp and measured latency,
are not part of the compatibility signature.

The GitHub-hosted and local lanes use different hardware. Compare latency only
within the same execution environment. Correctness, grounding, failure
recurrence, model/tool-call counts, and other hardware-insensitive fields remain
useful evidence when the benchmark configuration is otherwise matched.

Do not tune Q3 or Q5 merely to improve the score before this repeatability pass.
If their failure behavior changes across unchanged runs, record that as evidence.

## Interpretation

A small repeatability pass can reveal whether failures appear stable or variable,
but it is not a statistical-significance claim. The first purpose is to avoid
building a routed architecture around a one-off failure pattern.

Only after repeatability is characterized should the project implement the
smallest routed/control-plane prototype and compare it under matched conditions.
