# Benchmark Reporting Layer

The evaluator writes structured JSON with correctness, grounding, tool-use,
model-call, token, latency, and failure metadata.

This reporting layer converts reviewed result JSON into deterministic Markdown
so evidence can be inspected before it is used in portfolio claims.

## Single-agent usage

Run the benchmark in a local environment with the intended ClickHouse dataset
and Ollama model available:

    python3 scripts/run_single_agent_eval.py

Then render a Markdown report:

    python3 scripts/render_benchmark_report.py \
      experiments/results/single_agent_qwen2.5_7b.json

The default output is:

    docs/generated/single-agent-benchmark-report.md

You can override the destination:

    python3 scripts/render_benchmark_report.py \
      experiments/results/single_agent_qwen2.5_7b.json \
      --output docs/generated/reviewed-run.md

## Repeatability

A single generated report is not enough to establish the accepted comparison
anchor.

Use the repeatability orchestration to run the unchanged benchmark three times
and aggregate only compatible configurations:

    python3 scripts/run_repeatability_pass.py

See [Benchmark Repeatability](benchmark-repeatability.md) for the hosted and
local evidence lanes.

## Routed comparison

The repository also contains a matched oracle-metadata routed evidence lane.
That condition reuses the frozen Q1-Q6 contract while changing the execution
architecture.

Its accepted result is summarized in [Portfolio Results](portfolio-results.md).

The label matters: the routed comparison uses frozen benchmark metadata to
supply route-relevant facts. It must not be reported as learned routing,
natural-language routing, or a general multi-agent result.

## Publishing rule

Generating a report does not make a run a current benchmark.

Before publishing a result, verify:

- the intended dataset and seed;
- frozen question set or explicitly versioned successor benchmark;
- expected model/runtime identity;
- deterministic evaluator;
- read-only tool contract;
- metric definitions;
- benchmark schema and provenance;
- execution environment for hardware-sensitive comparisons;
- failed cases and unsupported claims.

Preserve the raw evidence artifact and exact commit that produced the reviewed
summary.

Portfolio reporting should lead with validated outcomes and claim boundaries,
not with the number of agents or frameworks used.
