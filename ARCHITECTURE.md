# Architecture

## Workshop baseline

The original workshop path is preserved as historical context:

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

## Current benchmark baseline

The architecture used for the controlled single-agent benchmark is smaller and local-first:

```text
Frozen evaluation question
  ↓
Python SingleAgent
  ↓
Ollama qwen2.5:7b
  ↓ tool decision
Read-only ClickHouse query tool
  ↓
Synthetic delivery_work_items table
  ↓
Captured query rows
  ↓
Final answer
  ↓
Deterministic evaluator
```

The evaluator keeps execution success separate from answer correctness. For Q1-Q5 it checks the required answer values against captured ClickHouse evidence. Q6 uses a deterministic epistemic-behavior check and does not require a database call. The harness also records model calls, tool calls, end-to-end latency, and Ollama token/timing metadata when available.

This benchmark architecture, not the historical LibreChat/Claude workshop run, is the comparison anchor for the future routed-agent experiment.

## Planned comparison

```text
                         ┌──────────────────────┐
Evaluation question ────▶│ Router / Lead Agent  │
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
                         Same read-only tool layer
                                    ▼
                         Same ClickHouse dataset
                                    ▼
                         Same deterministic evaluator
```

The routed version has not been implemented or evaluated yet.

## Comparison invariants

A fair architecture comparison must keep these constant unless a necessary baseline correction is applied to both sides:

- synthetic seed-42 dataset
- six frozen evaluation questions
- expected-answer contract
- read-only ClickHouse tool
- delivery metric definitions
- deterministic scoring rules
- measurement methodology

## Design principles

- Start with a trustworthy single-agent baseline before adding orchestration.
- Route only when specialization measurably improves outcome quality or efficiency.
- Keep tool access least-privilege and read-only by default.
- Treat SQL safety, metric semantics, and answer correctness as separate concerns.
- Prefer one correct analytical query over multiple unnecessary tool calls.
- Capture correctness, evidence consistency, model/tool calls, latency, tokens, and failure modes for every comparison run.
- Prefer synthetic/public data for the publishable version.
