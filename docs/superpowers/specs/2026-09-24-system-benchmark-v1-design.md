# System Benchmark v1 Design

**Status:** Proposed design, awaiting approval  
**Date:** 2026-09-24  
**Canonical tracking issue:** https://github.com/AjaneeI/agentic-analytics-lab/issues/49  
**Technical source of truth:** GitHub  
**Scope:** Design only. This specification does not authorize benchmark implementation, held-out execution, or changes to the frozen Q1-Q6 benchmark.

## 1. Purpose

System Benchmark v1 is a second, independent benchmark family for Agentic Analytics Lab. Its purpose is to measure when routed or agentic system complexity creates measurable value under heterogeneous analytical work, and when a simpler architecture remains preferable.

The benchmark must be capable of producing a negative result. If a strong single local agent or deterministic path is more reliable, faster, or cheaper for the tested workload, that is a successful benchmark outcome.

System Benchmark v1 is not a larger rewrite of Q1-Q6. It adds a separate system-level evaluation layer with heterogeneous evidence sources, explicit route inference, observable failure localization, clarification and unsupported-source behavior, human handoff structure, and cost-performance measurement.

## 2. Research question

When does routed or agentic system complexity produce enough measurable improvement in analytical task performance, reliability, or efficiency to justify its additional latency, model use, tool use, operational complexity, and failure surface over a strong simpler baseline?

The benchmark operationalizes this question by separating three layers:

1. **Route inference:** Given only realistic user language, did the router choose an appropriate execution route and capability profile?
2. **Worker execution:** Conditional on an intended route, did the selected worker produce a correct, grounded, policy-consistent result?
3. **End-to-end system:** Did the deployed routing plus worker configuration complete the task successfully, reliably, and efficiently?

A routing failure must not be mislabeled as a worker failure, and oracle metadata must not be reported as deployable routing performance.

## 3. Existing benchmark relationship

The benchmark family is:

- **Microbenchmark:** frozen Q1-Q6, unchanged.
- **System Benchmark v1:** separate tasks, fixtures, graders, artifacts, versioning, and claim boundaries.

The following Q1-Q6 properties remain frozen:

- questions and expected answers,
- seed-42 delivery data,
- qwen2.5:7b analytical comparison anchor,
- deterministic scorer semantics,
- system prompt and existing tool contract for the frozen benchmark,
- read-only ClickHouse boundary,
- exactly three official evidentiary runs.

System Benchmark v1 may reuse the existing delivery dataset as one evidence source, but it must not mutate that dataset or alter Q1-Q6 to create system-level difficulty.

### Live dependency state at design time

At the time of this design, main is commit 4e22b6f4fbeab8183f5313de3b71865367faf6af, the squash merge of PR #43. PRs #45, #46, #47, #48, and #51 remain open drafts and are not authoritative implementation infrastructure.

Their useful design concepts are treated as proposed dependencies:

- PR #45: architecture/dependency documentation.
- PR #46: deterministic diagnostics, provenance, and efficiency metrics.
- PR #47: free-text routing evaluation and a simple lexical baseline.
- PR #48: bounded validated-throughput measurement.
- PR #51: model-sensitivity lane, which remains out of scope for System Benchmark v1 architecture comparisons.

System Benchmark v1 must tolerate those PRs changing before merge. It may reuse merged code later, but this design does not depend on unmerged behavior.

### ASSERT evidence reconciliation

The preserved ASSERT Q3 experiment is treated as a negative tool-evaluation result, not as System Benchmark infrastructure. GitHub evidence and the Notion evaluation record agree that the experiment preserved three canonical Q3 traces, encountered a qwen2.5:7b judge timeout, produced a bounded qwen2.5:3b retry, exposed a viewer-path defect after score production, and failed to add reliable diagnostic value for the actual R4/R5 answer-synthesis failure. ASSERT remains rejected for this use case and is not part of System Benchmark v1.

## Architecture alternatives considered

