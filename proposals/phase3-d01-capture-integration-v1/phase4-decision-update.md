# Phase 4 decision refinement — inactive capture-integration proposal

Prepared October 19, 2026 for owner review. **P4-01, P4-04 and P4-02 remain open; all twelve Phase 4 decisions remain unresolved. No values or policies are adopted.** This note belongs to the inactive `phase3-d01-capture-integration-v1` package. It supplies no activation, evaluator acceptance, phase acceptance, analysis freeze or run authorization. PR #121's source head `42befe12de7d4c8cf5813a99cb32b7f3eb7c25dd` and its original evidence are preserved.

## Evidence and exact source pins

Paths below are relative to the outer preparation workspace, not this proposal directory. SHA-256 identifies the exact local bytes read for this note.

| Source | Pin / SHA-256 | Scope |
|---|---|---|
| `work/phase4-metadata-proposal-delivery/owner-decisions.json` | `9197f3af5d85dccc868dff39db25a594f66966c111db62fa09ea44c96ef78669` | All twelve unresolved owner decisions; copied without adopting or editing them |
| `work/phase4/docs/phase4-analysis-plan-proposal-2026-10-17.md` | `c4a77bb5bca481295bdcc82d0085c110b516e244a7d5f96ca735c674c3976d0b` | Roadmap estimand, planned eight families/three tasks each per bank, three matched repeats, alternatives and unresolved weights |
| `work/phase4/docs/phase4-evidence-validation-2026-10-17.md` | `3174fcf87b238b4386b343183afd5ab490f146764834f1d274c53ba14ada43b7` | Independent arithmetic check and documented method/code mismatch; actual repeat pairing unverified |
| `outputs/phase4-wolfram-verification-20261018/REVIEW.md` | `99ef5014e43fae30a60b0ad120fbc52476ee646c9f035bec9cfffc3055a55bce` | Preserved independent arithmetic audit, limitations and first-decision ordering |
| `outputs/phase4-wolfram-verification-20261018/source-pins-before.json` | `98a5b170f62869abcf5b3c1b2838233b87657f2e21c2d569e3baaf2810b1c246` | Audit source commit `403eda9b0ea47da9d6690e8750517b883ddaf4a9` and original source fingerprints |

The two Phase 4 documents match the audit's recorded fingerprints. Pinned public counterparts are the [analysis proposal](https://github.com/AjaneeI/agentic-analytics-lab/blob/403eda9b0ea47da9d6690e8750517b883ddaf4a9/docs/phase4-analysis-plan-proposal-2026-10-17.md) and [method/code ledger](https://github.com/AjaneeI/agentic-analytics-lab/blob/403eda9b0ea47da9d6690e8750517b883ddaf4a9/docs/phase4-evidence-validation-2026-10-17.md). The preserved original simulation SHA-256 is `81a41a2f31cb28e0480416e63b8eba58d877f3bd866174cf5c794906ca273768`; the unchanged inference source SHA-256 is `ab07c438859bfa7d272f7a24425663477eb3a611aa3832c7568793ba7702a29e`.

Only existing arithmetic is reused: Wolfram agreed on 3,000 stored synthetic records and 290 scalar summaries, with maximum absolute summary difference `2.220446049250313e-16`. Recorded coverage was 99.3% for independent data, 79.0% for family shocks and 32.3% for run shocks. Perfect-pairing synthetic data had zero point effect in all 300 datasets but mean interval width 26.3081 percentage points under independent arm-repeat resampling. These are dependence stress-test diagnostics, not measurements of actual benchmark pairing, dependence or generalization. Original bootstrap draws were not regenerated. The supplemental Wolfram pairing/weight/quantile identity request failed with a connection error; no successful result is inferred.

## P4-01 — target population and uncertainty

**Consequence.** The task remains the primary experimental unit. Conditioning on a declared task set targets its weighted mean candidate-minus-baseline success-probability difference under the declared repeat/execution conditions. Sampling tasks or families instead introduces a population claim and requires an explicit sampling frame and defensible sampling/dependence assumptions. Resampling task identities does not by itself justify that claim.

**Options for owner decision:**

1. Fixed declared task set; uncertainty concerns repeated execution on those tasks, including declared shared execution blocks. Report the scope as conditional on that set and protocol.
2. Sampled tasks within declared families/templates, or sampled families; define the population, task/family selection process and independent sampling units before choosing an estimator or interval.

**Supported recommendation, not adoption:** use the fixed-task scope for the next proposed analysis. The preserved preparation supplies a finite planned bank and no demonstrated probability sampling design for an external task/family population. This narrower scope avoids an unsupported generalization claim; it does not establish that three repeats are sufficient or endorse the existing interval. No bank completeness or actual repeat execution is verified here.

**Owner decision still required:** approve the population, parameter, execution conditions and uncertainty target explicitly, or specify the population/sampling design supporting option 2. Final weights and missingness rules remain prerequisites to a fully defined parameter.

## P4-04 — prospective repeat pairing and shared blocks

**Consequence.** Equal counts and matching task order establish neither paired repeats nor independent tasks/repeats. The existing helper pairs task identity but draws each arm's repeats independently. Preserved family/run-shock diagnostics show why dependence assumptions matter; they do not estimate actual dependence or select a replacement procedure.

