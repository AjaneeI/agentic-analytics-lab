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

---

## D-010 — No Codex-credit use for benchmark work
**Status:** Accepted — 2026-10-04

**Decision:** Benchmark implementation, debugging, testing, execution, and
review must not consume Codex credits.

**Why:** The benchmark must remain reproducible with deterministic, inspectable
engineering tools rather than depending on paid agent execution or review.

**Consequence:** Use standard-library implementations, local deterministic
tests, GitHub-hosted Python checks, CodeQL, and source-backed review. Do not
request Codex code/security review or silently fall back to Codex. Before
creating or readying a reviewable PR, account for external automatic-review
triggers. This budget rule does not weaken branch protection or benchmark
verification requirements.


---

## D-011 — Compare architecture tradeoffs with Pareto dominance
**Status:** Accepted — 2026-10-04

**Decision:** Architecture comparisons report quality/reliability and operational burden as separate declared metrics and use Pareto dominance/frontier membership rather than collapsing them into one weighted winner score.

**Simpler baseline:** Continue reporting the strong single-agent baseline and raw matched metrics directly. The frontier is an additional interpretation layer, not a replacement for those measurements.

**Why:** A weighted composite would embed arbitrary value judgments about how much latency, tool calls, model calls, tokens, or maintenance are worth relative to task success. Pareto analysis preserves those tradeoffs and identifies only architectures that are unambiguously dominated under the declared metric directions.

**Evidence boundary:** Frontier membership is conditional on the chosen benchmark, observed measurements, and declared metric directions. It does not prove generalization, business value, or that every point on the frontier is worth deploying.

**Consequence:** Any future weighted utility score requires a separate explicit decision with stakeholder-grounded weights. Added agentic complexity still has to move the observed quality-cost frontier outward to justify adoption.

---

## D-012 — Ship Personal Ops profile-first and fail closed at Red boundaries
**Status:** Accepted — 2026-10-06

**Decision:** The first Hermes Personal Ops product increment is one isolated `personalops` Desktop profile for the Agentic Analytics Lab safe-next-action workflow. It uses only local Qwen3.5-9B/Ollama, repository-scoped tools, at most one non-concurrent child, independent deterministic verification, and structured approval consultation for Red actions.

**Why:** The M0 evidence supports bounded local use when tool and delegation contracts are explicit. A narrow, inspectable product slice provides practical value without assuming that memory, more workers, more frameworks, or broader integrations improve reliability.

**Evidence boundary:** The product track is separate from the frozen benchmark track. Issues #89/#90 remain unchanged M0 provenance; issue #91 and its draft PR own product acceptance. A single passing smoke demonstrates only the approved workflow and cannot establish unrestricted autonomy, general model reliability, or Hermes superiority.

**Consequence:** Desktop Lite exposes only `clarify`, `delegate_task`, and the Personal Ops repository toolset. Green work proceeds autonomously; Yellow work requires the six-field child contract and post-child verification; Red work stops for Ajanee. Expansion requires new evidence and a separate decision.