### Approach A: Minimal heterogeneous benchmark — recommended

Use the existing read-only ClickHouse dataset plus a small version-controlled local policy corpus. Keep one strong local analytical agent, deterministic handlers, the existing three coarse execution routes, and explicit clarification/escalation/handoff dispositions. Add no specialist model agents.

**Experimental value:** High. It introduces genuinely different evidence types and multi-source work without predetermining that multi-agent orchestration is useful.  
**Implementation complexity:** Moderate and bounded.  
**Scoring difficulty:** Moderate, mostly deterministic.  
**Runtime:** Manageable for three matched trials.  
**Reproducibility:** High.  
**Portfolio relevance:** High because it demonstrates routing, retrieval, grounding, policy application, escalation, and system economics.  
**Risk of manufacturing complexity:** Low.

### Approach B: Split capability workers

Introduce separate analytical and document-specialist model workers plus a synthesis/orchestration path.

**Experimental value:** Potentially high if specialist workers are behaviorally distinct.  
**Implementation complexity:** High.  
**Scoring difficulty:** Higher because orchestration introduces new failure surfaces.  
**Runtime:** Higher due to additional model calls.  
**Reproducibility:** Moderate.  
**Portfolio relevance:** High, but only if specialization is empirically necessary.  
**Risk of manufacturing complexity:** High because the architecture could create the benchmark advantage it is meant to measure.

This approach is deferred unless Approach A shows repeatable failures that a genuinely distinct specialist capability can plausibly solve.

### Approach C: Stateful interactive work environment

Add a simulated user, mutable state, write operations, and multi-turn decision workflows.

**Experimental value:** Highest external realism.  
**Implementation complexity:** Very high.  
**Scoring difficulty:** High.  
**Runtime:** High.  
**Reproducibility:** Lower due to state and interaction effects.  
**Portfolio relevance:** High later, but premature for v1.  
**Risk of manufacturing complexity:** Medium to high.

This is a future benchmark generation, not v1.

### Decision

Adopt Approach A for System Benchmark v1. It gives the benchmark enough heterogeneity to test the research question while preserving causal clarity. It intentionally creates conditions in which the strong single-agent baseline can still win.

## 4. Task taxonomy

System Benchmark v1 keeps all eight task families because each measures a distinct capability or control behavior.

| Family | Distinct capability measured | Primary expected behavior |
| --- | --- | --- |
| A. Structured deterministic analytics | Cheap bounded structured computation | Prefer deterministic execution when a handler can solve the task exactly |
| B. Tool-grounded analytical reasoning | Interpretation over structured evidence | Local agent uses structured data and makes a supported conclusion |
| C. Document/policy retrieval | Retrieval and version-aware policy interpretation | Local agent retrieves the correct current or requested policy evidence |
| D. Multi-source synthesis | Evidence integration across structured data and policy documents | Local agent uses both sources and cites both |
| E. Ambiguity / clarification / escalation | Knowing when immediate execution is incorrect | Clarify one missing decision variable or escalate a true conflict |
| F. Epistemic and causal reasoning | Appropriate uncertainty and inference limits | Reject unsupported causal/generalization claims and state what evidence is needed |
| G. Unsupported-source handling | Tool/access honesty | Recognize unavailable sources and do not fabricate access or evidence |
| H. Human handoff / authority boundary | Evidence-backed transfer of authority | Prepare a complete decision package rather than make an unauthorized decision |

Family H is distinct from Family E: the task may be fully specified and evidence may be available, but decision authority is intentionally outside the system.

### Initial task-set size

The target v1 task bank is:

- **Development:** 24 tasks, 3 per family.
- **Held-out:** 24 tasks, 3 per family.
- **Route-robustness companion set:** 24 route-only perturbations derived from 12 held-out semantic cores after freeze, with one surface-noise variant and one meaning-preserving paraphrase/extra-wording variant per selected core.

The route-robustness companion set is not included in worker task-success averages. It measures route stability only.

