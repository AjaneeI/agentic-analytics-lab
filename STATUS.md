# Verified Project Status

_Last reviewed against System Benchmark v1 PR D and evidence-layer work on 2026-10-04._

## Current verified state

- The frozen Q1–Q6 benchmark remains unchanged historical/bounded evidence.
- The project keeps the single-agent, oracle-metadata routed, and
  natural-language routing evaluation lanes distinct.
- System Benchmark v1 is the active architecture-level evidence program.
- PR A (#63) merged typed task/response contracts, deterministic fixture
  loading, fingerprint inputs, and model-free validation.
- PR B (#65) merged as c5accae, establishing repository-local deterministic
  policy retrieval. It does not establish model quality.
- PR C merged via #68 as `6982f6753bdbcbc4cb547a3db0e1695cd87a2c72`; post-merge Python 3.11/3.12 and CodeQL passed.
- PR D / issue #69 is complete. Its reviewed five-file tree was integrated directly into `main` without a draft→ready transition, preserving the no-Codex rule.
- The PR D implementation keeps route inference independent from worker execution, supports oracle/free-text/simple-heuristic decisions, and exposes capability profiles `none`, `structured`, `documents`, and `multi_source`.
- Routed worker tool availability is intersected with the task's allowed-tool boundary, so routing errors cannot broaden permissions.
- Family G cannot fabricate unsupported-source evidence; Family H must return a handoff after bounded evidence gathering.
- PR D verification passed 13 focused tests and all 243 repository tests locally; the integrated `main` head `13008e4208320d2ebb6fb189f9aa9ba3091cd788` passed hosted Python 3.11/3.12 and CodeQL.
- Development-only heuristic diagnostics currently show 28.6% route accuracy, 57.1% capability accuracy, two false-cheap routes, and zero unsupported-source misses on the seven current development cases. This is a baseline diagnostic, not model-performance evidence.
- PR #74 adds a model-free cross-cutting evidence layer: hierarchical task/run bootstrap comparison, explicit optional trajectory contracts and deterministic trajectory scoring, hierarchical failure taxonomy, and Pareto-frontier architecture comparison.
- The evidence layer is implementation/regression evidence until it is run against accepted matched benchmark artifacts. It does not by itself establish architecture superiority or unseen-task generalization.
- Architecture comparison requires matching benchmark-contract provenance but permits provider identifiers to differ when provider/runtime composition is part of the architecture treatment.

## Previous PR C implementation

The current PR C candidate adds seven development-only task fixtures, seven
deterministic reference expectations, strict reference validation,
task/reference alignment, exact structured and policy evidence identities,
and deterministic scoring across disposition, evidence, tools, structured
values, clarification, handoff, and bounded answer terms.

Explicit reason codes cover missing/wrong/unsupported evidence, tool
violations, value mismatches, omitted required escalation, and unnecessary
escalation. A subprocess check verifies fixture/reference/scorer validation
imports no agent/model/tool runtime.

Local verification on Python 3.13.13:

- 82 System Benchmark tests pass;
- 230 repository tests pass;
- source/test compilation passes;
- Project Context Protocol checks pass;
- evals/questions.json retains SHA-256
  0dc047fbc378f0cf75f1c488e92fcb18dddcbfe976c79b1f16281e4b428654d1.

These are implementation/regression checks, not System Benchmark model results.
Python 3.11/3.12 and CodeQL remain required on the published candidate.

## PR C boundaries

PR C remains model-free, development-fixture-only, deterministic and
inspectable, separate from held-out evidence, separate from
architecture-performance claims, and free of Codex-credit use for benchmark
work.

No held-out cases, model runs, LLM judge, or chain-of-thought scoring belong in
this slice.

## Next bounded experiment

First apply the PR #74 evidence layer to the accepted matched single-agent and oracle-metadata routed repeatability artifacts and review the resulting uncertainty/frontier evidence. Then, before expanding benchmark infrastructure, run one supervised Hermes-vs-direct vertical slice against the PR D worker/routing contract. Use the same task, allowed tools, response contract, and deterministic verification for both paths. Measure Ajanee hands-on intervention, task acceptance, recovery behavior, tool/model calls, memory pressure, and incremental spend. Do not add concurrency, always-on behavior, new workers, or paid fallbacks.

## Evidence boundary

Landing PR C establishes the deterministic evaluation core only. It does not
establish single-agent or routed-agent superiority, unseen-task generalization,
or publication-ready benchmark results.

## Staleness rule

This file is not authoritative when it conflicts with repository evidence.
GitHub issues, PRs, commits, workflow runs, tests, and benchmark artifacts take
precedence.
