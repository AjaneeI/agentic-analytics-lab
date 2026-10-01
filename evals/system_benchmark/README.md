# System Benchmark v1

System Benchmark v1 is a benchmark family separate from the frozen Q1–Q6
microbenchmark in `evals/questions.json`.

This directory will hold version-controlled task fixtures and, in later
implementation phases, the local policy corpus and reference solutions defined
by the approved design.

## Current phase

PR A establishes only the benchmark contract and fixture loader.

It does **not** add development tasks, held-out tasks, policy documents, model
execution, routing treatments, graders, or official benchmark evidence.

Task fixtures are validated before execution and must declare their benchmark
version, family, split, expected route, capability profile, allowed/forbidden
dispositions, evidence requirements, semantic expectations, tool boundaries,
and reference-solution identity.

Held-out tasks are intentionally absent until the development interfaces,
scoring rules, tool contracts, routing contract, and corpus are frozen.