This size is intentionally small enough for careful human audit and three matched local-model trials, while giving every family repeated representation.

## 5. Data sources

### Structured source

Reuse the existing seed-42 synthetic delivery dataset in ClickHouse without modification.

The benchmark must continue using the dataset-scoped read-only account and the existing table/statement/resource guards.

### Document source

Add a small repository-local policy corpus with Markdown documents and a machine-readable JSON manifest.

Initial corpus:

- KPI dictionary,
- blocker-definition policy,
- delivery operating policy,
- escalation policy,
- service-level policy,
- analytical interpretation guide.

The corpus should include controlled overlap and edge cases:

- current and superseded policy versions,
- overlapping terminology,
- effective dates,
- explicit scope fields,
- at least one intentional policy conflict used only by ambiguity tasks,
- definitions that require section-level retrieval rather than filename matching.

The corpus manifest records document ID, version, status, effective date, scope, and path. The documents are immutable fixtures within a benchmark version.

No external SaaS, web retrieval, credentials, private data, or paid embedding service is required.

## 6. Tools and interfaces

### Existing structured-data tool

System Benchmark v1 reuses the existing ClickHouse read-only query capability. Its authorization and semantic guardrails remain unchanged.

### New local document capability

Add one read-only logical retrieval capability, provisionally named **retrieve_policy**.

Inputs:

- query text,
- optional as-of date,
- bounded top-k.

Outputs:

- document ID,
- document version,
- section ID,
- section text excerpt,
- effective date,
- status.

The v1 retriever should be deterministic and repository-local. The default design is a small section-level lexical scorer using standard-library text normalization, a stable tie-break, and manifest-aware version filtering. No embeddings framework is required.

The benchmark may expose direct section fetch by returned ID if implementation simplicity requires it, but the evidence identity must remain deterministic and auditable.

### Capability profiles

System Benchmark v1 does not add specialist model agents. Local-agent execution receives one of four capability profiles:

- **none**
- **structured**
- **documents**
- **multi_source**

The strong single-agent baseline receives both safe tools and must decide whether either is needed.

### System response contract

Every System Benchmark worker returns a normalized response envelope:

- disposition: answer, clarify, unsupported, or handoff,
- answer_text,
- evidence_refs,
- uncertainty,
- optional clarification object,
- optional handoff object.

The handoff object contains:

- trigger,
- evidence_refs,
- actions_taken,
- unresolved_uncertainty,
- requested_authority.

This structured envelope is a benchmark-facing interface, not a change to the frozen Q1-Q6 output contract.

## 7. Routing treatments

Preserve the existing top-level execution-route vocabulary for compatibility:

- deterministic,
- local,
- escalate.

System Benchmark v1 extends route evaluation with capability metadata rather than new agents.

A route decision is evaluated as:

- execution route,
- capability profile when local,
- reason code,
- escalation mode when applicable.

### Expected treatment by family

- A: deterministic.
- B: local + structured.
- C: local + documents.
- D: local + multi_source.
- E: escalate + clarify/conflict.
- F: local + none, unless the case explicitly requires checking a supplied benchmark result.
- G: escalate + unsupported_source.
- H: local + the evidence capabilities required by the case, followed by disposition=handoff.

Family H is deliberately not a generic early escalation. The worker must gather or interpret the bounded evidence needed to produce a decision package, then stop at the authority boundary.

### Route inference evaluation

Route inference receives only realistic user language and permitted static system context. It must not receive benchmark family labels, expected route metadata, or hidden ground truth.

Report:

- execution-route accuracy,
- capability-profile accuracy,
- confusion matrix,
- false-cheap routes,
- unnecessary escalations,
- unsupported-source misses,
- route-stability under perturbations.

A route mismatch is not automatically an end-to-end task failure. If a more expensive route still produces a correct answer, task success may pass while route quality and efficiency fail. This prevents brittle trajectory grading.

## 8. Baselines

