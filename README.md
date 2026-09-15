# Agentic Analytics Lab

Private portfolio-development repository for extending the **ClickHouse Agentic Data Stack** workshop into an original, measurable applied-AI project.

## Project goal

Build and evaluate a cost-aware delivery intelligence agent that can query structured operational data through MCP, synthesize evidence, and expose its execution path through observability tooling.

The portfolio version should answer a concrete engineering question:

> When does a routed or multi-agent design outperform a single-agent design enough to justify the added cost, latency, and complexity?

## Workshop baseline reproduced

- Self-hosted multi-service stack with Docker Compose
- LibreChat as the agent/chat interface
- Claude as the model provider
- ClickHouse Local through MCP
- Langfuse for tracing, latency, token, and cost observability
- Successful read-only database/schema discovery through MCP
- Agent execution inspected in both aggregated and expanded Langfuse graph views

### Debugging completed during the workshop

- Diagnosed a host PostgreSQL port collision on `5432`
- Identified the conflicting Homebrew PostgreSQL 16 process with `lsof`
- Stopped the host service, restarted the Docker stack, and confirmed the Compose services were healthy
- Observed a Claude Sonnet 5 + LibreChat tool/thinking compatibility failure and reproduced the same MCP workflow successfully with Claude Sonnet 4.6

## Portfolio extension

The original build will use synthetic or public delivery/operations data and compare:

1. **Single-agent baseline**
2. **Routed / specialist-agent design**
3. **Optional multi-agent orchestration** when the added complexity is justified

Evaluation dimensions:

- task success
- factual consistency
- tool-call count
- latency
- input/output tokens
- model cost
- failure rate
- recovery behavior

## Architecture

```text
User
  ↓
LibreChat / agent interface
  ↓
LLM
  ↓
MCP tool layer
  ↓
ClickHouse

Langfuse observes model + tool execution across the run.
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the planned portfolio architecture.

## Repository structure

```text
.
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── .env.example
├── .gitignore
├── docs/
│   ├── workshop-notes.md
│   ├── evidence-plan.md
│   └── screenshots/
├── experiments/
│   └── experiment-log.md
└── src/
    ├── agents/
    ├── tools/
    └── evals/
```

## Upstream references

This project is an original extension of concepts practiced in the ClickHouse workshop. It does **not** claim the upstream stack as original work.

- ClickHouse Agentic Data Stack: https://github.com/ClickHouse/agentic-data-stack
- ClickHouse MCP server: https://github.com/ClickHouse/mcp-clickhouse
- ClickHouse Agent Skills: https://github.com/ClickHouse/agent-skills
- ClickHouse best-practices skill: https://github.com/ClickHouse/agent-skills/blob/main/skills/clickhouse-best-practices/SKILL.md
- LibreChat: https://github.com/danny-avila/LibreChat
- Langfuse: https://github.com/langfuse/langfuse

## Status

Workshop baseline complete. Next milestone: reproduce the baseline from a clean start, add synthetic/public delivery data, and run the first controlled single-agent vs routed-agent experiment.
