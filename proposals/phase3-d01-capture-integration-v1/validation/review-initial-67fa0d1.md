# Independent exact-head review — 2026-10-19

Disposition: ACCEPT for inactive synthetic capture-integration preparation only. No new blocking finding identified in the eight-file branch delta. REJECT full semantic compatibility or Phase 3 acceptance: D01-TIE-ORDER-01 remains a demonstrated scientific false rejection. This review authorizes no activation, merge, model execution, live authentication, or phase transition.

Reviewed repository: `/Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/work/phase3-d01-capture-integration-v1`.

- Candidate HEAD: `67fa0d1cf6773d41ffa61fa401956ef73fa5906e`
- Candidate tree: `34caf1eb1cc33078ec01c29630cefbdd3d095bbe`
- Base: `42befe12de7d4c8cf5813a99cb32b7f3eb7c25dd`
- Base tree supplied by review contract: `6614373a03d95690be171bb42251fe23dfaa38d1`
- `git diff --name-status BASE HEAD` contains exactly eight additions, all under `proposals/phase3-d01-capture-integration-v1/`; no baseline path changed. `git status --short` was empty after validation. No implementation edits were made.

## Inspection and findings

Inspected PLAN, README, contract, adapter, runner, all new tests, configuration and Phase 4 refinement; also inspected unchanged upstream verifier and guarded validation entry point. Explicit host-selected token identity prevents copied/cross-session selection. The selected expected capture object and execution/call commitments prevent stale or substituted claim execution IDs from proving another call. Claim fields cannot supply the resolver or expected binding. Returned rows and caller input mutations cannot rewrite canonical snapshot/config/result strings; borrowed expected mappings are copies.

Actual SQLite execution is limited to the owned memory table with read authorization, approved aggregate functions, value/SQL/progress/row/serialized bounds and at most two attempted statements. Query exceptions and partial collections remain unsuccessful, receive a capture, and propagate; pre-execution denials receive zero-execute events. There is no automatic retry or favorable-call fallback. Source pins are checked for delivered explicit configuration before test SQLite creation, and upstream sources are pinned before loading. The adapter creates and verifies captures through the same pinned verifier module/class. Host-supplied source_commit remains an expressly documented provenance input; source hashes and exact reviewed HEAD are separate evidence. No claim of malicious-Python isolation is made.

The tie characterization is clearly labeled as incorrect upstream behavior. Both fresh matrices record scientific expected=proven and observed=contradicted/captured_result_mismatch; they count one supported-valid false rejection rather than treating the characterization's passing assertion as scientific success. Full semantic compatibility remains false. No upstream correction is requested within this scope.

Phase 4 recommendations remain proposals: fixed-task scope, prospective pairing, and family weighting all retain explicit owner decisions and dependencies. No missing outcome becomes zero, no retrospective pairing is asserted, and all twelve decisions stay unresolved. This review checked the refinement's claims and boundaries, not a new statistical calculation or independent re-audit of external source artifacts.

## Fresh guarded validation

Commands executed from reviewed repository, each with a fresh output and log:

```sh
/Users/ajaneeigharo/.local/share/uv/python/cpython-3.11.16-macos-aarch64-none/bin/python3.11 proposals/phase3-d01-capture-integration-v1/run_validation.py --configuration proposals/phase3-d01-capture-integration-v1/synthetic-config.json --output /Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/outputs/phase3-d01-capture-integration-v1-20261019/reviewer/py311-exact-head.json
/usr/local/bin/python3.12 proposals/phase3-d01-capture-integration-v1/run_validation.py --configuration proposals/phase3-d01-capture-integration-v1/synthetic-config.json --output /Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/outputs/phase3-d01-capture-integration-v1-20261019/reviewer/py312-exact-head.json
```

Both exited 0. Python versions: 3.11.16 and 3.12.6. Each ran 48 unit methods (20 new + 28 unchanged), with zero failures/errors, 60 upstream matrix cases with zero outcome mismatches, and 8 integration cases with zero unexpected mismatches. Both matrices have zero false acceptances; the integration matrix has exactly one known scientific false rejection. Each guard reports 178 memory SQLite connections and zero blocked side-effect attempts. These are synthetic engineering results only. No additional probes, broad test discovery, benchmark replay, runtime/model/service/resource operations, or live SQL were performed.

## SHA-256 receipts

| File | SHA-256 |
|---|---|
| PLAN.md | a66bf2e2d2c33e2bda0a3e3df56bc13f4e6cf8af6fd314cfc349b1b8eedecb8d |
| README.md | c1844fd80cb3636e2f5ca3e5212ea3192f912c693eca5d66ab853bee5c0d66d9 |
| capture_adapter.py | 6605861abcd6d14b82da3dcd205254745d4c9a7574f1a458efee6187b812665f |
| contract.json | f82f27b9c2529b8ebe7302b0dc29e8231b10a948f3bafb6445f83f8b6aee8961 |
| phase4-decision-update.md | b0a1092f043966ff39378fc51fafbbd2380ae76b88c43a522266e2f7e9628d60 |
| run_validation.py | 96c0c83c94ce985d319aaeb440411676029e90ea826efc1f4654fc2b1b089837 |
| synthetic-config.json | ce76cc16c23ac9568be9410f6338471015614cb082babb5c0e210a6454198ffd |
| test_capture.py | 2974a928d5b2ee7aff1ddaf88256244542477b6a7dc86a63ca3150268ab36d7c |
| py311-exact-head.json | c52f256ef2e32b8a7061469e87a72532c0c31f0c62b1e3e1d8104bb8d9485aa2 |
| py312-exact-head.json | 88b7dbe100efdb9b0a097a77dab474dd4cdb7910e1c7c9bf17157c4878d5490d |
| py311-exact-head.log | f91539155adaf7274693f8d15a0c9c1584330150529d84e3827670e7448ffcae |
| py312-exact-head.log | 8519e41a5bb4b3aa7859ac609ac854a406a15347fa3090d4ee890bd9077e9dd7 |

All verdicts remain live_qualified=false; candidate_active=false, phase3_accepted=false, full_semantic_compatibility=false, and new_treatment_a_attempts=0. Published-tree parity and any external reconciliation are outside this local review and are not claimed complete here.
