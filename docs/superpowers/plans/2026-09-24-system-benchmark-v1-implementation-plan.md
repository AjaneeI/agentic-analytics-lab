# System Benchmark v1 Implementation Plan

**Status:** Proposed implementation plan, awaiting Ajanee approval  
**Date:** 2026-09-24  
**Approved design:** PR #52, commit `dc202eb2396674842a387dea0a187dc3194ede7a`  
**Tracking issue:** #49  
**Planning-time main:** `5160d15757aab6644395848d03c6ad02d0c66b1a`  
**Scope:** Planning only. This document does not authorize implementation.

## 1. Implementation objective

Implement System Benchmark v1 as a benchmark family separate from the frozen Q1-Q6 microbenchmark, using:

- the existing seed-42 read-only ClickHouse dataset,
- a small version-controlled local policy corpus,
- deterministic handlers for exactly solvable tasks,
- one strong qwen2.5:7b local-agent baseline with access to both safe evidence tools,
- the existing deterministic/local/escalate route vocabulary with capability/disposition metadata,
- deterministic scoring and reference solutions,
- strict dev/held-out separation,
- three matched evidentiary trials per approved configuration,
- observable failure localization,
- provenance and validated-goodput measurement.

The implementation must be capable of showing that the simpler architecture is better.

## 2. Hard invariants

Implementation must not:

- edit `evals/questions.json`,
- change frozen Q1-Q6 expected values or scoring semantics,
- change the seed-42 delivery data,
- silently change qwen2.5:7b as the analytical comparison anchor,
- add an LLM judge to frozen or System Benchmark primary scoring,
- collect chain-of-thought,
- adopt ASSERT, Phoenix, OpenTelemetry, or NeMo Guardrails without a separately demonstrated need,
- add specialist model agents in v1,
- add paid external APIs,
- add production/private data or write-capable analytical tools,
- consume Codex credits,
- treat development results as held-out evidence,
- treat oracle routing as deployable routing performance.

All implementation work uses TDD and verification-before-completion.

## 3. Live dependency reconciliation

The planning-time repository differs from the design-time snapshot.

Current main is `5160d15757aab6644395848d03c6ad02d0c66b1a`, which merged PR #53, a visual project-health reporting feature. That change is orthogonal to System Benchmark v1 and does not alter benchmark semantics.

The following relevant PRs remain open drafts based on the earlier `4e22b6f...` main:

| PR | Role | Dependency treatment |
| --- | --- | --- |
| #45 | Architecture/dependency documentation | Optional documentation dependency; not on critical path |
| #46 | Failure diagnostics, provenance, efficiency metrics | **Required reconciliation before System Benchmark provenance/diagnostic integration** |
| #47 | Natural-language routing evaluation | **Required reconciliation before route-interface freeze and held-out routing freeze** |
| #48 | Bounded validated-throughput runner | Optional until systems-performance phase; reuse if merged |
| #51 | Model-sensitivity runner | Not a System Benchmark v1 dependency |
| #52 | Approved System Benchmark v1 design | **Must be landed or otherwise fixed as canonical before implementation branch work** |

### Dependency policy

Do not duplicate code from #46, #47, or #48 while those PRs are unresolved.

Before implementation begins:

1. refresh each critical PR against current main,
2. determine whether its final implementation still satisfies the approved System Benchmark design,
3. merge or explicitly supersede #46 and #47,
4. record the exact dependency SHAs,
5. decide whether #48 should land before or after capability implementation.

If #46 or #47 materially changes during review, update this plan before code begins rather than silently adapting implementation scope.

## 4. Proposed source layout

System Benchmark v1 should be visibly separate from Q1-Q6.

```text
evals/
└── system_benchmark/
    ├── README.md
    ├── corpus/
    │   ├── manifest.json
    │   └── *.md
    ├── dev_tasks.json
    ├── reference_solutions.json
    ├── heldout_tasks.json              # added only at freeze gate
    └── route_robustness.json           # added only at freeze gate

src/
├── evals/
│   └── system_benchmark/
│       ├── __init__.py
│       ├── contracts.py
│       ├── loader.py
│       ├── scoring.py
│       ├── reference.py
│       ├── routing.py
│       ├── diagnostics.py
│       ├── runner.py
│       └── reporting.py
└── tools/
    └── policy_retrieval.py

scripts/
├── validate_system_benchmark.py
└── run_system_benchmark.py

tests/
└── system_benchmark/
    ├── test_contracts.py
    ├── test_loader.py
    ├── test_policy_retrieval.py
    ├── test_scoring.py
    ├── test_reference.py
    ├── test_routing.py
    ├── test_diagnostics.py
    ├── test_runner.py
    └── test_reporting.py

.github/workflows/
└── system-benchmark.yml
```

