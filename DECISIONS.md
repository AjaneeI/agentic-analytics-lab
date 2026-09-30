# Decision Log

This file records durable architecture, evaluation, and operating decisions. It is not a task list.

## D-001 — Keep a strong single-agent baseline
**Status:** Accepted

**Decision:** New orchestration must be compared against the simplest credible single-agent baseline.

**Why:** Added agent structure can create latency, cost, maintenance, and failure modes that a simpler design avoids.

**Consequence:** More complex designs must earn adoption with measured outcome or efficiency gains.

---

## D-002 — Separate routed execution from route inference
**Status:** Accepted

**Decision:** Oracle-metadata routed execution and natural-language routing are evaluated as separate lanes.

**Why:** Supplying the correct route tests execution-layer specialization, not whether a real system can infer that route.

**Consequence:** Oracle-routed success must never be presented as proof of natural-language routing quality.

---

## D-003 — Keep the frozen benchmark deterministic
**Status:** Accepted

**Decision:** Where ground truth exists, use deterministic scoring and grounding checks. Do not insert an LLM judge into the frozen Q1-Q6 benchmark.

**Why:** The benchmark is intended to support reproducible, inspectable comparisons.

**Consequence:** Subjective evaluation may be explored separately, but cannot silently replace the frozen benchmark contract.

---

## D-004 — Preserve least-privilege analytical tooling
**Status:** Accepted

**Decision:** Analytical execution stays behind the dataset-scoped, read-only ClickHouse boundary with validation and resource safeguards.

**Why:** Architecture comparisons should not depend on giving one lane broader data access or unsafe tool permissions.

**Consequence:** Any broader access requires an explicit new decision and justification.

---

## D-005 — Treat ASSERT as evaluated-and-rejected for the bounded Q3 use case
**Status:** Accepted

**Decision:** Do not adopt ASSERT for the bounded Q3 evidentiary use case based on the completed comparison.

**Evidence:** The repository contains the bounded ASSERT Q3 comparison/plumbing work and subsequent project decision that ASSERT did not justify adoption for this use case.

**Why:** Additional framework/runtime complexity must earn its place with better evidence, not novelty.

**Revisit only if:** the task changes materially, ASSERT capabilities change materially, or a new bounded experiment defines a different success criterion.

---

## D-006 — Keep model sensitivity separate from baseline replacement
**Status:** Accepted

**Decision:** Model-sensitivity experiments may test other models, but `qwen2.5:7b` remains the frozen architecture-comparison anchor unless a separate benchmark-version change is explicitly approved.

**Why:** Changing the model while changing architecture would confound comparisons.

**Consequence:** A better-performing model is evidence about model sensitivity, not automatic permission to rewrite the benchmark baseline.

---

## D-007 — Measure validated throughput, not raw concurrency
**Status:** Accepted

**Decision:** Throughput experiments optimize validated goodput, not request volume alone.

**Why:** More parallel work is not useful if task success degrades, errors rise, or evidence quality falls.

**Consequence:** Queue wait, service latency, task success, execution errors, calls, tokens, and validated tasks/minute should be reported together.

---

## D-008 — Record observable failure attribution only
**Status:** Accepted

**Decision:** Failure diagnostics may attribute failures to observable stages such as tool selection, query validation, execution, evidence coverage, answer synthesis, and final validation, but must preserve `unknown` or `not_reached` when evidence is insufficient.

**Why:** Post-hoc diagnostics should not invent hidden reasoning or chain-of-thought.

**Consequence:** Failure analysis remains evidence-backed and inspectable.

---

## D-009 — Use Project Context Protocol v1
**Status:** Accepted

**Decision:** The repository uses four root context files:
- `PROJECT.md` for stable project contract;
- `AGENTS.md` for agent operating rules;
- `STATUS.md` for verified current state and next steps;
- `DECISIONS.md` for durable decisions.

**Why:** Coding agents should not reconstruct project intent, current state, or prior architecture decisions from scattered commits and chat history.

**Consequence:** Agents must read these files before substantial work and update status/decisions only when evidence warrants it.
