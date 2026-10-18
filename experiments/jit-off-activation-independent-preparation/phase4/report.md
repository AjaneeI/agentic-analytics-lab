# Preserved Phase 4 calibration: independent activation follow-up

**Arithmetic verified within scope; methodology needs owner decisions. No method is selected or frozen.** This model-free follow-up changes no production code, preserved experiment, decision, task, scorer or criterion. It performs no model, ClickHouse, held-out or provider access and no new simulation. The separate authorization for JIT-off activation and Treatment A waiting state is not authorization for this audit to run a treatment or diagnostic.

The original worktree remains at `403eda9b0ea47da9d6690e8750517b883ddaf4a9`, clean in both staged and unstaged checks. Its historical pending-scope wording is superseded by the approved scope and decision brief; this audit does not reopen that approval or infer a new qualification result. The Phase 3/4 decision brief remains a proposal, with statistical decisions unresolved.

## Recomputed evidence

[Independent endpoint audit](independent-endpoint-audit.json) checked all **10 scenarios, 3,000 endpoint records and 6,000 unique seeds**, with **zero numerical summary disagreements**. It independently derives truth with rational arithmetic, coverage, zero exclusion, positive-only exclusion, widths, zero-width counts, mean estimates, Monte Carlo SEs and intervals. Wilson bounds are computed by bisection of the binomial score inequality, without importing the simulation, prior validator or production inference helper. The `1e-11` agreement tolerance is a floating-point check, not scientific acceptance.

The preserved study used 300 outer datasets per scenario and 500 bootstrap draws per dataset (1.5 million draws already performed historically). **The MC denominator is 300 datasets, not 1.5 million draws.** Each proportion below has its own outer MC 95% Wilson interval. Width is in percentage points, with the preserved approximate normal 95% MC interval for its mean. The JSON retains full precision and positive-only Wilson intervals.

| Scenario | Coverage, MC 95% | Two-sided null false-positive diagnostic, MC 95% | Positive-only null events | Mean width pp, MC 95% | Zero widths /300 |
|---|---|---|---|---|---|
| `small_independent` | 98.7% [96.6, 99.5] | 1.3% [0.5, 3.4] | 1/300 | 77.38 [76.07, 78.68] | 0 |
| `independent` | 99.3% [97.6, 99.8] | 0.7% [0.2, 2.4] | 2/300 | 41.01 [40.65, 41.37] | 0 |
| `perfect_pairing` | 100.0% [98.7, 100.0] | 0.0% [0.0, 1.3] | 0/300 | 26.31 [26.09, 26.52] | 0 |
| `negative_pairing` | 96.0% [93.1, 97.7] | 4.0% [2.3, 6.9] | 4/300 | 51.63 [51.12, 52.14] | 0 |
| `heterogeneous_difficulty` | 98.7% [96.6, 99.5] | 1.3% [0.5, 3.4] | 2/300 | 34.29 [33.92, 34.65] | 0 |
| `heterogeneous_effect` | 100.0% [98.7, 100.0] | 0.0% [0.0, 1.3] | 0/300 | 57.92 [57.43, 58.42] | 0 |
| `family_shock` | 79.0% [74.0, 83.2] | 21.0% [16.8, 26.0] | 33/300 | 39.99 [39.38, 40.60] | 0 |
| `run_shock` | 32.3% [27.3, 37.8] | 67.7% [62.2, 72.7] | 98/300 | 25.62 [24.78, 26.47] | 16 |
| `near_ceiling` | 99.7% [98.1, 99.9] | 0.3% [0.1, 1.9] | 1/300 | 6.31 [5.80, 6.81] | 73 |
| `positive_effect` | 98.7% [96.6, 99.5] | N/A: true +20pp | N/A | 39.53 [39.14, 39.91] | 0 |

At true +20pp, 153/300 (51.0%) intervals exclude zero; that is a detection diagnostic, never a null false-positive rate. Family-shock and run-shock rates are dependence stress tests, not estimates of actual benchmark dependence. Near-ceiling zero-width intervals (73/300) and run-shock zero widths (16/300) remain reported. Neither unusual widths nor rates supply a new acceptance cutoff.

## Estimand and actual resampling unit

Let `d[t] = mean_r(Y[candidate,t,r] - Y[baseline,t,r])`. With equal repeat counts, linearity makes this point estimate equal to `mean_r(Y[candidate,t,r]) - mean_r(Y[baseline,t,r])`; that equality does **not** establish repeat pairing or the right variance. The current aggregate is the equal-task mean of these deltas. The synthetic truth conditions on the specified task probabilities, so it is a fixed-task, equal-weight diagnostic target, not an approved population estimand.

[Source anchors and twelve-decision ledger](method-code-audit.json) record source hashes and exact line ranges. The code draws task IDs with replacement and reuses each selected ID in both arms, then independently resamples baseline and candidate repeat slots. It preserves task identity but not repeat pairing, family clusters or common run blocks. Public checks of task order and equal counts do not identify paired repeat IDs/seeds. The method note instead says to resample already-computed task deltas only. This demonstrated mismatch remains open.

The perfect-pairing scenario is a concrete diagnostic: every stored point effect is zero, yet the existing method's mean interval width is 26.31pp. A bootstrap solely of those zero task deltas would be degenerate. This demonstrates a procedure difference; it does not select the appropriate replacement or prove how real repeats depend on each other.

## What remains unverified

