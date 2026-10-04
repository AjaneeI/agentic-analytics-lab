# System Benchmark v1

System Benchmark v1 is separate from the frozen Q1–Q6 microbenchmark in
evals/questions.json. It is built in bounded phases so task contracts,
evidence capabilities, scoring, runtime execution, and held-out evidence do
not become coupled.

## Current phase — PR C

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

PR C does not add held-out tasks, model execution, routing treatments, a
benchmark runner, an LLM judge, or changes to frozen Q1–Q6 semantics, scorer,
dataset, prompt/tool contract, or accepted comparison evidence.
