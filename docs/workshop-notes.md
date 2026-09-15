# Workshop Notes

## What was practiced

- self-hosted agentic analytics stack
- Docker Compose orchestration
- LibreChat agent interface
- ClickHouse MCP integration
- Langfuse observability
- agent tool use and iterative tool/model loops
- agent skills and modular best-practice rules
- multi-agent orchestration concepts

## Working baseline

A read-only prompt asking the model to list available ClickHouse databases and tables successfully triggered MCP tool calls against ClickHouse Local.

Observed databases included:

- `default`
- `INFORMATION_SCHEMA`
- `information_schema`
- `system`

The `default` database contained LLM observability/tracing application data, while `system` exposed ClickHouse diagnostics, monitoring, and configuration tables.

## Debugging record

### PostgreSQL port collision

Docker Compose initially failed because host PostgreSQL was already listening on port `5432`.

Diagnosis:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
ps -fp <PID>
```

Resolution used during the workshop:

```bash
brew services stop postgresql@16
docker compose up -d
docker compose ps
```

### Claude Sonnet 5 compatibility failure

The MCP tool path began correctly, but the run failed after tool use with a malformed/missing thinking field in the LibreChat ↔ Anthropic message flow.

Representative error:

```text
messages.3.content.0.thinking.thinking: Field required
```

Switching to Claude Sonnet 4.6 in a fresh chat produced a successful MCP workflow.

## Observability

Langfuse captured the successful run as an agent loop with model calls and tool batches. The run was inspected in both aggregated and expanded graph views.

One observed successful run had approximately:

- latency: 43.93 s
- estimated model cost: $0.028365

These numbers are workshop observations, not benchmark claims. Future portfolio experiments should reproduce measurements under controlled conditions.

## Additional observation to investigate

Docker Desktop showed Langfuse worker queue socket timeout messages involving Redis. The system still produced traces, but this should be investigated before claiming a clean production-like baseline.