### Baseline 1: Strong single agent

qwen2.5:7b via Ollama, using the System Benchmark response contract and access to both safe evidence tools.

No separate route classifier decides the worker. The agent must choose whether to use structured data, documents, both, or neither and must respect clarification, unsupported-source, and handoff boundaries.

This is the primary simplicity baseline.

### Baseline 2: Deterministic/simple execution where applicable

Use deterministic handlers only for tasks they can exactly and safely solve. This baseline is most relevant to Family A and explicit control-plane checks.

Do not stretch deterministic handlers into open-ended reasoning merely to raise their benchmark coverage.

### Baseline 3: Oracle routing

Use benchmark metadata to supply the intended route and capability profile.

Oracle routing is an execution upper bound and diagnostic treatment only. It answers whether the selected worker can solve the task when routing is correct.

It is never reported as deployable routing performance.

### Baseline 4: Natural-language router

Evaluate only after the free-text routing interface is stable and PR #47 or its successor has landed.

First measure route inference in isolation. End-to-end results are interpreted only after route and worker error rates are known separately.

### Baseline 5: Simple routing heuristic

Use an inspectable lexical/rule baseline before introducing any more complicated routing method.

A more complicated router must be compared against this baseline on task success, route quality, robustness, latency, and cost proxies. Beating random routing is not sufficient evidence.

## 9. Ground truth

Each task has a machine-readable contract containing:

- case ID and benchmark version,
- family,
- split,
- user request,
- expected top-level route,
- expected capability profile,
- allowed and forbidden dispositions,
- required evidence source types,
- required source IDs or acceptable source sets,
- expected structured values and tolerances where relevant,
- required claims,
- forbidden claims,
- required clarification concept when applicable,
- required handoff fields when applicable,
- allowed and forbidden tools,
- reference solution ID.

Ground truth should encode semantic requirements, not a single required tool-call sequence.

### Reference solutions

Every case must have a reference solution or reference state that:

1. proves the task is solvable,
2. proves the available tools expose sufficient information,
3. proves the expected outcome is internally consistent,
4. passes all automated graders.

Reference validation is a blocking preflight gate. If the reference solution fails, the task or grader is invalid and no model result from that case is used as architecture evidence until corrected and versioned.

## 10. Scoring

Prefer deterministic, inspectable graders.

### Primary task-success contract

A task passes only when all applicable requirements hold:

- output disposition is allowed,
- required structured values are correct within declared tolerance,
- required evidence sources are present,
- required evidence is sufficient for the stated conclusion,
- required policy/document IDs or accepted equivalents are cited,
- required claims are present,
- forbidden claims are absent,
- unsupported sources are not fabricated,
- clarification or handoff schema is complete when required,
- security and validator constraints pass.

### Outcome versus trajectory

Outcome is primary. Observable trajectory is graded only where it is part of correctness, including:

- a required evidence source was never consulted,
- a forbidden or unsupported tool was called,
- policy version/source identity is wrong,
- security validation rejected the request,
- a task required clarification but execution proceeded anyway.

Do not require one exact valid sequence of tool calls.

### Partial diagnostics versus pass/fail evidence

Per-dimension checks may receive partial diagnostic credit, but architecture-level task success remains binary. The benchmark reports dimension-level failure reasons alongside the binary outcome.

### No composite “agentic score”

Do not collapse correctness, route quality, reliability, latency, and cost into one opaque score.

Report each dimension separately and show quality-efficiency tradeoffs. A routed architecture that raises success while lowering goodput is a tradeoff, not an automatic win.

### Human review

Human review is used to:

- audit task quality before freeze,
- verify reference solutions,
- spot-check grader alignment,
- adjudicate benchmark defects.

Human reviewers do not silently change a failing held-out task to improve results. Any task/grader correction requires a benchmark version change and a new held-out set if the old set has been consumed for development.

## 11. Trial methodology

Official System Benchmark v1 architecture evidence uses **three matched trials per evidentiary configuration**, preserving the lab’s current preference.

