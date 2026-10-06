# Agentic Analytics Lab — Research Protocol & Roadmap

## Purpose

This document is the canonical research-program protocol for Agentic Analytics Lab. It defines what the study is trying to establish, the benchmark and methodology gates, the authorized sequence of work, and the evidence required before claims advance.

GitHub remains authoritative for implementation, tests, issues, pull requests, workflow runs, commits, benchmark artifacts, and technical claims. Notion is the program-level roadmap. Asana is the human-action queue.

## Research question

Under which analytical task conditions does routed execution improve validated task completion or reliability relative to a strong single-agent baseline, and what additional operational burden accompanies those gains?

### Decision question

Do the observed gains move the quality-cost frontier outward enough to warrant the added architecture?

The study must permit a negative result. A simpler system winning is a successful research outcome.

## Contribution

A reproducible, resource-bounded evaluation of routing value in analytical workflows combining business-metric semantics, structured evidence, versioned policy knowledge, clarification and abstention behavior, explicit authority and handoff boundaries, and cost/latency/operational burden.

## Experimental design

- Controlled matched repeated-measures architecture comparison.
- Task is the primary experimental unit.
- Development and held-out evidence remain strictly separate.
- Deterministic/objective graders are primary where verifiable ground truth exists.
- Final outcome, routing behavior, worker execution, trajectory quality, failure stage, and resource burden are reported separately.
- No opaque composite agent score.
- No chain-of-thought scoring.
- No LLM judge as the primary scorer.
- Added complexity must earn its place through measured benefit.

## Benchmark program

### Frozen Q1-Q6 microbenchmark

Historical/bounded evidence only. It remains unchanged and is not the System Benchmark v1 confirmatory study.

### System Benchmark v1

Target task bank:

- 24 development tasks: 3 per family.
- 24 held-out tasks: 3 per family.
- Separate route-robustness perturbation set.

Eight families:

1. Structured deterministic analytics.
2. Tool-grounded analytical reasoning.
3. Document and policy retrieval.
4. Multi-source synthesis.
5. Ambiguity, clarification, and escalation.
6. Epistemic and causal reasoning.
7. Unsupported-source handling.
8. Human handoff and authority boundary.

Evidence sources:

- seed-42 synthetic delivery dataset through the read-only structured-data boundary;
- version-controlled local policy corpus with explicit versions, scope, effective dates, and authority.

## Architecture conditions

Primary comparison candidates:

1. Strong single-agent baseline with the same safe evidence capabilities.
2. Routed architecture using the frozen routing/control-plane contract.

Diagnostic or secondary conditions:

- deterministic/simple execution where genuinely exact and cheap;
- metadata-supplied intended route for worker-execution diagnostics only;
- simple inspectable routing heuristic;
- natural-language routing after its interface is frozen.

Route inference, worker execution, and end-to-end system performance remain separate measurements.

## Outcomes

### Primary outcome

Binary end-to-end task success under the frozen deterministic grading contract.

### Effectiveness

- task success;
- evidence correctness;
- answer/value correctness;
- disposition correctness.

### Repeatability

- successes out of three observed trials;
- 3/3 observed success;
- 1/3 or 2/3 variable outcome;
- 0/3 observed failure.

These are observed repeatability summaries, not proof of general future reliability.

### Process quality

- required and forbidden tool behavior;
- unsupported or fabricated evidence;
- repeated calls;
- dependency/order violations only where the task contract requires order;
- routing error;
- authority/handoff behavior;
- earliest observable failure stage.

### Operational burden

- total latency;
- model calls;
- tool calls;
- token use where available;
- model-duration seconds where available;
- failed attempts and retries;
- validated tasks per minute;
- implementation and maintenance complexity.

## Evaluator-validity gate

Before held-out evidence counts:

- every known-good reference solution passes;
- known-bad adversarial solutions fail for the intended reason;
- valid alternative solutions are not rejected solely for using a different valid route;
- policy/version/authority expectations are explicit;
- ambiguous tasks distinguish intentional ambiguity from benchmark defects;
- scorer defects require versioned correction, not silent post-hoc changes.

## Statistical analysis plan

### Primary estimand

For each task, compute the observed candidate-minus-baseline difference in success proportion across matched repeats. Report the mean paired task effect under the predeclared task/family weighting rule.

### Uncertainty method

Do not finalize the inferential interval until the current documentation/code mismatch is resolved and the procedure is calibration-tested on simulated benchmark structures.

Before freeze:

1. specify exactly what is resampled;
2. define the population/estimand the interval refers to;
3. run model-free calibration simulations across plausible task difficulty and stochasticity;
4. document coverage, interval width, and false-positive behavior;
5. freeze the selected procedure before held-out outcomes are inspected.

