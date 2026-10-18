# Verified Project Status

_Last reviewed for approved schema-v1 activation on 2026-10-17._

## Scope observation v1 candidate — review required before execution

This branch proposes a separate `runtime-sql-scope-v1` observation amendment.
Executed canonical/aliased/equivalent active-work SQL now supplies scope without
a fabricated result label; all-item, uppercase-literal and OR-bypass labels are
ignored. Independent seed-42/SQLite controls use the real worker and unchanged
scorer with live clients blocked. The supported scope controls pass; a valid CTE
remains unknown and a literal-metric false positive remains a grader defect.
No overall evaluator acceptance or new Treatment A is claimed. Owner approval
of the versioned amendment is pending; frozen methods/fixtures stay unchanged.
See `experiments/runtime-scope-v1/` and the separate proposed configuration.

## Passive capture v2 — offline only

The [versioned capture library](docs/passive-capture-v2.md) records public
model/tool boundary events, pre-query SQL, partial metrics and a durable worker
entry, preserving delegate results and errors without retries. It requires
explicit run authorization, configuration/source pins and a passed runtime
validity gate. Its CLI remains preflight-only; no live activation adapter or
new Treatment A attempt is included. The current scope-observation gate remains
blocked on this branch. Existing collectors and failed evidence remain intact.
Offline verification passed 25 focused tests and all 322 repository tests.
The subsequent JSON model-envelope trace-copy fix passed 29 focused tests and
all 326 repository tests. It omits named private JSON keys in trace copies and
records the original content hash without changing runtime/scorer objects.
This is not complete privacy redaction; ordinary and opaque text remain intact.

## Approved schema v1 activation, scope validity still blocked

The user approved `phase2-runtime-schema-v1` activation and one new bounded
standalone Treatment A after offline/preflight success. The exact reviewed patch
is applied on this isolated branch; its runtime fingerprint matches the approved
candidate. PR101 and the original execution pin are preserved, not merged.

Actual model-facing query-tool payloads match across existing structured and
multi-source System Benchmark paths. Document/no-tool paths retain their limits.
The strong-single adapter and independent parity review remain future comparison
gates; no historical configuration without equivalent schema may be compared.

A real fixture integration characterization found that a valid active-work query
without a returned scope alias scores `missing_expected_value`. The user chose
runtime SQL evidence and to resolve this before any live attempt. No attempt has
been consumed. A separate versioned scope-observation amendment must be reviewed
before activation; frozen scorer and task/reference criteria remain unchanged.

The obsolete inactive-proposal-only test is preserved on PR101; this activation
branch replaces it with actual model-payload parity and the six candidate tests.

## Historical checkpoint: post-run diagnosis and inactive fix proposal v1

The following paragraph records the earlier inactive proposal branch. The
approved activation above supersedes its inactivity statement on this branch;
PR101 and the original execution worktree remain preserved.

The October 17 pinned Treatment A remains failed and unscored. Existing server
file logs correlate the error to query ID `d6e97785-4a0d-4e9c-ae5a-2590c536f194`:
code 47 `UNKNOWN_IDENTIFIER`, caused by `snapshot = 'seed-42'` in SQL against a
table with no `snapshot` column. A later read-only DESCRIBE corroborated the
schema; no failed SQL or Treatment A was replayed.

`proposals/phase2-runtime-schema-v1/` contains an inactive patch for owner review.
It supplies column metadata and preserves bounded HTTP/server error identifiers.
It is not applied to this branch's runtime source, the frozen execution pin, or
main. Approval of a new tool-context/capture contract and a new execution pin is
required before activation; any further live Treatment A requires separate
explicit authorization. No scorer, data, budget, SQL guard or frozen method was
changed. Existing raw evidence and its original report remain historical records;
the diagnosis is a separate addendum.

_Phase 2 preparation checkpoint: 2026-10-12. Historical implementation details below retain their original evidence boundaries._

## Phase 2 readiness checkpoint — 2026-10-12

The active gate remains issue #73: one bounded Treatment A run on development task SB-D01, followed by evidence capture and a stop. Treatment B and later research phases are not part of this continuation.

This isolated preparation branch combines current main `58add5e58e581be21d3511fc4cd2cb5be44f49b7` (the already-landed active-work SB-D01 correction from #80) with the exact two-file local-runtime repair previously recorded at `84263bfdadfd3f07a81ed7133456287e687146ba`. It restores the intended local request limits, `num_predict=512` and `num_ctx=65536`. No new prompt, tool, SQL-guard, scorer, reference, dataset, model-identity, or task changes are introduced here. This branch is prepared solely for the authorized SB-D01 slice, not a new frozen Q1–Q6 run.

The current session could inspect GitHub and run deterministic mocked checks, but could not access the required Mac workspace, Ollama model, or ClickHouse service. **No fresh Treatment A run or deterministic benchmark score was produced. Phase 2 remains incomplete.** See `docs/phase2-treatment-a-continuation-2026-10-12.md` for the pinned continuation procedure and evidence requirements.

Historical #73 and successor SB-D01 attempts remain unsuccessful/unscored. Passing capability micro-studies in successor branches are not accepted SB-D01 results. Those branches also have separate enforcement controls and protocols; do not silently substitute them for this A-only continuation.

## Previous verified implementation state

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
