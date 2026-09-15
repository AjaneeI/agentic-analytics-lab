# Social Posting Kit

This file keeps the public narrative close to the project evidence. It is for
drafting only. Do not post until the repo, screenshots, and claims have been
reviewed.

## Positioning

Agentic Analytics Lab is a portfolio project about measuring practical AI
systems. The strongest angle is not that an agent can query a database. The
stronger angle is that the project asks when agent orchestration is actually
worth its added cost, latency, and complexity.

Use this project to signal:

- applied AI operations judgment
- product-minded evaluation of AI systems
- analytics and dashboard thinking
- safe tool use and read-only data access
- semantic checks for business metrics
- comfort documenting failures, tradeoffs, and next steps

Avoid claiming:

- production ownership
- senior software engineering work
- model training or ML research
- enterprise-scale deployment
- benchmark results that have not been re-run under controlled conditions

## GitHub About Copy

Short description:

```text
Portfolio project evaluating when routed AI analytics agents are worth the added latency, cost, and complexity.
```

Topics:

```text
agentic-ai, analytics, clickhouse, mcp, langfuse, ai-evaluation, tool-calling, portfolio-project
```

## LinkedIn Draft

I have been turning the ClickHouse Agentic Data Stack workshop into a portfolio
project I can actually measure.

The project is called Agentic Analytics Lab.

The question I am working through:

When does a routed or multi-agent analytics system perform well enough to
justify the added latency, cost, tool calls, and maintenance?

So far, I have built a single-agent baseline that queries a synthetic delivery
operations dataset through a read-only ClickHouse tool. I also added tests and a
semantic guard for one of the first issues I found: the model could calculate
the complement of blocked work items and label it as `blocker_rate`.

That is the kind of failure I want this project to catch.

Not just "can the agent call a tool?"

But:

- did it use the right metric?
- did it make the smallest safe query?
- did it preserve read-only access?
- did the answer match the evidence?
- would routing to a specialist agent actually improve the result?

This is the part of applied AI that interests me most: turning a promising demo
into something that can be tested, inspected, and improved.

Next step: re-run controlled benchmarks and compare the single-agent baseline
against a routed design using the same questions.

## X Drafts

### 1. Project Announcement

I am turning an agentic data-stack workshop into a measurable portfolio project.

The question: when is a routed AI analytics agent actually worth the extra latency, cost, and complexity?

Current focus: single-agent baseline, read-only SQL, metric checks, and benchmarkable evals.

### 2. Metric Semantics

One useful failure in my agentic analytics project:

The model could calculate non-blocked items and label the result as `blocker_rate`.

The tool call worked. The SQL ran. The answer looked plausible.

The metric was wrong.

That is why semantic guards matter.

### 3. Practical AI Adoption

The more I work on AI agents, the less impressed I am by "it called a tool."

The better questions:

Did it call the right tool?
Did it use the right metric?
Did it avoid unnecessary calls?
Can I inspect what happened?
Would the workflow survive repeated use?

### 4. Single Agent First

I am intentionally starting my agentic analytics project with a single-agent baseline.

Not because routing is uninteresting.

Because I want evidence before complexity.

If a routed design wins, it should win against the same questions, same data, and same evaluation criteria.

### 5. Learning Update

Today's applied AI lesson:

A correct-looking answer can still hide a bad business definition.

For my blocker-rate question, the canonical formula is simple:

`SUM(blocked) / COUNT(*)`

The hard part is making sure the agent does not confidently optimize the wrong thing.

## Portfolio Notes

Before sharing publicly:

- Confirm the README renders cleanly on GitHub.
- Add or verify sanitized screenshots for tool calls and traces.
- Re-run tests after any documentation or code changes.
- Do not publish raw benchmark claims unless the benchmark was re-run under the current code.
- Keep the post focused on the project evidence, not broad claims about expertise.