A hierarchical or mixed-effects model may be used as a sensitivity analysis if justified by final benchmark size and model diagnostics. It is not automatically primary.

### Multi-objective decision

Compare quality/reliability gains against latency, tool/model use, and operational complexity using a Pareto view. Being nondominated alone does not automatically justify adoption. Predeclare a minimally useful quality gain, or an acceptable quality-loss margin for a cheaper system, before confirmatory interpretation.

## Reproducibility and provenance

Every evidentiary run records commit SHA, benchmark/task/corpus versions, benchmark-contract fingerprint, model/runtime/provider, tool/scorer configuration, route configuration, resource/time limits, run timestamp, artifact IDs, and CI/workflow reference where applicable.

GitHub artifacts, not prose, are the technical proof.

## Roadmap and gates

### Phase 0 — Historical baseline

Status: complete and bounded.

- Frozen Q1-Q6 preserved.
- Single-agent and routed-execution evidence preserved.
- Historical failures remain evidence rather than being rewritten.

### Phase 1 — System Benchmark contracts and deterministic core

Status: substantially complete.

- typed task/response contracts;
- repository-local policy retrieval;
- deterministic references and scoring;
- route/worker adapter layer;
- evidence/failure/provenance infrastructure;
- dry-run and corrupted-control validation.

### Phase 2 — Development runtime qualification

Status: ACTIVE NOW.

Goal: prove that the bounded real worker can execute System Benchmark development tasks under the actual safe tool boundary without changing benchmark semantics.

Current gate: resume issue #73 with Treatment A only on SB-D01 using the bounded local worker and deterministic scorer. Preserve accepted evidence and stop after the authorized slice.

Treatment B remains blocked until the delegation boundary enforces a hard one-worker/no-concurrency invariant. Prompt-only instructions are insufficient.

### Phase 3 — Benchmark and evaluator validity audit

Exit only when positive and negative control suites pass, valid alternatives are accepted where appropriate, policy ambiguity and authority rules are audited, task/template relationships are documented, no unresolved grader defects remain, and scorer/version changes are frozen.

### Phase 4 — Statistical calibration and analysis freeze

Exit only when documentation and implementation use the same inference procedure, calibration simulations are complete, the primary estimand and interval method are frozen, exclusion/timeout/rerun/harness-failure rules are frozen, multiplicity/secondary-analysis rules are frozen, and the practical decision threshold is frozen.

Output: Statistical Analysis Plan v1.

### Phase 5 — Complete development task bank

Exit only when 24 development tasks exist, every reference is validated, routing and worker contracts are stable, policy corpus v1 is stable, deterministic/simple and strong-single-agent baselines are runnable, and development results remain explicitly non-confirmatory.

### Phase 6 — Held-out freeze

Exit only when 24 held-out tasks are created and audited without development use, the perturbation protocol is frozen, the benchmark-contract fingerprint is generated, the exact commit or tag is recorded, and runtime cannot access ground-truth metadata.

After this point, tuning based on held-out failures consumes the set and requires a fresh version.

### Phase 7 — Confirmatory execution

Run approved configurations under matched conditions, exactly three trials per task/configuration unless the frozen protocol explicitly changes that before exposure.

Sequence:

1. strong single-agent baseline;
2. approved routed configuration;
3. diagnostic reference conditions as prespecified;
4. routing-robustness lane separately.

No architecture expansion during this phase.

### Phase 8 — Analysis and independent verification

- compute paired architecture effects;
- run the frozen uncertainty procedure;
- summarize observed repeatability;
- analyze route, worker, and end-to-end failures separately;
- produce Pareto cost-quality comparison;
- independently verify numerical claims with Wolfram where useful;
- run prespecified sensitivity analysis.

### Phase 9 — Claim review and publication package

Before public claims, every quantitative claim must map to an artifact; claim boundaries must name benchmark version, tested workload, runtime/model, and configuration; synthetic-data limitations must be stated; metadata/intended-route results must not be presented as deployable routing; development results must not be presented as held-out evidence.

Candidate outputs include a recruiter-facing technical case study, conference poster/demo or paper when evidence is mature, and reproducibility appendix/benchmark documentation.

## Stop conditions

Pause advancement when the grader is shown to mismeasure the intended construct, tool/runtime failures make architecture comparison non-comparable, benchmark semantics would require post-hoc tuning, held-out contamination occurs, security/provenance boundaries fail, or a new framework/agent is proposed without evidence that the current system cannot answer the research question.

## Current next step

Do not start held-out work. Do not add specialist agents. Do not add infrastructure for its own sake.

The next authorized technical step is the bounded SB-D01 Treatment A development rerun already identified in STATUS.md and issue #73. After accepted evidence is preserved, return to this roadmap and advance only through the next unmet gate.