Names may shift slightly to match merged #46/#47 conventions, but the benchmark-family separation must remain obvious.

## 5. Response and task contracts

### Worker response envelope

Create a System Benchmark-specific normalized result contract with:

- `disposition`: answer | clarify | unsupported | handoff
- `answer_text`
- `evidence_refs`
- `uncertainty`
- optional `clarification`
- optional `handoff`

The handoff object contains:

- trigger,
- evidence_refs,
- actions_taken,
- unresolved_uncertainty,
- requested_authority.

### Task contract

Each task records:

- case ID,
- benchmark version,
- family,
- split,
- user request,
- expected top-level route,
- expected capability profile,
- allowed/forbidden dispositions,
- required evidence source types,
- acceptable source IDs,
- expected structured values and tolerances,
- required claims,
- forbidden claims,
- required clarification concept where applicable,
- required handoff fields where applicable,
- allowed/forbidden tools,
- reference solution ID.

Ground truth describes semantic requirements, not one mandatory tool trajectory.

## 6. TDD and PR sequence

Implementation should be split into narrow pull requests. Each PR must leave the repository green and must not claim evidence from code that has not merged.

### PR A — Benchmark contract foundation

**Goal:** Establish the System Benchmark namespace, schemas/contracts, fixture loader, and deterministic validation without executing an LLM.

**Production files:**

- `src/evals/system_benchmark/__init__.py`
- `src/evals/system_benchmark/contracts.py`
- `src/evals/system_benchmark/loader.py`
- `evals/system_benchmark/README.md`
- `scripts/validate_system_benchmark.py`

**Tests first:**

- `tests/system_benchmark/test_contracts.py`
- `tests/system_benchmark/test_loader.py`

**TDD sequence:**

1. Write tests that reject invalid family, split, route, capability, disposition, duplicate IDs, malformed tolerance, missing source requirements, and incomplete handoff/clarification contracts.
2. Confirm tests fail for missing implementation.
3. Implement the smallest typed contracts and loader.
4. Add fixture-level fingerprint input enumeration.
5. Run focused tests, then full Python 3.11/3.12 tests and CodeQL.

**Acceptance:**

- invalid tasks fail before execution,
- Q1-Q6 files are byte-for-byte unchanged,
- no model/tool runtime is needed for schema validation.

**Depends on:** approved/landed design and current clean main.

---

### PR B — Local policy corpus and deterministic retrieval

**Goal:** Add the genuinely different evidence source without a framework dependency.

**Fixture files:**

- `evals/system_benchmark/corpus/manifest.json`
- KPI dictionary
- blocker-definition policy
- delivery operating policy
- escalation policy
- service-level policy
- analytical interpretation guide

**Production file:**

- `src/tools/policy_retrieval.py`

**Tests first:**

- `tests/system_benchmark/test_policy_retrieval.py`

**TDD cases:**

1. current policy beats superseded version by default,
2. explicit as-of date returns the applicable version,
3. overlapping terminology requires section-level ranking,
4. stable tie-breaking is deterministic,
5. top-k is bounded,
6. missing query returns an inspectable empty result,
7. path traversal is rejected,
8. corpus allowlist is enforced,
9. excerpt length is bounded,
10. returned evidence includes document/version/section identity.

**Implementation constraint:**

Use deterministic repository-local retrieval first. Prefer standard-library normalization/scoring and manifest filtering. Do not introduce embeddings, a vector database, or paid retrieval APIs in v1.

**Acceptance:**

- repeated identical retrievals return identical ranked evidence,
- every returned excerpt is traceable to immutable repo content,
- security tests prove corpus-bound read-only access.

**Depends on:** PR A.

---

### PR C — Deterministic graders, reference solutions, and development set

**Goal:** Prove the benchmark can objectively score every family before connecting a live model.

**Production files:**

- `src/evals/system_benchmark/scoring.py`
- `src/evals/system_benchmark/reference.py`
- `evals/system_benchmark/dev_tasks.json`
- `evals/system_benchmark/reference_solutions.json`

