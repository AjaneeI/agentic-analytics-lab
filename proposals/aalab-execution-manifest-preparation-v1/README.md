# P1 execution-manifest preparation v1 — inactive

Authority: direct owner approval October24,2026 in sole executor session01a14c56,
“I approve P1 execution-manifest preparation within C1’s exact bounds. Proceed
autonomously through offline validation, independent review and a draft PR.
Keep all scientific and live-execution restrictions.” Pickup95#6388953655.
C1 is the separately selectable preparation in issue95#6388701438, complete
20176-byte source SHA25617d79f9d986114a39edf921ada2b467ac8e356691873d52af1e8cd41258e6b37.
Original S1 specification selection and all its deferrals remain unchanged.

## Deliverable and implementation sequence

New files only in this directory: manifest.py (pure contract/validator),
test_manifest.py (16 deterministic fixtures), run_validation.py (pinned entrypoint),
this README (plan/assumption ledger), contract.json and synthetic-config.json.
No existing file, including STATUS.md, is edited: C1's explicit path/preservation
restriction takes precedence over the general STATUS-update convention. Current
technical state is recorded here and in existing issue95/Notion/Asana.

1. Preserve exact C1/base and original source/evidence; demonstrate all16 RED controls.
2. Implement only declaration consistency; validate with the bounded synthetic suite.
3. Pin source/config/contract, preflight before candidate imports, compile retained
   bytes rather than cached modules/bytecode, validate Python3.11/3.12.
4. Obtain one independent review of the exact committed candidate with up to8
   additional named cases (24 total), correct in-scope findings preserving failures,
   publish one inactive stacked draft and reconcile verified records.

Base PR125 head4c985a778976755cb8e426d5b34ced7a6b48b976, full tree
6734d3e4d816e22bb0c621d36e0b73a8b07b35d1, equals local473381149ce206e6cf55342edda25a8a38dd9a0e.
Native app worktree creation is unavailable for the projectless executor; the new
linked Git worktree/branch isolates this preparation from the preserved base.
Local implementation commits/config pins and published commit/tree parity are
recorded separately; a local source object is not a GitHub alias.

## Pure interface and host boundary

`validate(manifest: bytes, *, expected: bytes) -> dict` accepts strict UTF-8 JSON.
Host-owned expected bytes must be provided independently, never reconstructed from
submitted cells or retrieved/agent-controlled prose. There is no file, SQL, model,
network, scheduler, seed setting or timestamp acquisition in the validator.
Both sides are validated structurally; invalid expectations cannot legitimize an
invalid submission. JSON duplicate keys, nonfinite constants, invalid UTF-8 and
unsupported fields are rejected. No coercion, timestamp repair, sorting of input
bytes, inference of actual execution or unknown-to-independent conversion occurs.

This interface cannot authenticate host ownership, synthetic origin, signatures,
actual chronology or execution. A malicious caller controlling both inputs can
supply consistent fabricated declarations. Input hashes preserve bytes, not truth.
The bootstrap and approved configuration are trusted roots; Python audit/import
hooks are process safeguards, not an OS sandbox or malicious-host defense.

## Exact declaration contract

Root keys are exactly version, synthetic=true, independence and cells. Independence
is only `unknown` or `dependent`; an `independent` assertion is rejected. Empty
manifests are insufficient. Each input is at most65536UTF-8bytes, at most32cells,
8task IDs matching P1-SYN-[A-Z0-9-]+, arms baseline/candidate and repeat labels1/2.
These are fixture bounds, never benchmark membership, trial count or power claims.

Every cell has exactly the fields in contract.json:

