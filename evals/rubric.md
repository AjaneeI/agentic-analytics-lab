# Agent Evaluation Rubric

Each run is evaluated on:

- **Factual correctness**: numeric and categorical claims match ground truth.
- **Completeness**: the answer includes all values explicitly requested.
- **Tool grounding**: claims about the dataset are supported by tool/query results.
- **Epistemic discipline**: the agent does not infer causality or certainty beyond the evidence.
- **Efficiency**: unnecessary tool calls are penalized.
- **Latency**: total runtime is recorded.
- **Token usage**: input and output tokens are recorded when available.
- **Cost**: model cost is recorded when available.
- **Failure behavior**: errors, retries, malformed tool calls, or unsupported claims are recorded.

## Primary comparison

Compare the same evaluation set across:

1. Single-agent baseline
2. Routed / specialist-agent architecture

The routed design should only be considered beneficial when any improvement in answer quality or reliability is large enough to justify additional tool calls, latency, token usage, cost, and operational complexity.