**Tests first:**

- `tests/system_benchmark/test_scoring.py`
- `tests/system_benchmark/test_reference.py`

**Development task target:** 24 tasks, exactly 3 per family A-H.

**Required scorer dimensions:**

- disposition validity,
- structured-value correctness and tolerance,
- evidence presence,
- evidence completeness,
- document/policy identity,
- required claims,
- forbidden claims,
- unsupported-source honesty,
- clarification concept,
- handoff structure,
- security/validator outcome.

**Reference gate:**

Every development task must have a known-good reference response that passes every applicable grader.

A failing reference solution blocks the task. Do not weaken the grader merely to make a reference pass; fix the inconsistency and add regression coverage.

**Acceptance:**

- all 24 development reference solutions pass,
- deliberate negative fixtures fail for the intended reason,
- no LLM judge is used,
- scoring is independent from natural-language router implementation.

**Depends on:** PR A and PR B.

---

### PR D — Routing treatments and worker adapters

**Goal:** Separate route quality from worker quality and connect the approved baselines.

**Production files:**

- `src/evals/system_benchmark/routing.py`
- worker adapter code in the System Benchmark namespace or the smallest compatible existing module.

**Tests first:**

- `tests/system_benchmark/test_routing.py`

**Treatments:**

1. deterministic/simple execution,
2. strong single qwen2.5:7b agent with both safe evidence tools,
3. oracle routing,
4. natural-language router,
5. simple inspectable routing heuristic.

**Compatibility rule:**

Retain top-level execution routes:

- deterministic,
- local,
- escalate.

Add capability profile:

- none,
- structured,
- documents,
- multi_source.

Add escalation/disposition metadata rather than new specialist agents.

**Routing metrics:**

- route accuracy,
- capability-profile accuracy,
- confusion matrix,
- false-cheap routes,
- unnecessary escalations,
- unsupported-source misses.

**TDD cases include:**

- alternate route may still pass task outcome but fail route-quality checks,
- oracle metadata never enters natural-language router inputs,
- strong single agent receives both safe tools,
- family H gathers bounded evidence and returns handoff rather than making the decision,
- unsupported-source requests cannot fabricate capability.

**Acceptance:**

- route inference can run without worker execution,
- worker execution can run under oracle route independently,
- a routing failure can be distinguished from worker failure.

**Hard dependency:** #47 reconciled/merged or explicitly superseded before this PR begins.

---

### PR E — Failure diagnostics, runner, artifacts, provenance

**Goal:** Execute development tasks with observable failure localization and complete run provenance.

**Production files:**

- `src/evals/system_benchmark/diagnostics.py`
- `src/evals/system_benchmark/runner.py`
- `src/evals/system_benchmark/reporting.py`
- `scripts/run_system_benchmark.py`

**Tests first:**

- `tests/system_benchmark/test_diagnostics.py`
- `tests/system_benchmark/test_runner.py`
- `tests/system_benchmark/test_reporting.py`

**Failure-stage contract:**

1. preflight
2. routing
3. tool_selection
4. query_validation
5. query_execution
6. evidence_coverage
7. answer_synthesis
8. validation
9. none

Use only observable events. Do not infer hidden reasoning.

**Runner isolation:**

- fresh agent instance per task,
- fresh temporary directory per trial,
- immutable fixtures,
- explicit timeout,
- concurrency 1 for capability evidence,
- controlled caches,
- no cross-trial mutable state.

**Artifacts:**

- `manifest.json`
- `reference_validation.json`
- `results.jsonl`
- `routing_metrics.json`
- `diagnostics.json`
- `summary.json`

**Provenance:**

- Git SHA,
- benchmark version,
- contract fingerprint,
- task-set version,
- dataset seed/version,
- corpus fingerprint,
- model/runtime/settings,
- scorer fingerprint,
- route/tool configuration,
- timeout/resource settings,
- timestamp,
- artifact IDs/CI URL when applicable.

**Compatibility requirement:**

Reuse #46 provenance/diagnostic primitives if their merged contract fits. Add an adapter where necessary; do not rewrite historical Q1-Q6 diagnostics.

**Hard dependency:** #46 reconciled/merged or explicitly superseded before this PR begins.

---

### PR F — Development benchmark integration and regression proof