The source stores endpoints, estimates, seeds, probabilities and flags, **not raw Boolean matrices or bootstrap draw arrays**. This follow-up generates neither. It verifies endpoint summaries and necessary point-estimate lattice/identical-arm invariants, but does not independently regenerate bootstrap endpoints or rederive the other point estimates from raw outcomes. The prior preserved independent validation replayed 3,000 point estimates; it is separately hashed, not misrepresented as a new replay here.

Wilson intervals measure outer simulation precision for the finite-500-draw procedure. They do not establish the default 10,000-draw procedure's rates, incorporate all inner-bootstrap Monte Carlo error as a separate estimate, validate the data-generating model, or establish calibration under real task/repeat dependence. No pooled cross-scenario success rate or method winner is inferred. The input scope is sufficient to verify summaries; it is insufficient to validate replacement methods. No new simulations are needed to repair a missing summary, because these summaries are present and agree.

## Owner decisions: all twelve retained

| ID | Current state | Exact next decision |
|---|---|---|
| P4-01 | Open | Specify the population, parameter and uncertainty target: fixed tasks conditional on repeats, or sampled tasks/families. |
| P4-02 | Open | Specify task/family weights and absent/invalid-family handling before selecting the estimator. Equal-task and balanced equal-family arithmetic do not supply approval. |
| P4-03 | Open — demonstrated mismatch | Name the approved interval procedure and exact code/document versions. Task-delta resampling and task plus independent-arm-repeat resampling differ. |
| P4-04 | Open | Define matched repeat IDs, seeds, ordering and shared blocks; identify independent sampling units. Equal repeat counts do not prove pairing. |
| P4-05 | Open | Specify confidence/tails, draw budget, calibration scenarios/seeds and scientific coverage/FPR/width acceptance criteria. No new numerical tolerances are supplied here. |
| P4-06 | Open | Specify invalid-task/artifact exclusions, outcome-blind adjudication and required sensitivity reporting; preserve original attempts. |
| P4-07 | Open | Specify common timeout budget, interpretable-artifact requirements and endpoint/denominator handling. Do not invent a Boolean result for an unscored contract error. |
| P4-08 | Open for prospective protocol | Specify any future infrastructure-only recovery policy, action authorization and preservation of originals. This audit authorizes no retry or run. |
| P4-09 | Open | Specify pre-invocation, worker, transport, contract and scorer failure categories, missingness and denominators; absent score is not zero. |
| P4-10 | Open | Name the primary comparison/endpoint and any hierarchy or multiplicity rule. Zero exclusion remains an implementation diagnostic, not an approved confirmatory test. |
| P4-11 | Open | Set meaningful success improvement and acceptable latency/call/cost/maintenance burdens. D-011 keeps quality and burden separate; no new weighted winner score. |
| P4-12 | Not satisfied — freeze deferred | Record accepted prerequisites, exact task/scorer/protocol/analysis hashes, named gate owner and explicit signoff before a pre-held-out freeze. JIT-off activation does not supply statistical acceptance. |

## Inactive sensitivity protocol, if later authorized

1. First resolve population/weights and actual repeat/block pairing (P4-01, P4-02, P4-04). Then name the candidate procedures and versions to compare under P4-03. No candidate set is approved by this outline.
2. Supply the outer-dataset count, bootstrap budget, independent seeds, confidence/tail rules and coverage/FPR/width acceptance criteria under P4-05 before execution. This outline supplies no new numeric thresholds, draw budget or permission to expand the run.
3. A separately authorized model-free comparison should preserve matched input matrices and endpoints for each approved procedure, with declared fixed-task or population truth and dependence structure. Use the same declared input realization when comparing procedures, preserve every scenario and failure, and distinguish true-zero FPR from nonzero-effect detection. Existing endpoints alone cannot supply candidate-method intervals.
4. Record outer MC uncertainty, width and degeneracy alongside coverage/FPR, and resolve failure, exclusion, multiplicity and practical-value rules before any confirmatory freeze. Candidate calibration cannot accept Phase 2/3 prerequisites or authorize held-out/model execution.

This protocol is **inactive** and has no launcher or new data. Current evidence supports deferring method freeze until these choices and needed evidence are explicit.

## Reproduction and preservation

Run from the workspace root. The output is exclusive-create, so choose a fresh filename for a replay:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 outputs/jit-off-activation-v1/phase4/verify_preserved.py --source-root work/phase4 --output work/phase4-activation-followup/recheck.json
PYTHONDONTWRITEBYTECODE=1 python3.11 outputs/jit-off-activation-v1/phase4/test_verify_preserved.py
PYTHONDONTWRITEBYTECODE=1 python3.12 outputs/jit-off-activation-v1/phase4/test_verify_preserved.py
```

Seven focused tests pass on Python 3.11 and 3.12 with sockets, connection creation and DNS denied before importing the verifier. They test actual preserved evidence, nondegenerate Wilson limits at 0/300 and 300/300, the score equation, altered evidence, invalid endpoints, input immutability, and absence of repository runtime/random imports. See [3.11 receipt](tests-python311.txt) and [3.12 receipt](tests-python312.txt). No source-suite test or simulation was rerun.

Original simulation SHA-256 remains `81a41a2f31cb28e0480416e63b8eba58d877f3bd866174cf5c794906ca273768`. Before/after hashes for the six direct numerical/method inputs are in the audit JSON; broader preserved artifact hashes are in [preservation receipt](preservation.json). No existing worktree, GitHub record or tracker was modified. Only the assigned output and scratch folders were written.
