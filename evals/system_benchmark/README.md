# System Benchmark v1

System Benchmark v1 is a benchmark family separate from the frozen Q1–Q6
microbenchmark in `evals/questions.json`.

This directory holds version-controlled benchmark contracts, the repository-local
policy corpus, development-only tasks, and deterministic reference expectations.
Held-out evidence remains intentionally absent.

## Current phase

PR A (#63) established the typed benchmark task/response contracts, deterministic
fixture loader, fingerprint inputs, and model-free validation.

PR B (#65) merged the second evidence capability: a version-controlled local policy
corpus plus deterministic, read-only section retrieval with auditable
document/version/section identity, historical `as_of` selection, bounded `top_k`,
bounded excerpts, corpus path enforcement, and deterministic ranking.

PR C (PR #67, tracking issue #66) adds the deterministic evaluation core:

- `dev_tasks.json`: 24 inspectable development tasks, exactly three per family A–H;
- `reference_solutions.json`: one known-good observable reference record per task;
- `src/evals/system_benchmark/scoring.py`: model-free per-dimension scoring with
  explicit reason codes;
- `src/evals/system_benchmark/reference.py`: strict reference loading and
  task/reference coverage validation.

The scorer evaluates observable behavior only: disposition, evidence/source
coverage, tool records, structured values, required/forbidden claims,
clarification/handoff state, and deterministic validator outcome.

## Development boundaries

Development fixtures are intentionally inspectable and may be used to build and
debug the grader. They are **not held-out evidence** and must not be reported as
generalization or architecture-performance results.

PR C does **not** add:

- held-out tasks;
- model execution;
- routing treatments;
- an LLM judge;
- chain-of-thought collection;
- external SaaS or paid APIs;
- new analytical permissions;
- changes to frozen Q1–Q6 semantics or accepted comparison evidence.

Task fixtures continue to declare benchmark version, family, split, expected route,
capability profile, allowed/forbidden dispositions, evidence requirements,
structured expectations, claim boundaries, tool boundaries, and reference identity.

Reference scoring remains deterministic and inspectable. A known-good reference
response must pass every applicable dimension; a failing reference blocks the case
rather than weakening the grader.

## Next phase

After PR C lands, the next approved implementation slice is routing treatments and
worker adapters. Held-out task creation remains gated on frozen interfaces and
human audit.
