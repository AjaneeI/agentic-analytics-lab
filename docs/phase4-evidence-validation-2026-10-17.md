# Independent Phase 4 evidence validation — October 17, 2026

**Nonconfirmatory preparation only. Phase 4 is not accepted, no analysis plan is
frozen, and Phase 5/held-out execution remain gated.**

This check validates the preserved 10-scenario, 3,000-dataset synthetic run at
commit `736f72a`. It does not select or approve an interval procedure. The
[original simulation](../experiments/phase4-calibration-20261017/existing-interval-simulation.json),
its script, original README and original verification logs remain unchanged.
The validator made no model/provider/database calls and read no benchmark-task
or held-out data. The regression suite separately uses existing test fixtures;
it does not execute a live benchmark.

## Independent numerical check

The new [validator](../scripts/validate_statistical_calibration.py) does not
import the simulation generator, production statistical helper, agent/runtime,
or benchmark modules. The separate
[validation report](../experiments/phase4-calibration-20261017/independent-summary-validation.json)
records its own source digest and the input digest. Reproduction uses a new
output path; the CLI refuses an existing output and refuses overwriting input:

```sh
python3 scripts/validate_statistical_calibration.py --input experiments/phase4-calibration-20261017/existing-interval-simulation.json --output /tmp/phase4-independent-validation-new.json
python3 -m unittest tests.test_validate_statistical_calibration tests.test_statistical_calibration tests.test_statistical_evidence -v
```

All 3,000 trials and 6,000 distinct data/bootstrap seeds passed. Specifically:

- Truth is recomputed from the stored probability arrays using exact rational
  arithmetic on their decimal representations. Every data/bootstrap seed is
  checked against the master/scenario/trial rule, as well as for global uniqueness.
- A separate implementation reconstructs net Bernoulli successes from each
  data seed and checks every point estimate. It preserves the declared paired,
  antithetic, family and run dependence. It does not use the stored estimates
  as the expected values when computing mean estimates.
- Stored interval endpoints are checked for finite values, order and the
  Boolean-effect range `[-1, 1]`. Inclusive coverage, strict zero exclusion,
  positive-only exclusion, widths and zero-width counts are recomputed from
  those endpoints. Stored per-trial flags are checked rather than trusted.
- All aggregate counts, rates and Monte Carlo standard errors agree. Wilson
  endpoints are independently derived by solving the binomial score quadratic;
  width standard errors use the centered sum of squares with `n-1` degrees of
  freedom. The existing width normal interval retains its original `1.96`
  multiplier. Floating agreement uses absolute and relative tolerance `1e-12`;
  this is a computational comparison tolerance, not a calibration criterion.
- Inference and generator source digests match the preserved input. Corruption
  tests reject changed summaries, seeds, flags, widths, estimates, source
  digests, invalid endpoints and an incorrect null label for nonzero truth.

No numerical summary disagreement was found. The original rounded table also
agrees with the independently recomputed values: family-shock coverage is
`237/300 = 79.0%`; run-shock coverage is `97/300 = 32.3%`; their null zero
exclusion rates are `63/300 = 21.0%` and `203/300 = 67.7%`. Near-ceiling data
contain 73 zero-width intervals; the positive-effect case excludes zero in
`153/300 = 51.0%` of datasets and is not labeled a null false-positive rate.
The original report and validation JSON both retain Monte Carlo intervals.

Local verification passed 25 focused tests and all 307 repository tests, plus
source compilation, the context protocol and whitespace checks. The separate
[verification record](../experiments/phase4-calibration-20261017/independent-validation-verification.json)
preserves exact commands, exit codes and test-log digests. The frozen sources,
task files and original calibration artifacts match `736f72a`. Hosted Python
3.11/3.12 CI and CodeQL were not run for this local addition.

**Limit:** bootstrap endpoints are preserved observations for this check. This
validator does not independently regenerate their 1,500,000 bootstrap draws,
prove the RNG, validate the scientific assumptions, or establish operating
rates for the default 10,000-draw helper. No expanded simulation was run. The
seed replay checks agreement with the declared generator; it does not prove
that this data-generating process describes the real benchmark.

## Method/code agreement ledger

This is a source audit of the existing method, not an approved replacement.
The inference source digest is
`ab07c438859bfa7d272f7a24425663477eb3a611aa3832c7568793ba7702a29e`.

