# Inactive D01 capture-integration preparation

This is a separately versioned **synthetic compatibility prototype** stacked on PR121 at42befe12de7d4c8cf5813a99cb32b7f3eb7c25dd. It adds no active integration, benchmark/scorer/runtime change, model/tool/prompt field, provider API or live capture authentication. PR121's seven source files and all original evidence remain unchanged. Every verdict has live_qualified=false.

## Interfaces and trust

`SyntheticCaptureSession(rows, config)` owns a frozen complete new synthetic snapshot and configuration. `query(sql) -> list[dict]` matches the existing callback signature and returns only actual result rows. It does not import or invoke BoundedLocalExecutor; signature compatibility is not active-worker or ClickHouse qualification.

`calls`, `events`, `resolve(execution_id)`, `verification_context(call)` and `verify(claim, *, call=token)` are host-only interfaces. The host explicitly chooses an opaque token by identity from this session. Missing, copied, serialized or cross-session tokens cannot select evidence. No latest-successful/favorable fallback exists. The original `verify(claim, *, resolver, expected)` remains unchanged and is invoked with the registry's own context. The claim cannot register captures or replace host commitments. Borrowed expected dictionaries are copies; capture and event objects are frozen.

Only claim is untrusted. Python private attributes, object identity and source hashes are not process isolation, cryptographic attestation or protection from a malicious host/Python caller. This host must never be given to an agent. Host configuration source_commit is a supplied provenance input, not independently authenticated by the library. Delivered configuration pins the exact implementation commit/source hashes; validation receipts separately record actual reviewed/published heads. Unit fixtures identify their upstream PR121 pin explicitly.

## Bounded execution and evidence

The session creates one private memory-only table in an attached memory-only agentic_analytics namespace, permitting both qualified and unqualified source names. Fixture setup writes only new ephemeral synthetic rows. After setup, query_only and an authorizer deny mutation, attachment, unrelated sources and functions outside sum/count/avg. These are offline adapter restrictions, not changes to frozen SQL guards or a ClickHouse security qualification.

At most two callback calls execute SQL, once each, without retries. A100000-opcode progress handler bounds each statement; local SQL length8192, SQLite value2MiB, snapshot/config1MiB, captured result1000rows and combined serialized query/result/snapshot/config2MiB bounds apply. Results are fetched incrementally; overflow preserves a bounded prefix and complete=false, then raises. An oversized expression is stopped by SQLite before Python captures it. This does not increase or redefine experimental budgets and is not a guaranteed process RSS/wall-time ceiling.

Every executed callback retains exact SQL, frozen actual rows, complete original synthetic snapshot, configuration, source/task/metric/contract and execution/call commitments in the host registry. Failure exceptions are propagated and remain unsuccessful/incomplete; no replacement call is issued. Pre-execution input/budget/closed-session denials retain zero-execute failure events without inventing a capture. Timing is passive elapsed time only, not resource profiling or causal performance evidence.

## Validation and the known upstream blocker

Independent hand counts for the new fixture are Dune3/5=60%, Elm1/4=25%, Fern0/2=0%, with two completed Dune rows excluded. No frozen task/reference or generator is loaded. Tests exercise real in-memory SQLite and the pinned unchanged verifier. The inspected runner also executes the existing28D01 synthetic unit methods and60named regressions, under their unchanged socket/process/file-database/active-runtime import guard. No broad repository discovery or hosted CI is claimed.

**D01-TIE-ORDER-01 remains unresolved.** In a new two-team100%tie, SQLite can legitimately return Elm for ORDER BY blocked_pct DESC LIMIT1, while the upstream pure interpreter expects Dune. The verifier returns contradicted/captured_result_mismatch. The original failing test output is preserved. Deterministic secondary-sort and complete-result tie cases are separate valid controls; they do not fix or excuse the unspecified-order case. The integration matrix records scientific expected=proven versus observed=contradicted and counts this as a supported-valid false rejection. A passing engineering test suite includes a clearly labeled characterization of that incorrect behavior, not a scientific acceptance test. Full semantic compatibility and Phase3 acceptance remain false.

Run only the inspected entry point with an unused output path:

```sh
python3.11 proposals/phase3-d01-capture-integration-v1/run_validation.py --configuration proposals/phase3-d01-capture-integration-v1/synthetic-config-v2.json --output /absolute/fresh-evidence.json
```

Repeat with Python3.12 and a different unused output. JSON reports separate engineering checks from scientific mismatches. Existing and new RED/GREEN logs are preserved; output files refuse overwrite. Side-effect guards are test controls, not an operating-system security boundary.

## Delivery and gates

The source-pinned configuration, contract, author/reviewer results, preservation manifest and source hashes form an inactive draft-review package. A fresh independent exact-head review and published-tree/content parity are required before delivery is called complete. Review does not authorize activation, merge, a frozen-method change or a live experiment.

The Phase4 update reuses existing audits and sharpens P4-01population, P4-04pairing and P4-02weights recommendations. All twelve decisions remain open; no new simulation or method is adopted. Existing Phase2 diagnostics/protocols are reused. Phase2 stays unqualified, Phase3 unaccepted, Phase4 unfrozen, Phase5 unentered. No historical SQL replay/rescore, newTreatmentA, model/provider/service/resource operation, heldout access, paid fallback or automatic Codex review.

## Reviewed correction history

Initial head67fa0d1/config-v1 and its review remain preserved. A separate narrow follow-up found two failure-evidence gaps: lone-surrogate SQL left a partial registry entry/KeyError, and execute cancellation omitted error metadata. New RED regressions reproduced both. The corrected adapter rejects invalid UTF8 before token/SQL execution, retaining lossless bounded JSON code-point evidence without pretending to hash invalid UTF8. It records BaseException/cancellation type/message and propagates the original exception. This covers synchronous injected cancellation, not process kill/crash consistency. No normalization or retry is added.

Original synthetic-config.json is an immutable historical configuration and must now fail source-fingerprint preflight against corrected code. synthetic-config-v2.json is the corrected source-pinned configuration. Both histories and their hashes are retained. The upstream tie-order scientific limitation remains unchanged.
