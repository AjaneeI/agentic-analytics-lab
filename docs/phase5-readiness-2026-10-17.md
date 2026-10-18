# Phase 5 preparation: development bank readiness

This is model-free preparation under the October 17–23 acceleration sprint
(issues #94/#95), based on code head `58add5e`. It does not assert Phase 5
entry, acceptance of Phases 2–4, a frozen interface, or architecture quality.
The sprint authorization does not permanently supersede D-010.

## Reproduce the audit

From the repository root, run:

```sh
python3 scripts/validate_system_benchmark.py
python3 scripts/audit_system_benchmark_readiness.py
python3 -m unittest tests.system_benchmark.test_readiness_report
```

The readiness command prints JSON to stdout and returns **2** when readiness
is blocked. It writes no artifacts. Invalid fixture input raises a validation
error. The command deliberately has no held-out input option and cannot grant
phase acceptance. It uses only development contracts and local policy retrieval;
it performs no model calls, database queries, or worker execution. An isolated
test blocks network audit events and checks that no model client is imported.
The existing `src.routing` package imports inert single-agent/SQL-tool
definitions; their presence alone is not a model call or database connection.

The report reuses the existing freeze auditor without changing its semantics.
It adds task/reference counts, orphan-reference detection, policy-reference
identity probes, route-only diagnostics, and checks of the existing routed and
strong-single invocation tool contracts. A policy probe queries a document ID
at the referenced version's effective date; it proves bounded retrievability,
not that a model will select that evidence from the user's request.

## Current gap audit

| Family | Active tasks | Needed to reach three |
| --- | --- | --- |
| A — structured deterministic analytics | 1 | 2 |
| B — tool-grounded analytical reasoning | 0 | 3 |
| C — document/policy retrieval | 2 | 1 |
| D — multi-source synthesis | 1 | 2 |
| E — ambiguity/clarification | 1 | 2 |
| F — epistemic/causal reasoning | 0 | 3 |
| G — unsupported-source handling | 1 | 2 |
| H — human authority handoff | 1 | 2 |
| **Total** | **7** | **17** |

All seven task/reference expectation pairs validate. All four distinct allowed
policy reference identities are retrievable, including historical version 0.9.
There are no orphan references and the inspected worker invocation checks pass.
These are contract checks: `development_references.json` stores expectations,
not complete known-good worker response/observation artifacts. This audit does
not prove that every reference response passes the scorer. That separate gate
remains required for all 24 tasks, together with deliberate negative cases and
human review.

Route-only diagnostics on the seven inspectable development cases:

| Treatment | Route correct | Capability correct | False cheap | Unsupported misses |
| --- | --- | --- | --- | --- |
| Oracle metadata | 7/7 | 7/7 | 0 | 0 |
| Natural-language baseline | 1/7 | 4/7 | 3 | 1 |
| Simple heuristic | 2/7 | 4/7 | 2 | 0 |

Oracle correctness follows from supplied metadata. No router was tuned. None
of these numbers measures worker success, model quality, or generalization.

## Baseline and interface gaps

The existing contract and regression tests cover the three execution routes,
four capability profiles, free-text route inputs, policy version identity,
routed tool intersection, and hard G/H response boundaries. This preparation
changes none of those interfaces, the corpus, or the scorer. Passing these
checks does not approve freezing them.

`src/evals/system_benchmark/workers.py:build_strong_single_invocation` exposes
both safe tools. However,
`src/evals/system_benchmark/local_worker.py:BoundedLocalExecutor.__call__`
always uses `build_worker_invocation` with a route decision; it does not call
`build_strong_single_invocation`. Consequently the
invocation builder alone is not a complete strong-single treatment. Its default
`DEFAULT_LOCAL_MODEL = "hermes-local:qwen3.5-9b"` in that same runtime module
belongs to the separate Treatment A remediation;
the v1 design's comparison anchor is `qwen2.5:7b`. Treatment A acceptance must
not silently replace that anchor or imply acceptance of another treatment.

`src/routing/deterministic_handlers.py:execute_deterministic_handler` and its
injected-query unit tests establish bounded implementation behavior. This
preparation does not demonstrate a
System Benchmark deterministic/simple executor producing response envelopes
and runner artifacts for the applicable development cases. A route labelled
`deterministic` is not proof that execution uses a deterministic handler.

Before a full development run, prepare and verify explicit baseline adapters:

1. Deterministic/simple execution only for exactly solvable approved cases,
   declining unsupported cases rather than reading reference answers.
2. A strong single-agent treatment with both safe tools and no benchmark
   route classifier choosing its capability. Task scoring still enforces
   prohibited tool use and response boundaries.
3. Preserve model/runtime/settings provenance and an explicit accepted decision
   if a comparison anchor differs from the v1 design.

No adapters or runtime changes are activated by this readiness work.

## Required gates still open

- Accepted Phase 2–4 evidence and sprint authorization must be checked by the
  parent workflow; this audit cannot infer their acceptance.
- A separate expansion decision and human audit must approve the 17 proposed
  additions before activating a revised development bank. See
  [the draft proposal](phase5-development-expansion-proposal.md).
- All 24 complete reference response/observation pairs must pass the existing
  deterministic scorer. Negative cases must fail for the intended reasons.
- Approved deterministic/simple and strong-single baseline plumbing must be
  runnable, with traceable observations and no hidden-ground-truth access.
- The complete development run, grader disagreement review, failure attribution,
  Q1–Q6 regressions, and human review of a passing/failing trial per family must
  precede an interface-freeze decision.

The existing implementation plan's PR F freeze gate remains the authority for
its required task/reference/trial review. No held-out data was read or created.

## Local implementation verification

Python 3.14.7: five focused readiness tests pass; all 294 repository unit
tests pass with `python3 -m unittest discover -s tests -v`. Development fixture
validation and Project Context Protocol checks pass. The readiness command
returns the expected blocked exit 2. These are local implementation/regression
checks, including the frozen Q1–Q6 hash assertion. Hosted Python 3.11/3.12 and
CodeQL have not run for this candidate.
