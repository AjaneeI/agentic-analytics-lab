# Experiment Log

This is a chronological engineering log, not the current portfolio summary.

For accepted benchmark evidence and claim boundaries, start with [Portfolio Results](../docs/portfolio-results.md).

## EXP-001 - Claude Sonnet 4.6 + ClickHouse Local MCP

**Status:** Success  
**Role in project:** Historical workshop reproduction  
**Goal:** Verify end-to-end read-only ClickHouse schema discovery through MCP.  
**Model:** Claude Sonnet 4.6  
**Tool:** ClickHouse-Local MCP  
**Prompt:** List available databases and tables, do not modify data, and briefly explain each database.

**Observed result**

- MCP tools executed successfully.
- Model returned the available databases and table summaries.
- Langfuse captured the run.
- Aggregated and expanded execution graphs were visible.
- One observed trace showed about 43.93 s latency and about $0.028365 estimated model cost.

**Interpretation**

This proved the upstream workshop path worked. It is not used as the accepted portfolio benchmark because the later Python baseline, dataset, evaluator, and comparison contract are different.

---

## EXP-002 - Claude Sonnet 5 + ClickHouse Local MCP

**Status:** Failure  
**Role in project:** Historical integration failure  
**Goal:** Run the same schema-discovery task using Sonnet 5.

**Observed result**

- Initial MCP/tool use began successfully.
- The conversation failed after tool execution with a thinking-block/message serialization error.

Representative error:

    messages.3.content.0.thinking.thinking: Field required

**Interpretation**

The ClickHouse/MCP path was functioning. The observed failure occurred in the model/client message integration layer.

This run is preserved as integration history, not as evidence about the current Python benchmark.

---

## EXP-003 - Single agent vs oracle-metadata routed execution

**Status:** Completed bounded comparison  
**Role in project:** Accepted architecture experiment

**Question**

If route-relevant task facts are already known, can a routed execution layer improve validated outcomes or efficiency relative to the frozen single-agent baseline?

**Matched evidence**

- Single-agent baseline: [Actions run 35755961530](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/35755961530)
- Oracle-metadata routed comparison: [Actions run 35760422536](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/35760422536)

**Result**

- Single-agent task success: 4/6, 4/6, 4/6.
- Routed task success: 5/6, 6/6, 6/6.
- Single-agent model calls: 11 per run.
- Routed model calls: 1 per run.
- Tool calls: 5 per run in both conditions.
- Mean hosted latency: 217.0 s for the single-agent baseline and 33.9 s for the routed condition.

**Claim boundary**

The routed condition uses frozen benchmark category and \`requires_tool\` metadata. It tests execution value when the route is known. It does not measure free-text route inference and does not support a general multi-agent superiority claim.

See [Portfolio Results](../docs/portfolio-results.md) for the concise interpretation.

---

## EXP-005 - Qwen semantic grounding correction

**Model:** qwen2.5:7b via Ollama  
**Status:** Successful SQL generation after schema-semantic grounding

### Change

The system prompt was expanded with:

- the exact ClickHouse table
- column meanings
- the distinction between \`status\` and the \`blocked\` indicator
- explicit guidance that rates require a numerator and denominator

No ground-truth benchmark values were supplied.

### Result

For:

> Which team has the highest blocker rate?

The model generated a read-only query that:

- used the blocked indicator as the numerator;
- divided blocked work items by total work items;
- grouped by team;
- ordered by calculated blocker rate;
- selected the highest-rate team.

### Finding

The earlier failure was caused by insufficient semantic grounding rather than an inability to use tools.

That led to a lasting architectural distinction in the project:

1. tool-call capability;
2. execution safety;
3. semantic grounding for correct analytical reasoning.

The current tool boundary now includes a targeted guard against labeling the complement of blocked work as \`blocker_rate\`.