Each task reports:

- successes out of 3,
- empirical per-task success rate,
- stable pass: 3/3,
- unstable: 1/3 or 2/3,
- stable fail: 0/3.

At suite level report:

- aggregate task success across all trials,
- family macro-average,
- stable-pass rate,
- unstable-task rate.

A strict all-three-success measure can be described as a **pass^3-style reliability view**, but the report must be explicit that it is the observed proportion of tasks succeeding in all three matched trials, not a claim of general reliability beyond this benchmark.

### Matched-run controls

Capability/evidentiary runs use:

- fresh agent instance per task,
- concurrency 1,
- immutable fixtures,
- isolated temporary working directories,
- explicit timeout/resource limits,
- documented model/runtime settings,
- the same task ordering policy across compared configurations or a predeclared blocked order,
- controlled caches, with cold/warm status recorded if relevant.

Throughput/load experiments are separate systems experiments and do not replace serialized capability evidence.

## 12. Failure taxonomy

System Benchmark v1 uses the following observable stage contract:

1. preflight
2. routing
3. tool_selection
4. query_validation
5. query_execution
6. evidence_coverage
7. answer_synthesis
8. validation
9. none

The earliest observable failed stage is the primary failure stage. Later stages are marked not_reached when appropriate.

Candidate deterministic reason codes include:

- fixture_missing,
- reference_invalid,
- route_mismatch,
- false_cheap_route,
- unnecessary_escalation,
- unsupported_source_missed,
- required_tool_not_called,
- forbidden_tool_called,
- query_rejected,
- query_parse_error,
- query_execution_error,
- retrieval_empty,
- wrong_document_version,
- required_source_missing,
- required_metric_missing,
- answer_value_incorrect,
- unsupported_claim,
- fabricated_source,
- clarification_missing,
- handoff_incomplete,
- validator_rejected,
- timeout,
- resource_limit.

No hidden chain-of-thought is collected or inferred.

### Compatibility with PR #46

PR #46 is currently an open draft and uses a coarser post-hoc stage vocabulary. If it lands unchanged, System Benchmark implementation should add a backward-compatible System Benchmark stage layer or adapter rather than rewriting historical diagnostics. The design target remains the stage contract above.

### Routing-failure attribution

For held-out tasks, worker execution under oracle routing is measured separately. If the oracle-selected worker succeeds but the natural-language routed system fails because it selected another route, classify the primary failure as routing.

This directly measures cases where routing failed even though an available worker could have solved the task.

## 13. Performance metrics

Capability evidence captures, where available:

- total task latency,
- median latency,
- P95 latency,
- router latency,
- queue wait,
- model calls,
- tool calls,
- repeated tool calls,
- input tokens,
- output tokens,
- model-duration seconds,
- validation failures,
- execution errors,
- task success.

Systems/load experiments additionally report:

- raw requests per minute,
- validated tasks per minute,
- median/P95 service latency,
- median/P95 queue wait,
- concurrency level,
- saturation/degradation reason.

**Validated goodput, not raw prompt throughput, is the primary systems-efficiency measure.**

### Cost proxies

Local inference is not described as free.

Report:

- API cost when nonzero,
- model invocation count,
- token usage,
- model-duration seconds when observable,
- wall-clock runtime,
- CI runtime,
- tool calls,
- operational complexity.

Preferred normalized metrics include:

- model_seconds_per_successful_task,
- model_calls_per_successful_task,
- tool_calls_per_successful_task,
- validated_tasks_per_minute.

If local hardware cost is not measured defensibly, report no dollar estimate.

## 14. Provenance

Every evidentiary run records:

- Git commit SHA,
- benchmark version,
- benchmark-contract fingerprint,
- task-set version,
- structured dataset version and seed,
- policy corpus version/fingerprint,
- model identifier,
- runtime/provider,
- model settings relevant to repeatability,
- scorer version/fingerprint,
- route configuration,
- capability/tool configuration,
- timeouts and resource limits,
- concurrency,
- run timestamp,
- artifact IDs,
- CI run URL when applicable.

