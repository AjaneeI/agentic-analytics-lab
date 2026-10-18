# Existing interval: synthetic calibration diagnostics — October 17, 2026

**Nonconfirmatory model-free preparation. Phase 4 is NOT accepted and no analysis plan is frozen.**

This artifact executes the unchanged `src.evals.statistical_evidence.paired_hierarchical_bootstrap` on synthetic Boolean outcomes. It contains no benchmark/model outcomes or held-out data. See [the proposal](../../docs/phase4-analysis-plan-proposal-2026-10-17.md) for the source audit, design, unresolved owner decisions and exact command.

## Preserved run

- Base repository commit: `58add5e`.
- Python: `3.14.7`.
- Ten scenarios, 300 outer synthetic datasets per scenario (3,000 total), 500 bootstrap draws per dataset (1,500,000 total). Every task has three repeat slots.
- Master seed: `20261017`; all 6,000 data/bootstrap seeds are distinct and preserved per dataset, together with estimates, interval endpoints and outcomes.
- Target: fixed-task equal-weight mean of true candidate-minus-baseline success probabilities. This target is a calibration diagnostic; approval of the final inferential population is still required.
- No model/provider calls, task-bank loads, benchmark execution, held-out access or inference changes.

## Results

Rates and Wilson intervals below are percentages. Width and its Monte Carlo interval are percentage points. Wilson intervals describe outer Monte Carlo uncertainty for the finite-500-draw procedure, not uncertainty about the data-generating assumptions or calibration of the default 10,000-draw method.

| Scenario | Tasks | Coverage % [MC 95%] | Two-sided null FP % [MC 95%] | Mean width pp [MC 95%] | Zero-width datasets |
|---|---:|---:|---:|---:|---:|
| small_independent | 6 | 98.7 [96.6, 99.5] | 1.3 [0.5, 3.4] | 77.4 [76.1, 78.7] | 0 |
| independent | 24 | 99.3 [97.6, 99.8] | 0.7 [0.2, 2.4] | 41.0 [40.6, 41.4] | 0 |
| perfect_pairing | 24 | 100.0 [98.7, 100.0] | 0.0 [0.0, 1.3] | 26.3 [26.1, 26.5] | 0 |
| negative_pairing | 24 | 96.0 [93.1, 97.7] | 4.0 [2.3, 6.9] | 51.6 [51.1, 52.1] | 0 |
| heterogeneous_difficulty | 24 | 98.7 [96.6, 99.5] | 1.3 [0.5, 3.4] | 34.3 [33.9, 34.6] | 0 |
| heterogeneous_effect | 24 | 100.0 [98.7, 100.0] | 0.0 [0.0, 1.3] | 57.9 [57.4, 58.4] | 0 |
| family_shock | 24 | 79.0 [74.0, 83.2] | 21.0 [16.8, 26.0] | 40.0 [39.4, 40.6] | 0 |
| run_shock | 24 | 32.3 [27.3, 37.8] | 67.7 [62.2, 72.7] | 25.6 [24.8, 26.5] | 16 |
| near_ceiling | 24 | 99.7 [98.1, 99.9] | 0.3 [0.1, 1.9] | 6.3 [5.8, 6.8] | 73 |
| positive_effect | 24 | 98.7 [96.6, 99.5] | N/A: true effect +20pp | 39.5 [39.1, 39.9] | 0 |

For the true +20pp scenario, the interval excludes zero in 51.0% of datasets (MC 95% interval: 45.4–56.6%). This is a diagnostic detection rate, not a false-positive rate. The JSON separately retains positive-only null false-positive rates, Monte Carlo standard errors and every dataset outcome.

## Interpretation and limits

- Independent cases are conservative in this screening run; that behavior is not robust to shared family or repeat conditions.
- Under identical paired outcomes the observed point estimate is exactly zero for every dataset, but independent arm resampling gives a mean interval width of 26.3pp. The procedure preserves task pairing, not repeat pairing.
- Perfectly correlated tasks within eight three-task families give 79.0% coverage and 21.0% null zero exclusion. Shared run shocks give 32.3% coverage and 67.7% null zero exclusion. These intentionally strong dependence stress tests identify an assumption that needs resolution; they do not estimate real benchmark correlations.
- Near-ceiling outcomes can yield zero-width intervals despite only three repeats per task. High null coverage here is not proof of precise uncertainty estimation.
- Task-level-only documentation, task+independent-arm-run implementation, resampling population, family weights and repeat matching remain unresolved. No alternate method was implemented or selected, and no current method is approved for confirmatory inference.
- Five hundred bootstrap draws per dataset and 300 outer datasets are a screening budget. Use the preserved Monte Carlo intervals when assessing differences; final approved methods need separately authorized calibration at the frozen draw count. No additional expanded runs were performed.

## Prerequisites and measurement overlap

[Treatment A draft #97](https://github.com/AjaneeI/agentic-analytics-lab/pull/97) records an HTTP 404 ClickHouse error after 52.42 seconds and no score; [Phase 3 draft #98](https://github.com/AjaneeI/agentic-analytics-lab/pull/98) records nine unresolved evaluator mismatches. Phase 2/3 are not accepted. This preparation cannot advance Phase 4/5 or authorize held-out execution.

CPU simulation overlap with the Treatment A window occurred. The recorded Treatment A window was 2026-10-18 00:11:19.638056–00:12:12.057710 UTC (October 17 EDT). The exact overlap duration and calibration pause timestamp were not measured. The synthetic process was paused on request and resumed after Treatment A stopped, preserving its RNG state; it was not rerun or tuned. This does not establish resource-control isolation, the ordering of the pause versus the failed query, or any cause of the HTTP 404. Treat runtime timing/resource comparisons as confounded by this overlap.

## Verification and provenance

- `unittest-focused.txt`: exact focused command `python3 -m unittest tests.test_statistical_calibration tests.test_statistical_evidence -v` — 14 passed.
- `unittest-full.txt`: exact full command `python3 -m unittest discover -s tests -v` — 296 passed.
- Tests cover Wilson boundary uncertainty, preserved pairing/clustering in generated data, exact replay of the existing helper, deterministic replay, nonzero-truth labeling, exact known truth and runtime-import isolation.
- Compilation, context protocol, staged whitespace and unchanged frozen-source checks are recorded in `verification.json`.
- Python 3.11/3.12 hosted CI and CodeQL have not been run for this unpublished local branch.
- Per-branch Codex credit consumption is not observable here. This script has no paid-provider dependency and makes no provider calls.

| File | SHA-256 |
|---|---|
| `src/evals/statistical_evidence.py` | `ab07c438859bfa7d272f7a24425663477eb3a611aa3832c7568793ba7702a29e` |
| `scripts/calibrate_statistical_interval.py` | `f3ba578b31074eb57cb88d9870d46d9caef4f1f4e95056fd26bef84ec1650fac` |
| `existing-interval-simulation.json` | `81a41a2f31cb28e0480416e63b8eba58d877f3bd866174cf5c794906ca273768` |
| `unittest-full.txt` | `3078b2b3401e95a94733ab84168a1e5aa00ce74d2972dc8fdc1631796175372c` |
| `unittest-focused.txt` | `76b60da6d0a42f45ca0334668bce6d204369ad58281ddb4d767c8fc856e2b152` |
