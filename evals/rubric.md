# Agent Evaluation Rubric

Each run is evaluated on:

- **Execution success**: the agent completed without a runtime, tool, adapter, or infrastructure exception.
- **Task correctness**: required numeric and categorical claims match the frozen ground truth.
- **Completeness**: the answer includes all values explicitly requested by the case.
- **Tool grounding**: Q1-Q5 require database evidence; Q6 is an epistemic question and does not require a query.
- **Factual consistency**: required answer values are present in the captured ClickHouse result rows.
- **Epistemic discipline**: the agent does not infer causality or certainty beyond the evidence.
- **Efficiency**: unnecessary or repeated tool calls are recorded separately from correctness.
- **Latency**: total end-to-end runtime is recorded.
- **Model calls**: total model invocations are recorded.
- **Token usage**: Ollama input/output token counts are recorded when returned by the local API.
- **Cost**: Ollama has no per-request API charge; local compute/electricity cost is not estimated by this benchmark.
- **Failure behavior**: errors, malformed calls, ungrounded answers, repeated calls, and incorrect answers are labeled.

## Scoring method

The frozen cases use deterministic checks rather than LLM-as-a-judge when deterministic checks are available.

- Q1-Q5 check required answer values against `evals/questions.json` and against captured ClickHouse evidence.
- Q4 additionally checks ranking order.
- Q6 checks that the answer rejects a causal conclusion, distinguishes association/correlation from causation, and requests stronger evidence or study design.
- Unsupported-claim detection is intentionally conservative. The automatic scorer flags missing/contradictory required evidence; a human review is still required before publishing a benchmark artifact.

Execution success alone is not benchmark success. A case passes only when the final answer meets the deterministic answer contract and required evidence checks.

## Primary comparison

Compare the same evaluation set across:

1. Single-agent baseline
2. Routed / specialist-agent architecture

The routed design should only be considered beneficial when any improvement in answer quality or reliability is large enough to justify additional tool calls, model calls, latency, token usage, cost, and operational complexity.

The dataset, question set, answer contract, read-only tool layer, metric definitions, evaluator, and measurement methodology should remain fixed across both architectures.
