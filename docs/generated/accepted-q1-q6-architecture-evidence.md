# Accepted Q1-Q6 Architecture Evidence Analysis

## Evidence identity

This analysis uses the exact preserved GitHub Actions artifacts from the
repository's accepted matched comparison:

- single-agent baseline workflow run: `35755961530`, artifact `10708618392`;
- oracle-metadata routed workflow run: `35760422536`, artifact `10709533113`.

Both artifacts contain three runs of the frozen Q1-Q6 benchmark. They predate
the repository's embedded `metadata.provenance.benchmark_contract_sha256`
field, so this is explicitly a **legacy accepted-evidence analysis**. Benchmark
identity is attested by the accepted repository/workflow evidence rather than
embedded in the historical JSON. Future comparisons must use the stricter
provenance check in `src/evals/statistical_evidence.py`.

## Observed task success

| Architecture | Successful tasks | Observations | Success rate |
|---|---:|---:|---:|
| Single agent | 12 | 18 | 66.7% |
| Oracle-metadata routed | 17 | 18 | 94.4% |

Observed delta: **+27.8 percentage points** for oracle-metadata routed
execution.

Per-task recurrence:

| Task | Single agent | Oracle routed |
|---|---:|---:|
| Q1 | 3/3 | 3/3 |
| Q2 | 3/3 | 3/3 |
| Q3 | 0/3 | 3/3 |
| Q4 | 3/3 | 3/3 |
| Q5 | 0/3 | 3/3 |
| Q6 | 3/3 | 2/3 |

The architecture difference is therefore concentrated: routing converted stable
Q3/Q5 failures into stable passes, while Q6 has one scored failure in the routed condition. Q6 uses the same local worker; that observation alone does not identify a route-inference regression.

**Task success is not execution completion.** The accepted comparison distinguishes completed agent executions from correct, grounded task outcomes. The 12/18 and 17/18 totals above are scored task-success observations, not counts of processes that avoided an exception.

## Descriptive uncertainty

A hierarchical bootstrap was run over the exact accepted outcomes with seed 42
and 100,000 samples. Each bootstrap replicate resampled task IDs and then
resampled observed repeated outcomes within each selected task.

- observed mean delta: **+27.8 percentage points**;
- descriptive 95% bootstrap interval: **-11.1 to +66.7 percentage points**;
- bootstrap fraction with positive routed-minus-single delta: **0.868**.

This interval is intentionally conservative about the tiny evidence base. Six
tasks with three repeats each are not enough for a precise general performance
claim. The result characterizes the accepted frozen task set; it does not
establish unseen-task generalization.

## Operational burden

Mean per six-task run:

| Metric | Single agent | Oracle routed |
|---|---:|---:|
| Tool calls | 5.0 | 5.0 |
| Model calls | 11.0 | 1.0 |
| Input + output tokens | 9,270.3 | 834.0 |
| End-to-end latency | 217.002 s | 33.899 s |

Relative to the single-agent condition, the routed condition used:

- the **same mean tool-call count**;
- about **90.9% fewer model calls**;
- about **91.0% fewer recorded tokens**;
- about **84.4% lower mean end-to-end latency**.

These are GitHub-hosted matched-run measurements. They should not be mixed with
Apple Silicon/local latency measurements.

## Complexity/value frontier

Using task success as a maximize metric and latency, tool calls, model calls,
and tokens as minimize metrics, the accepted oracle-metadata routed point
Pareto-dominates the accepted single-agent point:

- higher observed task success;
- lower latency;
- equal tool calls;
- fewer model calls;
- fewer tokens.

This is descriptive dominance on these observed metrics, not a population-level result. The small sample, supplied oracle route, unmeasured maintenance costs, and recorded runner-environment differences limit the conclusion. Latency remains directional rather than a hardware-controlled causal estimate.

## Claim boundary

The correct conclusion is:

> On the accepted frozen Q1-Q6 GitHub-hosted comparison, supplying the known
> benchmark route improved observed task success and reduced model/latency/
> token burden enough to Pareto-dominate the strong single-agent baseline on
> the declared metrics.

It is **not** evidence that:

- natural-language routing works;
- multi-agent systems are generally better;
- the effect generalizes to unseen tasks;
- the six-task benchmark is large enough for a precise population-level effect.

The evidence-expansion program is System Benchmark v1. Follow [STATUS.md](../../STATUS.md) for the next bounded development experiment and its integration gates. This legacy analysis is not authorization to skip directly to held-out execution, delegated workers, or more framework code.