| Element | Current implementation and preserved calibration | Agreement status |
|---|---|---|
| Point estimate | Equal-task mean of candidate-minus-baseline success proportions | Agrees with an equal-task form of the roadmap estimand; final weights remain open |
| Outer bootstrap | Uniformly sample `task_count` task indices with replacement; use the same selected task for both arms | Task identity is paired |
| Inner bootstrap | For each selected task, independently draw each arm's own number of repeat slots with replacement | Within-repeat pairing is not preserved; `paired` in the function name does not imply paired repeat draws |
| Endpoints | Sort bootstrap effects; linearly interpolate at `.025*(samples-1)` and `.975*(samples-1)` | This is the finite-draw percentile interval the simulation exercised |
| Positive fraction | Fraction of bootstrap effects strictly greater than zero | Diagnostic only; not a p-value, posterior probability or approved test |
| Method document | `docs/agent-evaluation-evidence-method.md` and its Wolfram example resample precomputed task deltas only | **Unresolved mismatch** with task+independent-arm-run code; original document and historical results remain unchanged |
| Public validation | Comparison validates Boolean outcomes, provenance, tasks/order and equal repeat counts | Equal counts do not establish paired repeat IDs, common seed blocks or execution ordering |
| Calibration target | Fixed-task, equal-weight mean of specified true Bernoulli differences | A synthetic diagnostic target; final inferential population remains open |

Existing `test_bootstrap_reflects_run_level_variability` in
`tests/test_statistical_evidence.py` exercises identical observed outcomes in
both arms and obtains an interval spanning both sides of zero. The preserved
perfect-pairing scenario likewise has zero point effect in every dataset but
positive interval width. These agree with independent within-arm resampling,
and explain why this is not the task-delta-only procedure in the method note.
No test or source claim resolves whether that procedure is scientifically
appropriate for the eventual owner-approved population and pairing design.

## Owner decision ledger — all approval gates remain open

These entries organize the unresolved decisions in the
[proposal](phase4-analysis-plan-proposal-2026-10-17.md); they are not decisions
made by this validation. No durable methodology decision was added to
`DECISIONS.md`.

| ID | Required owner decision | Evidence / constraint | State |
|---|---|---|---|
| P4-01 | Inferential population and estimand | Fixed tasks vs sampled task/family population changes the uncertainty target | Open |
| P4-02 | Task/family weights and absent-family handling | Current helper uses equal task weights; no outcome-driven renormalization approved | Open |
| P4-03 | Interval procedure and method/code agreement | Task-delta document differs from task+independent-arm-run code | Open |
| P4-04 | Actual repeat pairing, seeds and execution blocks | Equal run counts alone do not validate pairing; shared shocks can invalidate calibration assumptions | Open |
| P4-05 | Confidence/tails, bootstrap budget, calibration matrix and tolerances | Screening run uses 300 datasets and 500 draws; no scientific acceptance threshold supplied | Open |
| P4-06 | Invalid task/artifact exclusions and adjudication | No silently dropped, replaced or renormalized attempts | Open |
| P4-07 | Timeout handling and common time budget | Do not invent a Boolean score when the existing scorer cannot interpret an artifact | Open |
| P4-08 | Future infrastructure-only retry policy | Existing sprint prohibits tuning/retries after observed frozen runs; original attempts retained | Detailed future rule open |
| P4-09 | Harness failures, missingness and denominator | Distinguish pre-invocation failure from a started treatment failure without relabeling outcomes | Open |
| P4-10 | Primary comparison/endpoint and multiplicity | No confirmatory comparison hierarchy or family-wise allocation approved | Open |
| P4-11 | Minimum practical effect and acceptable operational burden | D-011 preserves separate quality/burden and Pareto reporting; no new numerical threshold selected | Open |
| P4-12 | Prerequisites, owner signoff and versioned freeze | Accepted Phase 2/3 evidence, protocol/task/scorer/analysis hashes and recorded owner approval required before held-out access | Not satisfied |

The current scope-observation validity blocker halts further Treatment A
execution under [issue #95](https://github.com/AjaneeI/agentic-analytics-lab/issues/95).
Its remedy is pending review; no remedy or statistical method is approved by
this validation. Phase 2 remains unqualified and the nine Phase 3
evaluator mismatches remain unresolved. Synthetic arithmetic verification does
not accept either prerequisite or advance a phase. Runtime overlap limitations
in the original calibration README also remain in force.

The next bounded step remains owner review of P4-01–P4-12 and the prerequisite
blockers. Any approved candidate-method calibration or implementation must use
its own preserved artifact and authorization; these checks cannot select it.
