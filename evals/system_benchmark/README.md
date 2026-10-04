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


## Policy retrieval regression boundary

Section heading/body relevance is the primary ranking key. Document identity only breaks equal-relevance ties or provides a fallback for source-name-only searches; it cannot outweigh stronger section relevance. This is a deterministic lexical baseline, not semantic retrieval or a general recall guarantee.

Both `as_of` and manifest `effective_date` require an exact `YYYY-MM-DD` ASCII calendar date. Basic ISO and week-date forms are rejected. Historical policy bodies contain only period-appropriate rules. Policy authorization regressions compare rules governing the same action and circumstances without exposing benchmark-construction labels in retrievable text.

The repository-corpus regressions are development tests, not held-out tasks. Benchmark work must not invoke Codex or consume Codex credits; see `AGENTS.md` and decision D-010. Manual Python and CodeQL workflows provide a verification path that does not require a new reviewable PR.
