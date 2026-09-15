# Publishing Plan

This plan prepares Agentic Analytics Lab for GitHub and social media without
overstating the project's maturity.

## Public Positioning

One-sentence version:

> Agentic Analytics Lab evaluates when a routed AI analytics agent is worth the
> added latency, cost, tool calls, and operational complexity.

Portfolio angle:

- practical AI adoption
- agent evaluation
- read-only tool use
- data-backed answers
- semantic metric checks
- cost and latency tradeoffs
- evidence before orchestration

## GitHub Readiness Checklist

- [x] README explains the project in plain language.
- [x] README separates workshop baseline from original portfolio extension.
- [x] Safety and evaluation criteria are visible.
- [x] Repository map points to docs, evals, experiments, source, and tests.
- [x] Social posting copy is saved as draft-only documentation.
- [ ] GitHub About description is updated.
- [ ] GitHub topics are updated.
- [ ] Sanitized screenshots are added or linked.
- [ ] Current benchmark claims are verified against the current code.

## Evidence To Add Before A Bigger Launch

- sanitized successful tool-call screenshot
- sanitized Langfuse trace list
- sanitized aggregated trace graph
- sanitized expanded trace graph
- controlled benchmark table
- single-agent versus routed-agent comparison once routed prototype exists

## LinkedIn Plan

Use one polished narrative post after the GitHub README renders correctly.

The post should focus on:

- why the project exists
- what has been built so far
- one concrete failure caught by testing or guardrails
- what the next experiment will compare

Do not claim production readiness or final benchmark wins.

Draft copy lives in [social-posting-kit.md](social-posting-kit.md).

## X Plan

Use short learning-in-public posts. Rotate between:

- project announcement
- semantic metric failure
- read-only tool safety
- single-agent baseline before routing
- evidence before complexity
- debugging and observability notes

Draft copy lives in [social-posting-kit.md](social-posting-kit.md).

## Final Review Before Posting

- Run the full test suite.
- Check `git status` for unintended files.
- Confirm no secrets or private identifiers appear in screenshots.
- Confirm benchmark language matches current, reproducible results.
- Keep posting, profile updates, and repository changes as separate approvals.
