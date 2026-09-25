# Reproducibility

Agentic Analytics Lab separates **code-level reproducibility** from **benchmark reproducibility**.

A clean unit-test run proves that the Python contracts, guards, evaluators, routing logic, and reporting code behave as expected. A benchmark run additionally requires the pinned model and data services used by the accepted evidence.

## 1. Fast verification

The repository's CI runs on clean Python 3.11 and 3.12 without a Python dependency-install step.

From the repository root:

    python -m compileall -q src
    python -m unittest discover -s tests -v

This validates the code paths that do not require a live ClickHouse or Ollama process.

## 2. Canonical benchmark lane

The most reproducible end-to-end path is the manual GitHub Actions workflow in [\`.github/workflows/repeatability-benchmark.yml\`](../.github/workflows/repeatability-benchmark.yml).

That workflow:

1. checks out the exact commit under test;
2. starts an ephemeral ClickHouse instance;
3. regenerates the deterministic seed-42, 500-row delivery dataset;
4. creates a separate SELECT-only ClickHouse user for the evaluated tool;
5. starts pinned Ollama 0.34.2 and pulls \`qwen2.5:7b\`;
6. runs benchmark preflight checks;
7. executes three unchanged benchmark passes;
8. preserves raw runs, a repeatability summary, environment metadata, and non-secret diagnostics as an Actions artifact.

The accepted single-agent reference is [Actions run 35755961530](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/35755961530).

## 3. Local reference lane

A local benchmark is useful for development, but hardware-sensitive measures such as latency should not be compared directly with GitHub-hosted evidence.

With the benchmark environment already running and loaded:

    python scripts/preflight_benchmark_env.py
    python scripts/run_repeatability_pass.py

The pass preserves three raw result files and generates the repeatability summary.

For the step-by-step fallback, see [Benchmark Repeatability](benchmark-repeatability.md).

## 4. Ground truth and scoring

The benchmark keeps model behavior separate from its answer contract.

Relevant artifacts:

- [Frozen Q1-Q6 cases](../evals/questions.json)
- [Evaluation rubric](../evals/rubric.md)
- [Deterministic scorer](../src/evals/scoring.py)
- [Synthetic data generator](../scripts/generate_delivery_data.py)
- [Ground-truth verification](../scripts/verify_ground_truth.py)
- [Read-only ClickHouse boundary](../src/tools/clickhouse_readonly.py)

Deterministic checks are preferred when a result can be verified directly. An LLM judge is not required for the accepted Q1-Q6 score.

## 5. Provenance

[\`src/evals/provenance.py\`](../src/evals/provenance.py) fingerprints the files that define the benchmark contract and records the evaluated Git commit.

This protects against an easy benchmarking mistake: comparing two architectures after silently changing the prompt, scorer, data generator, or tool semantics.

## 6. Compatibility gate

Repeated runs are aggregated only when their benchmark metadata and question ordering are compatible. Hardware-sensitive latency claims are compared only within the same execution environment.

A failed environment is preserved as an environment failure. The workflow does not silently substitute a smaller model and label it equivalent evidence.

## 7. What reproducible means here

The project does **not** claim that a generative model will emit byte-identical text on every run.

It does aim to make the following reproducible and reviewable:

- the exact code and benchmark contract
- the dataset seed and ground truth
- the model/runtime identity
- the allowed tool boundary
- the evaluator and success criteria
- the number and ordering of cases
- the preserved result artifacts
- the interpretation limits attached to those results

That is the level of reproducibility needed for the architecture comparison in this lab.