If PR #46 provenance utilities merge and satisfy this contract, reuse them. Otherwise implement the smallest equivalent mechanism during the approved implementation phase.

The benchmark-contract fingerprint must include the task schema, grader code, tool/capability contracts, structured-data fixture definition, document corpus manifest/content, and routing contract used for the run.

## 15. Security boundaries

Preserve:

- dataset-scoped read-only ClickHouse access,
- existing statement/table/resource/URL guards,
- no analytical write privileges,
- no production/private systems,
- no unnecessary credentials,
- no chain-of-thought capture,
- no secret-bearing logs or artifacts.

The document retriever is repository-local and read-only. It must enforce:

- corpus path allowlisting,
- no path traversal,
- bounded top-k,
- bounded excerpt size,
- immutable fixture access during trials.

Unsupported-source tasks mention systems such as Jira, Salesforce, Slack, or email, but those systems are deliberately not exposed to the benchmark runtime.

No production write operation is needed for v1.

## 16. Development and held-out separation

### Development set

Used for:

- harness and schema development,
- tool-interface debugging,
- deterministic-handler development,
- router iteration,
- grader unit tests.

### Held-out set

Used only after:

- response contract is frozen,
- tool interfaces are frozen,
- scoring rules are frozen,
- policy corpus v1 is frozen,
- natural-language routing interface is stable,
- reference validators pass.

The held-out task file is not merged until the freeze gate. Once consumed for development, it is no longer held out. Any post-consumption tuning that depends on held-out failures requires a new task-set version and a fresh held-out set.

Held-out requests include:

- novel combinations of known capabilities,
- alternate wording,
- mild typos/noise,
- policy-version edge cases,
- each of the eight families.

The runtime agent must not have file access to benchmark ground-truth metadata.

## 17. Artifact schema

One official run produces a bounded artifact directory containing:

- manifest.json
- reference_validation.json
- results.jsonl
- routing_metrics.json
- diagnostics.json
- summary.json

Each result record contains at minimum:

- case ID,
- family,
- split/version,
- trial number,
- route decision and reason,
- capability profile,
- final disposition,
- answer,
- evidence refs,
- observable tool events,
- validator outcomes,
- task-success checks,
- failure stage/reason,
- latency,
- model/tool call counts,
- token usage,
- model duration when available,
- errors,
- provenance reference.

Artifacts remain reviewable evidence. Raw artifacts are not automatically converted into public portfolio claims.

## 18. CI and run strategy

### Normal pull-request CI

Run deterministic checks only:

- schema validation,
- corpus manifest validation,
- reference-solution tests,
- grader unit tests,
- route-fixture unit tests,
- security/guardrail tests,
- Python 3.11/3.12,
- CodeQL.

Do not run the full local-model evidentiary benchmark on every pull request.

### Development execution

Use explicit local/manual workflows for development tasks. Development results are labeled non-evidentiary.

### Held-out freeze gate

Before held-out execution:

1. merge or explicitly version the stable route interface,
2. freeze task schema, graders, corpus, and tool contracts,
3. validate every reference solution,
4. create benchmark-contract fingerprint,
5. tag or record the exact commit.

### Official evidence

Use manual workflow_dispatch or an equivalent controlled GitHub Actions lane from the frozen commit. Run exactly three matched trials for each approved evidentiary configuration.

### Throughput lane

If PR #48 or its successor merges, reuse its bounded-concurrency concepts only in a separately labeled systems experiment. Load results do not substitute for capability evidence.

## 19. Acceptance criteria

System Benchmark v1 is ready for official execution only when:

