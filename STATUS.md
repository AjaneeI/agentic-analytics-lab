# Verified Project Status

## M0.6 fresh SB-D01 A/B — 2026-10-06

- M0.6 was frozen at commit `0d93415a7a9c4aa0a88eed07aa0c932464613d29`
  and tag `m0-6-fresh-sb-d01-ab-v1` on successor branch
  `m0-6-fresh-sb-d01-ab`; issue #87 is the durable preregistration/evidence
  record. Historical issues #73, #82, #84, #85, #86 and draft PR #83 remain
  unchanged.
- Treatment A ran once and was unscored: the local model used unqualified
  `delivery_work_items`, which the unchanged validator rejected. Elapsed time
  was 43.936 seconds; retries, Ajanee intervention, and paid spend were zero.
- Treatment B ran once and was unscored: one child reproduced the unqualified
  SQL failure, retrieved policy evidence, then exhausted its evidence-tool
  budget; the parent later attempted six forbidden evidence calls. Elapsed time
  was 762.717 seconds; retries, Ajanee intervention, and paid spend were zero.
- Hermes made exactly one valid delegation, created exactly one child, launched
  no second worker, and made no extra delegation attempt. Raw parent requests
  prove `delegate_task` was present initially and absent from all six
  post-child parent requests. Post-success retirement therefore held even
  though overall Treatment B failed.
- Fixed-state checks passed before A, before B, and after B. Raw evidence and
  deterministic post-run analysis are preserved under
  `experiments/results/m0-6-fresh-sb-d01-ab-2026-10-06`.
- M1 readiness: **not supported**. Neither treatment produced an accepted
  result, and Hermes required repeated enforcement of child budget and parent
  evidence boundaries.
- Next bounded experiment: preregister a three-case blocker-rate SQL
  qualification micro-study that changes only the model-visible
  `query_clickhouse` wording to explicitly require the exact fully qualified
  table. Keep the validator, model, context, temperature, data, and
  no-normalization policy unchanged. Do not rerun M0.6.

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
- Issue #78 / draft PR #79 remediated the direct-worker failure from #73 with a bounded local `hermes-local:qwen3.5-9b` executor that exposes only the real `query_clickhouse` and `retrieve_policy` tools, derives observations from actual runtime calls, and provides no filesystem/shell tool surface. The reviewed two-file tree is on `main`; Python 3.11/3.12 and CodeQL passed on the integrated code head.

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

Resume issue #73 by rerunning **Treatment A only** with the new bounded local worker on the same SB-D01 task and deterministic scorer. Do not use generic OpenCode for this rerun. If Treatment A is accepted, preserve that evidence and stop. Treatment B remains blocked until Hermes enforces a hard one-worker/no-concurrency invariant at the delegation boundary; do not rerun Hermes by prompt instruction alone. Keep spend at $0 and do not change benchmark semantics, add workers, or start new infrastructure.

## Evidence boundary

Landing PR C establishes the deterministic evaluation core only. It does not
establish single-agent or routed-agent superiority, unseen-task generalization,
or publication-ready benchmark results.

## Staleness rule

This file is not authoritative when it conflicts with repository evidence.
GitHub issues, PRs, commits, workflow runs, tests, and benchmark artifacts take
precedence.
