# Verified Project Status

_Last reviewed against System Benchmark v1 PR C work on 2026-10-04._

## Current verified state

- The frozen Q1–Q6 benchmark remains unchanged historical/bounded evidence.
- The project keeps the single-agent, oracle-metadata routed, and
  natural-language routing evaluation lanes distinct.
- System Benchmark v1 is the active architecture-level evidence program.
- PR A (#63) merged typed task/response contracts, deterministic fixture
  loading, fingerprint inputs, and model-free validation.
- PR B (#65) merged as c5accae, establishing repository-local deterministic
  policy retrieval. It does not establish model quality.
- PR C (#66) is the active implementation slice.

## PR C implementation candidate

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

## Next gate

Publish the tested candidate on an isolated branch without a Codex review
trigger, obtain supported-version Python and CodeQL evidence, then review and
integrate only after the zero-Codex trigger boundary is preserved.

## Evidence boundary

Landing PR C establishes the deterministic evaluation core only. It does not
establish single-agent or routed-agent superiority, unseen-task generalization,
or publication-ready benchmark results.

## Staleness rule

This file is not authoritative when it conflicts with repository evidence.
GitHub issues, PRs, commits, workflow runs, tests, and benchmark artifacts take
precedence.
