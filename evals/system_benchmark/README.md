# System Benchmark v1

System Benchmark v1 is a benchmark family separate from the frozen Q1–Q6
microbenchmark in `evals/questions.json`.

This directory holds version-controlled benchmark contracts and the repository-local
policy corpus used by the current development phase. Development fixtures,
deterministic reference/scoring contracts, model execution, routing treatments,
and held-out evidence land only in later bounded phases.

## Current phase

PR A established the typed benchmark contract, deterministic fixture loader,
fingerprint inputs, and model-free validation.

PR B adds the second evidence capability: a version-controlled local policy corpus
plus deterministic, read-only section retrieval with auditable
document/version/section identity, historical `as_of` selection, bounded `top_k`,
bounded excerpts, corpus path enforcement, and deterministic tie-breaking.

The current phase still does **not** add development task fixtures, held-out tasks,
model execution, routing treatments, graders, or official System Benchmark v1
performance evidence.

Task fixtures are validated before execution and must declare their benchmark
version, family, split, expected route, capability profile, allowed/forbidden
dispositions, evidence requirements, semantic expectations, tool boundaries,
and reference-solution identity.

Held-out tasks remain intentionally absent until the development interfaces,
scoring rules, tool contracts, routing contract, and corpus are frozen.

## Next phase

PR C adds development-only fixtures and deterministic reference/scoring contracts.
It remains model-free and does not expose held-out benchmark evidence.