**Options for owner decision:**

1. Prospectively define paired candidate/baseline execution blocks: matched task/repeat IDs; seeds where applicable; treatment versions; execution order; and any family, session or run block shared across tasks. Identify which blocks can reasonably be treated as independent.
2. Define an explicitly unpaired execution protocol and its independence assumptions. Do not reconstruct pairing from equal counts or fabricate missing seed/block metadata for historical attempts.

**Supported recommendation, not adoption:** specify the prospective paired-block design before any future authorized exposure, consistent with the roadmap's matched-repeat intent. Capture enough host-owned provenance to inspect task/repeat alignment and shared blocks, including unknown or unavailable observations. Owner review must settle ordering/blocking and whether seed matching is meaningful for each treatment. A shared seed alone cannot prove equal exposure, pairing quality or independence.

This is a design recommendation, **not verified actual pairing**. The inactive capture-integration package may support provenance inspection; metadata consistency cannot establish capture authenticity, valid scoring, independent units, statistical pairing or calibration. No capture-field presence or synthetic verifier result can substitute for actual execution records and an approved protocol.

**Owner decision still required:** approve matched identities, applicable seed rules, ordering, shared-block structure and independent sampling units. Then verify actual records against that protocol before selecting an interval. Missing or contradictory provenance remains unresolved evidence, not permission to infer independence or relabel an attempt.

## P4-02 — weights and incomplete families/tasks

**Consequence.** Equal-task weighting targets the observed task mix; equal-family weighting targets a declared family mix. They coincide for the fully balanced planned bank but can differ after imbalance or exclusions. Neither arithmetic agreement nor a metadata validator approves either target.

**Options for owner decision:**

1. Equal family weights, then equal task weights within each declared family: the existing proposal is `1/8` per family and `1/(8*n_family)` per task. For the complete planned bank of three tasks in each of eight families, the proposal records `1/24` per task.
2. Equal task weights across the declared target bank; family representation then determines each family's total weight.
3. Other scientifically justified task/family weights, specified prospectively with their target and rationale.

**Supported recommendation, not adoption:** retain option 1 as the proposal for owner review, conditional on approval of an eight-family target and explicit task membership. It preserves a stated family mix when valid planned family sizes differ. On the fully balanced planned bank it adds no change to the recorded equal-task arithmetic. It is not an operational fallback for missing tasks or families.

**Absent-family and invalid-task treatment remain unresolved.** Owner decisions must specify exclusions/adjudication, denominators and what happens when the declared family/task target is incomplete. Choices such as withholding an aggregate, retaining a planned denominator under an approved endpoint/missingness rule, or prospectively redefining the target require explicit approval. This note chooses none. There is **no silent renormalization**, dropping, replacement, or conversion of an absent/unscored result to zero. An observed-family-only average must not silently replace the declared eight-family estimand.

**Owner decision still required:** approve the target family/task list and weights together with absent-family/invalid-task rules. Resolve those rules before the estimator is selected or weights can be applied.

## Dependencies and unchanged gates

Review in order P4-01 → P4-04 → P4-02, revisiting any earlier decision if a later dependency changes its meaning. This prioritizes decisions; it does not close them.

| Remaining decision | Required dependency |
|---|---|
| P4-03 — interval | Resolve task-delta-only documentation versus task plus independent-arm-repeat code; choose only after population, actual pairing/blocks and weights are approved. Preserve historical results. |
| P4-05 — calibration | Approve confidence/tails, draw budget, scenarios/seeds and scientific coverage/FPR/width criteria, including prospective numerical representation, quantile interpolation and zero-boundary handling. Existing arithmetic tolerance is not an acceptance criterion. |
| P4-06 — exclusions | Approve outcome-blind adjudication, invalid-task/artifact rules and sensitivity reporting; required for target membership and weights. |
| P4-07 — timeouts | Approve common budget, interpretable-artifact requirements and endpoint/denominator handling; no invented Boolean outcome for an unscored contract error. |
| P4-08 — recovery | Any prospective infrastructure-only recovery needs separately approved authorization and preserved originals; no consumed attempt is retried by this proposal. |
| P4-09 — failures/missingness | Approve failure categories, missingness and denominators; absence of a score is not zero and observation availability does not decide endpoint availability. |
| P4-10 — multiplicity | Name the primary comparison/endpoint and hierarchy or control rule before confirmatory interpretation. |
| P4-11 — practical thresholds | Owner must set meaningful success improvement and acceptable operational burdens; retain D-011's separate quality/burden reporting. |
| P4-12 — freeze | Accepted prerequisite evidence, exact task/scorer/protocol/analysis hashes, named gate owner and explicit signoff remain necessary before held-out access. |

All P4-01–P4-12 remain open/unresolved; P4-12 is not satisfied. Phase 2/3/4/5 dispositions and consumed authorizations are unchanged. No owner decision, new calculation, simulation, SQL, model call, service/resource operation, held-out access or frozen-method change is supplied by this refinement. The next step is an explicit owner decision record, followed only by separately authorized work within its scope.
