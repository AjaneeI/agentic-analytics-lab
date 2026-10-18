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

## Phase 3 preparation — 2026-10-17 sprint, not accepted

Owner authorization in issues #94/#95 permits this independent model-free
preparation while Phase 2 remains a separate prerequisite. The additive
evaluator audit preserves seven authored reference responses (7/7 pass),
17 intended-reason negative controls (17/17 reject), five additional semantic
negative controls (all wrongly pass), and nine valid alternatives (four
wrongly reject). Nine unresolved control mismatches block evaluator acceptance.
The audit records A01 scope ambiguity, explicit policy/version authority,
task-template overlap, and unchanged hashes for 18 frozen inputs. No scorer,
task, reference expectation, corpus, Q1–Q6, or data generator was changed.

See `experiments/evaluator-validation-20261017/README.md` and its preserved
`audit.json`. The audit command intentionally exits 2; four audit-tool tests
and all 293 repository tests passed on the original candidate. This is evaluator
defect evidence and preparation only, not Phase 3 acceptance, Phase 2
qualification, model performance, or held-out evidence. Versioned evaluation
corrections require owner approval; no corrections were applied here.

The later model-free integration characterization loads the real frozen D01
task/reference and runs eight SQL controls on an in-memory SQLite copy of
unchanged seed-42 generator output, with real local policy retrieval and the
unchanged worker/extractor/scorer. Independent counts confirm Data at 8/45
active items (17.7778%). Three valid unlabelled query forms wrongly reject;
one unfiltered query with a literal rate and active label wrongly passes.
Four other controls match expectations. Its command also exits 2, and the
original audit report remains byte-identical with nine unresolved controls.
All 18 frozen inputs remain unchanged; no production source was edited.

See `runtime-characterization.json` in the same evidence directory. Four new
tests verify actual rows, independent counts/ranking, frozen outcomes,
reproducibility and blocked network/live-model/database transports. All 297
repository tests pass on Python 3.14.7. SQLite behavior and scripted decisions
do not qualify live ClickHouse, model behavior or Phase 2/3. A runtime SQL
provenance remedy is separate work and requires approval before activation.