**Goal:** Run the complete development benchmark to prove interfaces, graders, references, route separation, and artifacts work before held-out creation.

**No public architecture claim is produced from this phase.**

**Work:**

- run all 24 development tasks through approved baseline/treatment plumbing,
- audit every grader disagreement,
- validate reference and model artifacts,
- inspect failure-stage classifications,
- confirm no benchmark task can access hidden ground truth,
- confirm Q1-Q6 regressions remain green.

**Required review:**

Human audit of:

- all 24 task contracts,
- all reference solutions,
- at least one passing and one failing trial from each family,
- any scorer edge case discovered during development.

**Exit criterion:**

Freeze the following interfaces:

- task contract,
- worker response envelope,
- tool contracts,
- scoring rules,
- route contract,
- corpus v1,
- artifact schema.

Only after this freeze may the held-out task set be finalized.

**Depends on:** PR C, PR D, PR E.

---

### PR G — Held-out freeze and routing robustness set

**Goal:** Create the evidence set only after interfaces and scoring are frozen.

**Files added:**

- `evals/system_benchmark/heldout_tasks.json`
- `evals/system_benchmark/route_robustness.json`

**Held-out target:** 24 tasks, 3 per family.

**Perturbation target:** 24 route-only variants from 12 held-out semantic cores:

- one surface-noise/typo variant,
- one meaning-preserving paraphrase or extra-wording variant.

**Pre-freeze verification:**

- reference solutions pass,
- no held-out task was used in development,
- no task wording exposes expected route or source identity unnecessarily,
- each family includes novel combinations/wording,
- perturbations preserve task meaning,
- benchmark/task/corpus fingerprints are recorded.

**Contamination policy:**

After the first evidentiary use, failures may be analyzed but not used to tune and rerun against the same set while calling it held-out. Any such tuning requires a new held-out version.

**Depends on:** PR F freeze approval.

---

### PR H — CI and manual evidentiary workflow

**Goal:** Make deterministic validation continuous while keeping expensive local-model evidence explicit and controlled.

**Workflow file:**

- `.github/workflows/system-benchmark.yml`

**PR CI lane:**

- schema validation,
- corpus validation,
- reference checks,
- grader tests,
- route-fixture tests,
- security tests,
- Python 3.11/3.12,
- CodeQL.

**Manual evidence lane:**

Use `workflow_dispatch` or the repository's established equivalent to execute frozen configurations.

Do not run the full local qwen2.5:7b System Benchmark on every PR.

**Throughput integration:**

If #48 is merged and still fits the design, reuse its bounded-concurrency/validated-goodput primitives in a separate systems experiment. Capability evidence remains concurrency 1.

**Acceptance:**

- deterministic CI is green,
- manual workflow records the exact frozen commit,
- artifacts are uploaded even when a benchmark trial fails,
- a failed artifact-collection step fails the run rather than silently losing evidence.

**Depends on:** PR E and PR G. #48 optional.

---

### Evidence Run — Three matched trials

**Goal:** Produce the first official System Benchmark v1 evidence without implementation changes during the run.

Approved configurations should minimally include:

1. strong single agent,
2. deterministic/simple execution where applicable,
3. oracle routing,
4. simple routing heuristic,
5. natural-language routed system.

Run exactly three matched trials per stochastic evidentiary configuration.

**Report:**

- aggregate task success,
- family macro-average,
- 3/3 stable-pass rate,
- unstable-task rate,
- route quality,
- grounding/evidence completeness,
- failure-stage distribution,
- total/median/P95 latency,
- model calls,
- tool calls,
- input/output tokens,
- model-duration seconds where available,
- model seconds per successful task,
- raw requests/minute if measured,
- validated tasks/minute.

Do not collapse these into a single composite agentic score.

**No benchmark code changes are allowed between matched trials.**

---

### Results PR — Interpretation and public claim review

**Goal:** Publish evidence-backed conclusions while preserving claim boundaries.

**Required analysis:**

- where deterministic handling dominates,
- where the single agent is sufficient,
- where multi-source access materially helps,
- oracle-versus-natural-router gap,
- false-cheap routing cost,
- unnecessary escalation cost,
- failure-stage concentrations,
- quality/latency/cost-proxy tradeoffs,
- whether routed complexity earned adoption.

**Public claim gate:**

Every claim must name:

- System Benchmark version,
- held-out task distribution,
- model/runtime,
- configuration,
- number of matched trials.

