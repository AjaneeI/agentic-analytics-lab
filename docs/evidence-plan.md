# Evidence Plan

The final public portfolio should prove the system works without exposing
secrets, private identifiers, or unverified benchmark claims.

## Safe Evidence To Publish

- sanitized LibreChat screenshot showing a successful ClickHouse-Local MCP tool call
- sanitized Langfuse trace list
- sanitized aggregated trace graph
- sanitized expanded trace graph
- Docker Compose service-health screenshot with private identifiers removed if needed
- architecture diagram
- experiment comparison table
- test-suite output showing the current code is green
- small SQL examples that demonstrate valid and rejected metric definitions

Current proof artifact:

- [test-suite-proof-2026-09-15.md](test-suite-proof-2026-09-15.md)

## Do Not Publish

- screenshot containing the workshop Anthropic API key
- raw Langfuse screenshots that expose user/session IDs
- any private Slack/Linear/customer data
- raw `.env` values
- benchmark claims from older code without a fresh run
- screenshots that expose local usernames, paths, or private project names unless intentionally approved

## Strong Portfolio Evidence Sequence

1. problem statement
2. architecture diagram
3. successful tool call
4. trace visualization
5. controlled experiment table
6. failure analysis
7. cost/latency optimization result
8. lessons learned and next steps

## Current Evidence Story

The most defensible current story is:

1. A workshop baseline proved the agentic data stack could connect an LLM to
   ClickHouse through MCP and expose traces through Langfuse.
2. The portfolio extension turns that workshop into an evaluation project with
   synthetic delivery-operations data.
3. The first baseline is a single agent with read-only ClickHouse access.
4. Tests now protect both SQL read-only behavior and a known blocker-rate
   semantic failure.
5. The next public milestone is a controlled benchmark comparing the
   single-agent baseline against a routed design.
