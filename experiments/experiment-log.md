# Experiment Log

## EXP-001 — Claude Sonnet 4.6 + ClickHouse Local MCP

**Status:** Success  
**Goal:** Verify end-to-end read-only ClickHouse schema discovery through MCP.  
**Model:** Claude Sonnet 4.6  
**Tool:** ClickHouse-Local MCP  
**Prompt:** List available databases and tables, do not modify data, and briefly explain each database.  

**Observed result**

- MCP tools executed successfully.
- Model returned the available databases and table summaries.
- Langfuse captured the run.
- Aggregated and expanded execution graphs were visible.
- One observed trace showed ~43.93 s latency and ~$0.028365 estimated model cost.

**Notes**

Treat workshop measurements as baseline observations only. Re-run under controlled conditions before publishing benchmark claims.

---

## EXP-002 — Claude Sonnet 5 + ClickHouse Local MCP

**Status:** Failure  
**Goal:** Run the same schema-discovery task using Sonnet 5.  

**Observed result**

- Initial MCP/tool use began successfully.
- The conversation failed after tool execution with a thinking-block/message serialization error.

Representative error:

```text
messages.3.content.0.thinking.thinking: Field required
```

**Interpretation**

The ClickHouse/MCP path was functioning; the failure appeared in the model/client message integration layer.

**Follow-up**

- reproduce on current LibreChat + Anthropic versions
- check whether thinking configuration changes resolve it
- compare with Sonnet 4.6 baseline

---

## EXP-003 — Planned: Single Agent vs Routed Agents

**Status:** Planned

Compare a single generalist agent against a routed specialist design using the same synthetic/public delivery dataset.

Capture:

- task success
- factual consistency
- tool calls
- latency
- tokens
- cost
- failure modes