A result that favors the simpler architecture is a valid and publishable outcome.

## 7. Dependency graph

```text
Approved design (#52)
        │
        ├──────────────► Reconcile #46 ─────┐
        │                                   │
        ├──────────────► Reconcile #47 ─────┤
        │                                   │
        └──────────────► #48 optional       │
                                            │
PR A Contracts ──► PR B Corpus/Retrieval ──► PR C Graders + Dev Set
                                            │
#47 ───────────────────────────────────────► PR D Routing + Workers
                                            │
#46 ───────────────────────────────────────► PR E Runner + Diagnostics + Provenance
                                            │
PR C + PR D + PR E ────────────────────────► PR F Development Integration/Freeze
                                            │
                                            ▼
                                     PR G Held-out Freeze
                                            │
                                            ▼
                                     PR H CI/Evidence Lane
                                            │
                                            ▼
                                  Three Matched Evidence Runs
                                            │
                                            ▼
                                   Results/Claim Review PR
```

## 8. What can run in parallel

After PR A lands:

- corpus authoring/retrieval work in PR B can proceed while #46/#47 are being reconciled,
- deterministic scorer design for known fixture shapes can begin after PR B fixture identities stabilize,
- #46 and #47 reconciliation can proceed independently,
- #45 documentation can progress independently,
- #51 remains fully independent.

Do **not** parallelize:

- held-out task authoring with active dev-set tuning,
- official evidence runs with code changes,
- competing implementations of provenance/routing while #46/#47 are unresolved,
- load experiments with capability evidence.

## 9. Verification matrix

| Gate | Required verification |
| --- | --- |
| Contracts | invalid fixture tests fail correctly; full tests green |
| Retrieval | deterministic ranking, versioning, path guard, bounded output |
| Scoring | reference solutions pass; negative fixtures fail intentionally |
| Routing | route-only metrics independently reproducible |
| Worker | oracle-routed execution isolates worker performance |
| Diagnostics | synthetic failure fixtures map to exact observable stages |
| Provenance | fingerprints change when contract/corpus/scorer changes |
| Isolation | repeated trials cannot see prior temp state |
| Held-out | no dev exposure; references pass before first model run |
| CI | Python 3.11/3.12 + CodeQL + artifact retention |
| Evidence | three matched trials from one frozen commit |
| Claims | every public claim traceable to stored artifacts |

## 10. Code review and security process

For each implementation PR:

1. write failing tests first,
2. implement the smallest passing change,
3. run focused tests,
4. run full Python test matrix,
5. run CodeQL,
6. review GitHub Actions changes with actionlint/zizmor only if already available or separately justified,
7. request CodeRabbit review,
8. verify each actionable finding technically,
9. fix verified issues without broadening scope,
10. re-run checks,
11. record exact evidence before declaring completion.

GitHub Copilot review is optional supplemental evidence only.

Codex is not authorized.

## 11. Asana abstraction

Asana should track outcomes and gates, not file-level implementation.

Recommended execution tasks:

1. Reconcile System Benchmark prerequisites (#46/#47; #48 decision).
2. Land benchmark foundation and local policy evidence lane.
3. Prove deterministic graders on the 24-task development set.
4. Freeze routing/worker contracts and development benchmark.
5. Freeze held-out System Benchmark v1.
6. Complete CI/manual evidence lane.
7. Run three matched evidentiary comparisons.
8. Review and publish evidence-backed conclusions.

Detailed technical subtasks remain in GitHub.

## 12. Stop conditions

Stop implementation and return to design/planning if:

- a task family cannot be objectively graded without an LLM judge,
- local document retrieval requires an external framework to function acceptably,
- #46/#47 merged contracts materially conflict with the approved design,
- a proposed specialist agent appears necessary,
- held-out contamination occurs,
- the benchmark requires write access or private systems,
- evidence collection cannot be reproduced from a pinned commit.

Any of these requires explicit review rather than silent scope expansion.

## 13. Implementation approval gate

This plan is the second required gate.

**No System Benchmark v1 implementation branch should be created from main until Ajanee explicitly approves this implementation plan.**

After approval:

1. reconcile and land/supersede the prerequisite PRs,
2. record the then-current clean `main` SHA,
3. create the first narrow implementation branch for PR A,
4. begin with failing contract/loader tests,
5. proceed through the PR sequence above with verification at every gate.