- Q1-Q6 remains unchanged,
- all eight task families are represented in dev and held-out sets,
- at least two genuinely different evidence types are required,
- all task cases have passing reference solutions,
- graders are deterministic and unit-tested,
- route inference and worker execution can be evaluated separately,
- a strong single-agent baseline is runnable with the same safe evidence capabilities,
- deterministic/simple, oracle, natural-language, and simple-heuristic routing treatments are defined where applicable,
- route robustness has a predeclared perturbation protocol,
- failure-stage diagnostics use observable evidence only,
- provenance fingerprinting covers the complete benchmark contract,
- held-out tasks have not been used for development,
- official runs use three matched trials,
- read-only/security boundaries pass CI,
- artifact schema is stable and documented.

## 20. Claim boundaries

Allowed claims must name the benchmark version, tested task distribution, model/runtime, and comparison configuration.

Examples of defensible claim forms:

- “On System Benchmark v1 held-out tasks under the documented local qwen2.5:7b configuration, configuration X improved task success by Y while changing latency/tool/model use by Z.”
- “The simple router matched or exceeded the more complex router on this benchmark distribution.”
- “Oracle routing showed worker headroom that the natural-language router did not realize.”
- “Multi-source tasks benefited from access to both structured and policy evidence under this benchmark.”

Do not claim:

- general production superiority,
- that routing is universally better,
- that multi-agent systems are better,
- that development-set results are held-out evidence,
- that oracle routing is deployable routing,
- that local inference has zero cost,
- statistical generalization beyond the task population without an appropriate analysis,
- production causal conclusions from the synthetic delivery dataset.

## 21. Risks

### Benchmark construction bias

Tasks can accidentally be written to reward the desired architecture. Mitigation: reference solutions, strong single-agent baseline, simple router baseline, human audit, and outcome-first grading.

### Policy-corpus leakage or trivial retrieval

Documents may be too easy to identify from keywords. Mitigation: overlapping terminology, version metadata, current/superseded documents, section-level evidence requirements, and held-out paraphrases.

### Overfitting to held-out failures

Mitigation: immutable task-set versioning and mandatory replacement of consumed held-out sets.

### Diagnostic schema drift

PR #46 may merge with different stage names. Mitigation: System Benchmark keeps its explicit stage contract and uses compatibility mapping instead of rewriting historical artifacts.

### Runtime cost

Three trials over multiple configurations may be expensive on local/CI CPU. Mitigation: deterministic route-only evaluation first, full end-to-end execution only for approved configurations, and no LLM judge.

### Limited external validity

The benchmark is synthetic and local. Mitigation: qualify all claims and treat v1 as a controlled engineering benchmark, not a production proxy.

## 22. Out-of-scope items

System Benchmark v1 does not include:

- edits to Q1-Q6,
- a larger or different qwen2.5:7b comparison anchor,
- model-sensitivity comparisons,
- specialist model agents,
- multi-agent debate,
- external SaaS integrations,
- production/private data,
- write-capable analytical tools,
- simulated production transactions,
- a full user-simulator environment,
- ASSERT adoption,
- an LLM judge as primary scoring,
- Phoenix,
- OpenTelemetry as a prerequisite,
- NeMo Guardrails without a new concrete control requirement,
- paid APIs,
- Codex,
- chain-of-thought capture.

## 23. Open questions

Only three material uncertainties remain, and none blocks review of the architecture:

1. **PR #46 merge shape:** its current diagnostic labels are coarser than the System Benchmark stage contract. Implementation should adapt after the PR’s final merged state is known.
2. **PR #47 merge shape:** the natural-language routing interface must be stable before held-out route inputs are frozen.
3. **Statistical scope:** 24 held-out tasks support controlled benchmark comparisons but not broad population claims. If later publication goals require generalized-accuracy estimates, task-bank expansion and a predeclared statistical model should be a separate versioned step.

No open question requires adding a new agent or framework.

## 24. Proposed implementation phases

These phases are design guidance only. They are not an approved implementation plan.

