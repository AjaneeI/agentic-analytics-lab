# Verified Project Status

_Last reviewed against `main` source `58add5e` on 2026-10-05; documentation audit only._

## October 5 source and evidence snapshot

- Audited source: [58add5e](https://github.com/AjaneeI/agentic-analytics-lab/commit/58add5e58e581be21d3511fc4cd2cb5be44f49b7).
- The independent Python 3.13.13 check passes **289 repository tests**. Hosted
  [Python 3.11/3.12](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/37250042363)
  and [CodeQL](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/37250042377)
  passed on this same source. Test counts describe regression coverage, not benchmark size.
- The accepted Q1–Q6 results remain **12/18 vs. 17/18 task-success observations**:
  six distinct tasks repeated three times. They test oracle-metadata execution,
  not natural-language route inference. The [accepted analysis](docs/generated/accepted-q1-q6-architecture-evidence.md)
  includes a descriptive uncertainty interval spanning zero.
- PR #80 is on `main`: SB-D01 now uses the **active-work** denominator and
  expected blocker rate **17.8%**, rather than the all-item rate. The frozen
  Q1–Q6 questions, generator, and original scorer were not changed by this fix.
- [PR #72](https://github.com/AjaneeI/agentic-analytics-lab/pull/72) remains an
  intentionally draft, separately verified execution-rehearsal candidate. Its
  seven controls, fourteen negative controls, and 278-test snapshot are not
  interchangeable with the current `main` source.
- This recruiter-readiness pass updates documentation and evidence navigation
  only. It does not execute a model, change a scorer, merge an experimental
  branch, or unlock a held-out phase.

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
- Issue #78 / draft PR #79 remediated the direct-worker failure from #73 with a bounded local `hermes-local:qwen3.5-9b` executor that exposes only the real `query_clickhouse` and `retrieve_policy` tools, derives observations from actual runtime calls, and provides no filesystem/shell tool surface. The reviewed two-file tree is on `main`; Python 3.11/3.12 and CodeQL passed on the integrated code head.

## Historical PR C implementation evidence

The merged PR C slice established seven development-only task fixtures, seven
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

These were implementation/regression checks at the PR C milestone, not System Benchmark model results or the current suite count. PR C is merged; current-source checks are listed in the October 5 snapshot above.

## PR C boundaries

The PR C slice was model-free, development-fixture-only, deterministic and
inspectable, separate from held-out evidence and architecture-performance
claims. The repository's no-Codex-credit rule governs further benchmark work;
this statement is an operating constraint, not an audit of historical billing.

No held-out cases, model runs, LLM judge, or chain-of-thought scoring belong in
this slice.

## Next bounded experiment

Resume issue #73 by rerunning **Treatment A only** with the new bounded local worker on the same SB-D01 task and deterministic scorer. Do not use generic OpenCode for this rerun. If Treatment A is accepted, preserve that evidence and stop. Treatment B remains blocked until Hermes enforces a hard one-worker/no-concurrency invariant at the delegation boundary; do not rerun Hermes by prompt instruction alone. Keep spend at $0 and do not change benchmark semantics, add workers, or start new infrastructure.

## Evidence boundary

PR C established the deterministic evaluation core only. Later implementation and regression work does not
establish single-agent or routed-agent superiority, unseen-task generalization,
or publication-ready benchmark results.

## Staleness rule

This file is not authoritative when it conflicts with repository evidence.
GitHub issues, PRs, commits, workflow runs, tests, and benchmark artifacts take
precedence.
