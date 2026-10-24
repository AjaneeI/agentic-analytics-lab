# Prospective endpoint and execution metadata — inactive v2 draft

Preparation approval: issue95 comment6388458353; start receipt6388473610. This proposes a scientific protocol; it adopts no method, activates no bank and schedules nothing. Phase2 remains unqualified, Phase3 unaccepted, Phase4 unfrozen, Phase5 unentered. New attempts0. Ajanee retains final scientific approval. Source fingerprints and every decision disposition are in `decision-dispositions.json`.

## Target, membership and endpoint

Recommend conditioning on a prospectively declared fixed task set under a declared execution protocol. No external-task or family-population generalization is supported by a probability sampling design. PR104 commit15256f598e70bb09032120c0f0c0cf9e289a25fe supplies exactly seven compatibility tasks: SB-A01, SB-C01, SB-C02, SB-D01, SB-E01, SB-G01, SB-H01. It omits B/F and cannot instantiate an eight-family estimate. The 24-case three-per-family proposal and its17 additions remain inactive; scientific membership activation is deferred. Newly named SYN-V2 controls are not benchmark tasks.

Propose one primary endpoint: routed-system minus explicitly configured strong-single baseline verified binary task success. For an approved complete eight-family roster, the symbolic target is sum over families of1/8 times mean within-family task effects; task weight1/(8*n_family). It equals1/24 only with three tasks per family. The supplied validator never computes success means, quality estimates, intervals or historical aggregates. It cannot verify host authority, actual synthetic origin, actual approval or runtime pairing; its flags are metadata declarations only.

## Host-owned target and outcome schema

Before any future exposure, an immutable host-owned manifest declares task_id, task_version, family A-H, arm baseline/candidate, positive integer repeat_id and block_id. Host-derived `n_family` counts unique tasks, never repeats; synthetic=True and metadata_approved=True qualify only declared synthetic examples for this inactive validator. Booleans are forbidden as counts. The expected target is supplied independently of observed rows, never reconstructed from available outcomes. Duplicate or undeclared fields/identities, unknown arm/family, task family/version drift, unequal paired block IDs, missing arms and missing required families invalidate eligibility. Unknown/extra observed identities withhold even when every expected outcome also exists.

Observations carry exact identity, declared status, `scored` Boolean and `success`. Status categories are not_started, started_timeout, transport_error, worker_error, contract_error, scorer_error, scored_success, scored_failure. Scored success/failure require the matching Boolean; unscored outcomes require success=null. A timeout additionally retains original elapsed_seconds, stage and artifact_available. A timeout with an available valid scorer-interpretable response may retain its actual Boolean (scored=true); a missing/uninterpretable response remains null. This does not infer a score from artifact availability. Future provenance must bind the scorer receipt separately. Invalid artifacts and missing scores are not automatically task exclusions.

All required task×arm×repeat outcomes must be valid and scored before primary eligibility; missing, unscored, invalid, duplicate, extra or unmatched outcomes withhold the target aggregate. Counts by category and availability are separate descriptive diagnostics. Never impute zero, delete post-outcome tasks, substitute/retry, compute an observed-only aggregate or silently renormalize. Every return is inactive=true, live_qualified=false, aggregate=null, new_attempts=0. `eligible_for_primary=true` means only complete metadata under this draft; no scientific estimate is produced.

## Prospective paired execution design — declaration only

Retain three matched repeats as a planning value, with sufficiency unresolved. Propose immutable pairing keys task/version/repeat/block; store execution_order AB or BA, arm start/end UTC, run_id, session_id, family_block_id, shared_block_id and treatment/configuration hashes in a separate execution manifest. Use a predeclared deterministic counterbalance (repeat1 AB, repeat2 BA, repeat3 AB for half the declared task blocks; reverse for the other half). Which tasks receive each sequence is fixed before outcomes; no scheduler exists here. Counterbalancing does not remove period/carryover effects or create randomization.

For SYN-V2-A at repeat1, baseline and candidate share block paired-1 and declared order AB; repeat2 shares paired-2/order BA. An observed candidate with block other-1 is unmatched and withholds. Seeds must carry seed_control=controlled with the exact integer only when the runtime actually controls it, otherwise seed_control=unavailable, seed=null and reason; equal seeds are not proof of independent or coupled stochastic behavior. Record shared run/session/family shocks rather than assuming each task/repeat independent. The metadata function checks the narrow identity/score contract only; execution order, seed and shared-shock provenance require later manifest verification and independent-unit signoff.

## Adjudication, missingness and recovery