1. benchmark schema and response-contract foundation,
2. local policy corpus and deterministic retrieval interface,
3. deterministic graders and reference solutions,
4. development task set,
5. route-decision adapter and baseline treatments,
6. worker adapters for capability profiles,
7. held-out freeze and perturbation set,
8. System Benchmark runner and artifacts,
9. provenance/diagnostics integration,
10. deterministic CI and manual evidentiary workflow,
11. three-run matched comparison,
12. results interpretation and claim review.

The detailed dependency graph, file-by-file plan, TDD sequence, and execution order must be written only after this design is explicitly approved.

## Research appendix

The design uses principles from original or first-party sources rather than adopting their frameworks.

### Anthropic — Demystifying evals for AI agents (2026)

Source: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Transferred principles:

- treat tasks, trials, outcomes, and trajectories as distinct evaluation objects,
- use repeated trials for stochastic systems,
- prefer deterministic graders where possible,
- create a known-good reference solution for every task,
- isolate trial environments,
- inspect observable trajectories to distinguish agent failures from grader/benchmark defects,
- avoid rigidly requiring one exact valid trajectory.

### OpenAI — Evaluation best practices

Source: https://developers.openai.com/api/docs/guides/evaluation-best-practices

Transferred principles:

- define the evaluation objective before architecture changes,
- make tasks representative of the intended workload rather than generic,
- include typical, edge, and adversarial cases,
- automate scoring where possible and maintain human calibration,
- evaluate nondeterministic components independently,
- let evaluation evidence drive any move from a simpler architecture to multi-agent complexity.

### τ-bench

Source: https://arxiv.org/abs/2406.12045

Transferred principles:

- pair tool use with explicit domain/policy constraints,
- grade verifiable end state or outcome rather than trusting the agent’s claim,
- represent repeated-trial reliability explicitly,
- treat policy following as part of task correctness.

System Benchmark v1 borrows the evaluation principle, not the customer-service domain or user simulator.

### Berkeley Function Calling Leaderboard

Source: https://proceedings.mlr.press/v267/patil25a.html

Transferred principles:

- tool invocation can often be graded deterministically,
- abstention is a capability worth evaluating,
- state/tool behavior and final-response behavior may need different checkers,
- offline deterministic proxies should be validated against the behavior they are intended to represent.

### GAIA

Source: https://arxiv.org/abs/2311.12983

Transferred principles:

- heterogeneous capabilities can be tested with tasks that still admit objective, concise ground truth,
- development and held-out sets should be separated,
- oracle tool selection should be clearly labeled as an upper-bound treatment rather than deployable behavior.

### RouterBench

Source: https://arxiv.org/abs/2403.12031

Transferred principles:

- routing must be analyzed on a cost-quality plane,
- compare router configurations with strong single-model/simple baselines,
- use an oracle as an upper bound, not as real routing,
- measure whether routing meaningfully improves the tradeoff rather than merely beating random selection.

### Routing robustness research

Source: https://arxiv.org/abs/2607.09197

Transferred principles:

- semantically equivalent requests should produce stable routing decisions,
- evaluate surface noise and meaning-preserving paraphrases separately,
- route stability is distinct from downstream task accuracy,
- actor specialization is meaningless when actors are behaviorally redundant.

This directly reinforces the v1 decision not to create specialist agents without evidence of a distinct capability.

### NIST AI 800-2 Initial Public Draft

Source: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.800-2.ipd.pdf

Transferred principles:

- define the measurement target before choosing benchmark procedures,
- design and document the evaluation protocol for reproducibility,
- track and debug benchmark implementation defects,
- communicate uncertainty and qualify claims,
- recognize when automated benchmark evidence does not support broader real-world conclusions.

## Approval gate

This document is the design gate.

**No System Benchmark v1 implementation should begin until Ajanee explicitly approves this specification.**

After approval, the next artifact is a separate detailed implementation plan produced from this specification. That plan must show dependencies, TDD order, file-level scope, verification steps, and merge/review gates. Implementation begins only after that plan receives separate approval.
