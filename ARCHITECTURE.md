# Architecture

## Baseline

```text
User
  ↓
LibreChat
  ↓
Claude
  ↓ decides whether a tool is required
ClickHouse MCP
  ↓
ClickHouse Local
  ↓
Tool result returned to model
  ↓
Final answer

Langfuse records model calls, tool calls, latency, tokens, and cost.
```

## Portfolio target

```text
                         ┌──────────────────────┐
User request ───────────▶│ Router / Lead Agent  │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             Delivery/Data     Workstream       Executive
               Analyst          Specialist       Synthesizer
                    │               │                │
                    └───────────────┼────────────────┘
                                    ▼
                               MCP tools
                                    ▼
                               ClickHouse

                      Langfuse traces every run
```

## Design principles

- Start with a single-agent baseline before adding orchestration.
- Route only when specialization measurably improves outcome quality or efficiency.
- Keep tool access least-privilege and read-only by default.
- Use schema discovery before analytical queries.
- Capture cost, latency, tool count, and failure modes for every experiment.
- Prefer synthetic/public data for the publishable version.