Proposed prospective invalid-task reasons: ambiguous_authority, contradictory_authority, invalid_reference, unsupported_required_evidence, duplicate_identity, version_mismatch. Work lead supplies source passage/version, evidence and recommendation without outcome-driven deletion; Ajanee alone approves a scientific roster amendment. Preserve every artifact. An amendment creates a separately versioned target and requires renewed aggregate disposition; it does not repair the original target or trigger another audit here.

No automatic recovery, retries, replacement or warmups. Restoring infrastructure is distinct from creating another attempt; prior permissions are consumed. Runtime readiness, optional observation and a new TreatmentA have separate later gates. No current draft revives any gate.

## Endpoint hierarchy, practical bounds and signoff

Family, route, failure-availability and latency/call/token/cost/maintenance breakdowns remain descriptive. A future confirmatory hierarchy or multiplicity rule remains unapproved; positive bootstrap fraction is not a p-value. Quality and burden stay separate with Pareto reporting, no weighted winner score. Concrete options and evidence gaps are in `method-resolution.md`.

Before freeze bind exact target/scorer/adapter/transport/model digest/prompt/security/protocol/analysis hashes, actual pairing/dependence evidence, runtime-budget comparability, approved missingness/adjudication rules, independently reviewed numerical/calibration results, accepted Phase2/3 gates and Ajanee's signoff. Every acceptance field in the machine-readable decision file remains false. No held-out access or Phase5 entry follows from synthetic controls.

## All twelve Phase4 dispositions — proposed direction versus deferral

| ID | Inactive draft direction | Explicit deferral |
|---|---|---|
| P4-01 target_population | Fixed declared tasks conditional on approved execution protocol; no external task/family population claim. Seven-task PR104 roster is compatibility only. | Scientific roster activation and population signoff. |
| P4-02 weights | Symbolic equal-family/equal-task 1/(8*n_family) only for complete approved synthetic A-H metadata; 1/24 only for three tasks per family. | Actual application until membership, missingness, timeout and failures accepted. |
| P4-03 interval | Compare fixed-task paired whole-block direction versus task-population task-delta and paired hierarchy candidates; preserve existing code/document mismatch as evidence. | Interval selection, inference-code change and code/document freeze. |
| P4-04 pairing_blocks | Prospective task-by-repeat paired blocks; three matched repeats planning only; predeclare AB/BA order and shared run/session/family IDs; seeds only if actually controllable. | Independent-unit and repeat-sufficiency signoff; actual scheduling. |
| P4-05 calibration_numerics | Proposed nominal95% two-sided percentile comparison, ordered synthetic scenarios and seeds, bounded screening/final options, outer/inner MC uncertainty and explicit unknown acceptance values. No draws. | Confidence/tails/draw count/calibration pass criteria/MC precision/quantile/zero-boundary freeze and calibration execution. |
| P4-06 exclusions_membership | No post-outcome deletion/substitution/renormalization; prospective authority/reference/evidence/duplicate/version reasons; lead recommends and Ajanee approves a versioned scientific roster amendment. | Scientific roster amendment/activation or new audit. |
| P4-07 timeout | Retain timeout timing/stage/artifact; actual scorer-interpretable Boolean preserved, missing/uninterpretable success null; propose lineage-preserving common model options for later feasibility review. | Numerical common timeout/runtime budget adoption or configuration change. |
| P4-08 recovery | No automatic retry/replacement; infrastructure recovery distinct from a new attempt; every failure preserved. | Prospective recovery exception or resurrection of consumed permissions. |
| P4-09 failures_denominators | Eight declared statuses; unscored null; missing/invalid/duplicate/unknown/unmatched required identities withhold primary; no observed-only replacement or zero imputation. | Live endpoint/denominator adoption or historical rescoring. |
| P4-10 endpoint_multiplicity | One proposed routed minus explicitly configured strong-single verified binary task-success primary; family/route/burden breakdowns descriptive. | Confirmatory hierarchy/testing/multiplicity freeze until method/protocol acceptance. |
| P4-11 practical_thresholds | Recommend reliability-first direction with separate quality and burden/Pareto reporting; concrete noninferiority/descriptive alternatives and gaps. | All numerical quality gain/loss and latency/calls/tokens/cost/maintenance bounds; no weighted winner. |
| P4-12 freeze | Proposed signoff binds exact target/scorer/adapter/model/prompt/protocol/analysis hashes, upstream gates and Ajanee owner decision. | Final freeze, Phase4 acceptance, held-out access and Phase5 entry. |