| Fields | Rule |
|---|---|
| task_id, task_version, family | Synthetic task ID; bounded ASCII version; one family A-H; task version/family consistent across all its cells. No requirement that this prototype's fixtures cover all scientific families. |
| arm, repeat_id, block_id | One cell per task/version/arm/repeat, even if a different block is supplied; every task/version/repeat/block has exactly both arms. Boolean counts are rejected. |
| execution_order | AB means baseline before candidate; BA reverses it. Both cells must declare the same order. |
| start_utc, end_utc | Strict real UTC ISO strings YYYY-MM-DDTHH:MM:SS[.ffffff]Z; start strictly before end; first arm ends no later than second starts. Exact adjacent boundaries allowed. These are authored synthetic times, never measured clocks. |
| run_id, session_id, shared_block_id | Bounded explicit ASCII IDs. A declared block has one run/session/shared-block tuple; shared-block IDs have one run/session scope. Different tasks may overlap and share a dependence block. No inference of independent units. |
| seed_control | Exactly state/seed/reason. controlled requires integer0..2^63-1 (not Boolean), reason=null. unavailable requires seed=null and a nonblank reason of at most256characters. This records a claim of controllability; it neither sets seeds nor proves reproducibility. |
| treatment_sha256, configuration_sha256 | Lowercase64hex; one consistent pair per arm. Every field, including these fingerprints and synthetic timestamps, must equal the independently supplied expected identity's declaration. |

Row order need not match input order: explicit IDs and chronology carry meaning.
Original input bytes/hashes are retained. Comparison ignores no extra cell/field
and selects no favorable row. Expectation cannot be supplied inside a submission.
The source/file contract hash is recorded separately from input commitments.

## Controls and bounded validation

Sixteen authored cases: four positives AB/BA/shared dependence/unavailable seed,
and twelve negatives missing/extra identity, contradictory order, reversed time,
sequential overlap, run/session mismatch, family drift, shared-block drift,
missing controlled seed, inconsistent unavailable seed, treatment/configuration
drift and unsupported independence. Expectations/reasons are literal, independent
of validator helpers. The invalid-overlap case makes both host and submission
invalid, demonstrating that matching bad inputs is not a pass. Up to8 additional
independent cases fit the24-case total; no case uses benchmark tasks or outcomes.
Initial16 failures on each Python version are preserved outside the checkout.

Every validation invocation must use the approved external test watchdog retained
with the executor evidence:29-second kill threshold within a30-second bound,
65536bytes combined stdout/stderr, bounded cleanup, no automatic expansion.
Each invocation refuses existing evidence paths. The child has SQL (including
SQLite), network, subprocess/model imports and stochastic sources denied before
candidate import. Only the outer test-process launch is allowed. Limit failures
preserve the captured prefix/outcome and stop that invocation. There is no runtime
feasibility benchmark or throughput/resource measurement.

The source entrypoint is:

    python -I -B proposals/aalab-execution-manifest-preparation-v1/run_validation.py --output /absolute/NEW.json

This command is **not itself a wall-time limiter**; run it through the approved
watchdog/test-process supervisor with C1's exact30s/64KiB limits. Before candidate
import it verifies all five source/doc/contract hashes and the inactive approved
configuration, retains verified bytes and loads fresh modules. It cross-checks
the source contract against retained contract.json. Cached modules and .pyc files
are not used. Output must be new/outside the checkout; receipt maximum65536bytes.
No active worker, evaluator or runtime imports this entrypoint.

Completed PR125 regressions are reused. No repository-wide rerun is justified by
six isolated, inactive additions; it would exceed C1's no-SQL validation boundary.
Independent review and delivery are evidenced separately, not presumed from this
plan. No hosted CI, live-model compliance or execution authentication is claimed.

## Assumption ledger and unresolved gates

Every verdict is active=false, live_qualified=false,
independence_established=false, scientific_ready=false, new_attempts=0, including
structurally consistent fixtures. Unknown dependence stays unknown; explicit
shared dependence is a declaration. A pass proves only consistency with supplied
host expectations under this finite contract. It grants no scientific readiness.

Unresolved: authentic live provenance; empirical independent/exchangeable unit;
period/carryover/shared-shock magnitude; repeat sufficiency; final roster and
reference acceptance; runtime/model/budget comparability and feasibility;
utility thresholds; interval/numerical/calibration acceptance; full evaluator
acceptance and scientific freeze. The future host will need an authorized design
and authentic receipts; this prototype does not supply them. S1's missing-score
and primary-withholding rules are separate, unchanged; no outcomes or scores are
consumed here. No historical rescoring, estimate, interval or resampling array.

Phase2 remains DEFER/zero attempts; Phase3 unaccepted, Phase4 unfrozen, Phase5
unentered. No new SQL including SQLite, failed query replay, model/network/service/
resource operation, scheduler, random draw, held-out access, active scorer/runtime/
configuration/bank change, paid provider, automatic review, merge or deployment.
Preparation completion does not automatically start a subsequent stage.
