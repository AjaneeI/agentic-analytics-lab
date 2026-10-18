# Phase 4 statistical analysis plan proposal — 2026-10-17

**Status: nonconfirmatory model-free preparation. NOT a frozen analysis plan,
methodology approval, Phase 4 acceptance, or authorization to enter Phase 5.**

Owner authorization is limited to the October 17–23 sprint in
[issue #94](https://github.com/AjaneeI/agentic-analytics-lab/issues/94) and
[issue #95](https://github.com/AjaneeI/agentic-analytics-lab/issues/95).
The no-Codex operating rule is superseded only within that scope. No automatic
reviews, model/provider calls, benchmark executions, held-out access, scorer
changes, or inference changes are part of this preparation.

## Requirements and acceptance criteria

The [canonical Notion roadmap](https://app.notion.com/p/3f18182531ca81679e9de110c8a8e2be)
defines the task as the primary experimental unit. Its primary estimand is:

> For each task, compute the observed candidate-minus-baseline difference in
> success proportion across matched repeats. Report the mean paired task effect
> under the predeclared task/family weighting rule.

The planned bank is 24 development and 24 held-out tasks, three per each of
eight families, with three matched trials per configuration and task. This
preparation reads neither held-out tasks nor outcomes. It does not authorize
completing or running either bank. The roadmap does not yet specify numerical
weights or resolve the resampling population.

Acceptance of this preparation requires an inspectable audit of the current
implementation; reproducible, standard-library simulations with seeds,
parameters, coverage, width, false-positive diagnostics and Monte Carlo
uncertainty; a proposal listing all unresolved owner decisions; and preserved
frozen inference/scoring/task/security files. Actual Phase 4 exit additionally
requires accepted Phase 2/3 evidence, resolved documentation/code agreement,
owner-approved methodology, and a versioned pre-held-out freeze. None follows
from passing the added unit tests.

## Existing rules and implementation audit

| Surface | Existing behavior | Gap to resolve before freeze |
|---|---|---|
| Primary point estimate | `compare_architectures` computes the arithmetic mean of candidate-minus-baseline per-task success proportions | Equal task weights are implicit; no explicit family weights or weighted estimator interface |
| Repeated outcomes | Boolean `task_success`; same tasks/order and equal run counts across architectures | No matched repeat ID, execution-order, or shared-seed validation; matching counts does not establish paired repeats |
| Provenance | Benchmark schema, model, dataset, question source and contract SHA must match; providers may differ as part of treatment | Protocol must identify task-bank, scorer and analysis versions and exact treatment composition |
| Interval in code | `paired_hierarchical_bootstrap` samples task indices uniformly, then samples baseline and candidate outcomes **independently** within each selected task; percentile endpoints use linear interpolation | Task pairing is preserved; within-repeat pairing and common repeat/family shocks are not. Its name does not imply paired repeat draws |
| Interval in method document | `docs/agent-evaluation-evidence-method.md` says resample task-level deltas only; its Wolfram example does that too | Not the same procedure as the current implementation |
| Interval in historical generated report | `docs/generated/accepted-q1-q6-architecture-evidence.md` explicitly reports task+run resampling, seed 42 and 100,000 draws | Historical results must retain their original method and provenance; no retrospective replacement |
| CLI descriptions | `scripts/compare_architecture_evidence.py` calls the method task-level bootstrap | Description underspecifies the current second resampling stage |
| Interpretation | Existing code labels interval descriptive for frozen tasks and disclaims unseen-task generalization | Whether uncertainty targets fixed-task repeat randomness or a task population remains unspecified; bootstrapping tasks adds task variation even when the target conditions on those tasks |
| Positive fraction | Fraction of bootstrap estimates strictly above zero | Not a p-value, posterior probability, or approved decision rule |
| Input validation | Public comparison rejects non-Boolean outcomes, mismatched metadata/task order, provenance and run counts; at least two runs and tasks required | No specified missing-attempt/exclusion policy. Low-level helper is not a full public validation interface |

The frozen helper and all existing output semantics remain unchanged in this
branch. This audit records a real mismatch rather than silently resolving it.

## Simulation design and reproducibility

`scripts/calibrate_statistical_interval.py` calls the **existing**
`paired_hierarchical_bootstrap` directly. It generates Boolean matrices only;
there are no benchmark fixtures, ground-truth references, model APIs, database
connections, or held-out inputs. An isolated-process test verifies that imports
do not load agent/model/tool/routing/System Benchmark runtime modules.

The common diagnostic target is the **fixed-task, equally weighted mean of the
true Bernoulli probability differences**, conditional on the scenario's task
probabilities. It is not a claim that this is the already-approved inferential
target. There are three matched-index repeats per task in every scenario.

| Scenario | Tasks | Data-generating structure | True mean effect |
|---|---:|---|---:|
| `small_independent` | 6 | Independent arms/tasks/repeats, both p=.5 | 0 |
| `independent` | 24 | Independent arms/tasks/repeats, both p=.5 | 0 |
| `perfect_pairing` | 24 | Identical baseline/candidate Boolean outcomes at every task/repeat, both p=.5 | 0 |
| `negative_pairing` | 24 | Candidate is complement of baseline at each task/repeat, both marginals p=.5 | 0 |
| `heterogeneous_difficulty` | 24 | Eight difficulty levels .1,.2,.3,.4,.6,.7,.8,.9; three independent tasks each; both arms same probabilities | 0 |
| `heterogeneous_effect` | 24 | Twelve tasks baseline .2/candidate .8; twelve baseline .8/candidate .2; independent draws | 0 |
| `family_shock` | 24 | Eight independent families, three tasks each share all per-arm/per-repeat outcomes; arms independent | 0 |
| `run_shock` | 24 | All tasks share each arm's repeat outcomes; arms independent | 0 |
| `near_ceiling` | 24 | Independent outcomes, both p=.99 | 0 |
| `positive_effect` | 24 | Independent baseline p=.5/candidate p=.7 | +.2 |

The perfect-pairing, family-shock and run-shock cases are deliberate dependence
stress tests, not estimates of dependence in the actual bank. Family membership
is synthetic, with no observed development or held-out performance fitted into
these parameters.

Run from the repository root:

```sh
python3 scripts/calibrate_statistical_interval.py --trials 300 --bootstrap-samples 500 --seed 20261017 --output experiments/phase4-calibration-20261017/existing-interval-simulation.json
python3 -m unittest tests.test_statistical_calibration tests.test_statistical_evidence -v
python3 -m unittest discover -s tests -v
python3 scripts/check_project_context.py
git diff --check
```

The JSON records the script and unchanged inference source SHA-256, Python
version, probability arrays, dependence, repeat count, all per-dataset estimates
and interval endpoints, master/scenario/trial/bootstrap seeds, and aggregate
diagnostics. Scenario seed is `20261017 + 100000 * scenario_index`; trial data
seed is `scenario_seed + 2 * trial`, and bootstrap seed is that seed plus one.
Re-running from identical sources and Python RNG behavior reconstructs every
synthetic matrix. There is no runtime/timestamp field that makes outputs vary.

Coverage means inclusive interval coverage of the known scenario truth. A
two-sided false-positive diagnostic is an interval entirely above or below
zero **only for true-zero scenarios**. Positive-only false positives are also
recorded. For the +.2 scenario, zero exclusion is labeled a diagnostic detection
rate, never a false-positive rate. Neither definition approves interval
exclusion as a future hypothesis test.

Proportions include outer-simulation Monte Carlo standard errors and 95% Wilson
intervals, retaining uncertainty at zero/one observed events. Width includes its
mean, Monte Carlo standard error and an approximate normal 95% interval. Those
Monte Carlo intervals quantify simulation precision for this finite-500-draw
procedure. They do not validate the assumed data-generating process or establish
the operating rates of the default 10,000-draw procedure. Five hundred bootstrap
draws per dataset is a screening budget; candidate final methods need larger
calibration and independent seeds before freeze.

See `experiments/phase4-calibration-20261017/README.md` for the preserved outcome
table and interpretation after the simulation completes. Execution may be
paused while a real local measurement is active to avoid CPU interference;
pausing/resuming an unchanged synthetic RNG stream does not select or retry
benchmark outcomes.

## Proposed analysis plan — owner decisions, not adopted rules

Let `Y[a,t,r]` be the existing deterministic Boolean task-success outcome.
For the planned three matched repeats, let
`d[t] = (1/3) * sum_r (Y[candidate,t,r] - Y[baseline,t,r])`.
The reported primary effect is `sum_t w[t] * d[t]`, with nonnegative
predeclared `w[t]` summing to one. Report percentage points alongside raw task
success counts, denominators and per-task differences. Repeats do not become
additional independent task observations.

| Required owner decision | Concrete proposal/alternatives for approval | Current status |
|---|---|---|
| Population and estimand | Decide whether uncertainty conditions on the frozen task set (repeat randomness only) or also models task sampling within a family/template population. Preserve the roadmap point estimand in either case; state the target in every result | Open |
| Weights and missing families | Propose equal family weights `1/8`, equal task weights within each family `1/(8*n_family)`. With all planned families containing three tasks this equals `1/24`. Owner must approve what happens if a task/family is invalid; no silent renormalization after outcomes | Open |
| Interval and resampling | Resolve task-delta-only vs existing task+independent-arm-run method. Candidates for model-free comparison include task-delta resampling, a genuinely paired task/run method, and fixed-task paired repeat/block methods if shared repeat shocks exist. Which method is appropriate depends on the approved population and actual repeat pairing; no method is selected here | Open; known doc/code mismatch |
| Repeat matching | Predeclare matched repeat IDs, seeds where applicable, ordering/blocking and treatment version; verify task×repeat alignment before analysis. Equal counts alone are insufficient | Open |
| Interval size and calibration | Specify confidence level, tail rule, bootstrap seed/draw count, tolerable coverage/FPR departure and width, and calibration matrix before selecting a method. Nominal 95% in existing code is not evidence of 95% coverage | Open |
| Exclusions | Predeclare invalid-task and invalid-artifact reasons, identify who adjudicates without using treatment outcomes, preserve all exclusions and their counts, and show sensitivity if exclusions matter | Open |
| Timeouts | Propose retaining a started valid attempt that times out in its assigned task/repeat slot as an unsuccessful operational outcome, subject to the existing scorer contract. Freeze time budget identically across arms. Do not invent a Boolean score for an artifact the scorer cannot interpret | Open; no scorer change here |
| Retry policy | Sprint authorization prohibits tuning/retries after observed frozen runs. Preserve the original outcome. Any future infrastructure-only rerun rule must be approved and versioned before exposure, with original attempts retained | Existing sprint boundary retained; detailed future rule open |
| Harness failures | Distinguish pre-invocation failure from a started treatment failure; preserve raw records and provenance. Owner must decide denominator/missingness and any predeclared infrastructure recovery; never silently drop, replace, or relabel failures | Open |
| Multiplicity | Propose one named primary candidate-vs-strong-baseline comparison and one primary endpoint. If multiple confirmatory treatments/endpoints are retained, predeclare family-wise control or hierarchy; family/route breakdowns remain descriptive unless separately allocated | Open |
| Practical threshold | Owner sets a minimum meaningful success improvement in percentage points and acceptable latency/call/cost burden before exposure. Keep D-011's separate quality/burden metrics and Pareto reporting; no invented weighted winner score | Open; no numerical threshold supplied |
| Analysis/data freeze | Record task-bank/scorer/protocol/analysis hashes, exclusions and pairing/weights, accepted Phase 2/3 evidence links, named gate owner and signed/recorded owner decision before held-out access | Not satisfied |

Three repeats do not automatically provide enough information to estimate
within-task variance, pairing covariance, family dependence or common run
shocks reliably. New methods or additional repeats require explicit approval
before frozen exposure; this preparation does not change the roadmap's repeat
count.

## Gate disposition and next bounded step

Preparation can establish an implementation diagnostic only. Phase 4 remains
**not accepted / not frozen** while the inference mismatch, weights, population,
failure rules, multiplicity and practical threshold remain open. Phase 2/3
acceptance is not inferred from this work. Phase 5 entry and held-out execution
remain gated.

The prerequisite evidence now records a
[Treatment A error with no score](https://github.com/AjaneeI/agentic-analytics-lab/pull/97)
and [nine unresolved evaluator mismatches](https://github.com/AjaneeI/agentic-analytics-lab/pull/98).
Neither prerequisite is accepted. The statistical preparation cannot convert
either result into an accepted gate.

The next bounded step is owner review of these decisions, followed by approved
model-free comparison/calibration of the chosen candidate procedures, a
documented implementation/method agreement, and a versioned analysis-plan
freeze after accepted prerequisite evidence. Historical Q1–Q6 results and their
analysis remain intact. No durable methodological decision is recorded in
`DECISIONS.md` because none has been approved.
