# System Benchmark v1

System Benchmark v1 is separate from the frozen Q1–Q6 microbenchmark in
evals/questions.json. It is built in bounded phases so task contracts,
evidence capabilities, scoring, runtime execution, and held-out evidence do
not become coupled.

## Current source snapshot

As of the October 5, 2026 audit, `main` includes PR A–D foundations,
trial/artifact support, the bounded local worker, and cross-cutting evidence
utilities. The seven development cases remain development-only.
See [verified status](../../STATUS.md) for the next bounded experiment and
for the separate unmerged rehearsal candidate in PR #72.

Validate the development contracts without model execution:

```bash
python3 scripts/validate_system_benchmark.py --emit-provenance
```

Run that command from the repository root. It validates task/reference
compatibility and emits a contract fingerprint; it is not an agent run.

## Foundation — PR A through PR C

PR A established typed task/response contracts, deterministic fixture loading,
fingerprint inputs, and model-free validation.

PR B added the repository-local, read-only policy corpus and deterministic
section retrieval with version-aware as_of behavior.

PR C adds the deterministic evaluation core:

- development_tasks.json — seven inspectable development cases only;
- development_references.json — exact machine-checkable evidence/tool/answer
  expectations keyed by reference_solution_id;
- src/evals/system_benchmark/references.py — strict reference loading and
  task/reference compatibility validation;
- src/evals/system_benchmark/scoring.py — deterministic per-dimension scoring
  over observable response, evidence, tool-call, structured-value,
  clarification, and handoff state.

The development set covers structured analytics evidence, current policy
retrieval, structured + policy cross-source alignment, unsupported evidence,
bounded clarification, conflicting policy authority requiring handoff, and
historical policy selection.

No held-out fixture is present in this phase.

## Evidence reference format

Reference expectations use explicit repository-local identifiers:

- structured source: structured:<source_id>
- policy section: policy:<document_id>@<version>#<section_id>

Policy identity therefore remains auditable at document, version, and section
granularity. Wrong-version evidence is scored separately from missing evidence.

## Scoring dimensions

score_response evaluates dimensions in a fixed order:

1. disposition;
2. evidence;
3. tools;
4. structured values;
5. clarification;
6. handoff;
7. bounded answer terms.

Failures return stable reason codes including missing_required_evidence,
wrong_policy_version, unsupported_evidence_source, missing_required_tool,
forbidden_tool_used, structured_value_mismatch, required_clarification_omitted,
required_handoff_omitted, unnecessary_escalation, and
forbidden_answer_disposition.

Scoring uses no LLM judge, hidden reasoning, model inference, external SaaS,
or paid API.

## Development-only boundary

Development fixtures are inspectable and may be used to debug the scorer.
They are not evidence of unseen-task generalization or architecture
performance.

The PR C slice itself did not add held-out tasks, model execution, routing treatments, or a benchmark runner. Later sections describe subsequent implementations. Frozen Q1–Q6 semantics, scorer, dataset, prompt/tool contract, and accepted comparison evidence remain a separate contract; no LLM judge is introduced.

## PR D — routing treatments and worker adapters

Tracking issue: #69.

PR D adds a model-free adapter layer that keeps route inference
separate from worker execution:

- `routing.py` defines normalized route/capability decisions, oracle routing,
  a free-text adapter over the existing natural-language baseline, a simple
  inspectable capability heuristic, and route-only metrics;
- `workers.py` defines bounded worker invocations, capability-specific tool
  exposure, the strong-single-agent tool contract, and hard Family G/H
  response boundaries.

The worker adapter intersects predicted capability tools with the task's
allowed-tool contract, so a routing mistake cannot expand permissions.

Development-only route checks on the seven current PR C cases are diagnostic,
not architecture-performance evidence:

- oracle metadata: 100% route accuracy and 100% capability-profile accuracy
  by construction;
- simple inspectable heuristic: 28.6% route accuracy and 57.1% capability
  accuracy, with two false-cheap routes and zero unsupported-source misses.

The weak heuristic result is intentionally preserved as a simple baseline
rather than tuned to the development fixtures.

PR D does not itself execute a model, Hermes, Ollama, or a benchmark worker runtime.

PR D was integrated into `main` on 2026-10-04 without marking the draft PR ready, preserving the repository's no-Codex benchmark rule. The integrated tree passed hosted Python 3.11/3.12 and CodeQL.


## Cross-cutting evidence extensions

The repository also includes model-free evidence utilities that can be applied
to System Benchmark artifacts without changing task semantics or the
deterministic scorer:

- `src/evals/statistical_evidence.py` compares matched repeated runs with a
  task-level paired bootstrap so repeated executions of one task are not
  counted as independent benchmark items;
- `src/evals/trajectory_quality.py` measures observable tool selection,
  dependency order, repetition, malformed calls, and call-budget violations;
- `src/evals/failure_taxonomy.py` groups raw reason codes and diagnostic
  stages into a stable hierarchical reporting taxonomy while preserving the
  underlying evidence;
- `src/evals/complexity_frontier.py` compares architectures with Pareto
  dominance instead of collapsing quality and operational burden into one
  weighted score.

These utilities do not create a new benchmark claim on their own.

System Benchmark task contracts may now optionally declare a `trajectory`
object with `max_tool_calls` and explicit `ordered_dependencies`. When a
task declares either constraint, deterministic scoring adds a `trajectory`
dimension with stable reason codes for dependency-order violations, repeated
calls, malformed calls, and call-budget overruns. Existing fixtures that omit
the object retain their previous behavior.

The current development set uses this conservatively: SB-D01 declares a
two-call budget for its two-source task, but no arbitrary source order is
imposed because the evidence contract does not require one.

See `docs/agent-evaluation-evidence-method.md` for the research rationale,
claim boundaries, and optional Wolfram independent-verification path.
