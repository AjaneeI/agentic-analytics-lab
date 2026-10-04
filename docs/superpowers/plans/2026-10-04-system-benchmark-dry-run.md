# System Benchmark Dry-Run Implementation Plan

> Execute inline with superpowers:executing-plans. Do not invoke coding/review agents.

**Goal:** Rehearse the seven development cases end-to-end with actual local evidence
and demonstrate that predefined corruptions fail for their intended reasons.
**Architecture:** Existing contracts/scorer, a guarded evidence gateway, a labelled
seed-42 SQL replay backend, and trusted scripted responses. Immutable JSON trace
snapshots separate worker declarations from observed backend outputs.
**Tech stack:** Python standard library; existing policy retriever and SQL validator.
**Spec:** ../specs/2026-10-04-system-benchmark-dry-run-design.md

## Global constraints

No Codex credits, model invocation, held-out exposure, paid dependency, or changes
to frozen Q1-Q6/data/prompt/agent/tool boundaries. Serial writes on an isolated
branch. Existing policy corpus unchanged. No automatic-review readiness event.

## Review focus

- Right + wrong version together must still fail: scorer regression.
- bool/numeric coercion and enormous integers: scorer regressions.
- Rejected calls must never reach backend and cannot claim tool success: gateway tests.
- Worker-mutated returns and forged handoff citations must not rewrite provenance: gateway/record tests.
- Scope mismatch, reference inconsistency, zero-call cases and unexpected fault failure: rehearsal tests.

## Task 1 — Reference/scorer integrity
- [x] Add tests/system_benchmark/test_execution_scoring_regressions.py; observe RED
  for mixed policy versions, bool/numeric coercion and integer overflow.
- [x] Make minimal corrections in src/evals/system_benchmark/scoring.py; run tests.
- [x] Pin SB-D01 active population through generated seed-42 rows in rehearsal tests;
  correct only that development fixture with before/after provenance.

## Task 2 — Guarded execution record
- [x] Add tests/system_benchmark/test_execution.py with explicit missing-module RED,
  then behavior tests for deny-before-dispatch, type/size/call limits, result isolation,
  invalid responses, heldout rejection and grounding.
- [x] Implement src/evals/system_benchmark/execution.py: PublicTask, WorkerOutput,
  ToolEvent, ToolGateway, ExecutionRecord, execute_task(...), canonical_json(...).
- [x] Run focused then full unittest discovery, record actual results.

## Task 3 — Real-evidence dry-run
- [x] Add tests/system_benchmark/test_dry_run.py for seven controls, policy/as-of,
  data-scope computation, fault detection and model/network-free execution.
- [x] Implement src/evals/system_benchmark/dry_run.py and
  scripts/run_system_benchmark_dry_run.py; backend replay and scripts do not read
  reference expectations. Preserve stable provenance and original negative traces.
- [x] Reproduce canonical artifact across processes/hash seeds/Python 3.11/3.12/3.13.

## Task 4 — Verification and preservation
- [x] Self-review full diff; add bounded adversarial regressions for discovered gaps.
- [x] Run full supported tests, compilation, context checker and git diff --check.
- [x] Save report under experiments/system-benchmark-dry-run-v1/ with precise boundaries.
- [x] Update STATUS, benchmark README and D-011. Preserve original Q1-Q6 hashes.
- [ ] Publish tested branch without force; dispatch Python tests/CodeQL and inspect logs.
- [ ] Reconcile GitHub/Notion/Asana with actual candidate/merge state and cost correction.
