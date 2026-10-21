# phase3-d01-dependency-preflight-v1

Owner annotation on PR123 limitation authorized routine offline correction. No
activation, TreatmentA, integration, historical rescore or frozen-method change.

Root cause: run_validation.py executed the upstream runner and imported candidate
tests before inspecting its configuration. Its old manifest covered only five
candidate files and listed five upstream files without enforcing those hashes.
Upstream test_verifier.py and run_validation.py were missing from the pinned set.

Correction: parsing and all hash checks happen before dependency import. Six
candidate files and seven upstream files must match exact allowlists and SHA256
pins. Original five upstream contract commitments must agree with configuration.
The runner import itself is inert. The default immutable v3 configuration replaces
the previous unpinned no-configuration path; explicit v1 refuses without imports.
An existing output is still refused first. No evidence output is created on a
preflight failure. Result JSON records every verified dependency fingerprint.

Tests use private temporary copies, import interception and new synthetic inputs.
Every upstream file is individually changed and removed; incomplete, extra,
forged, malformed and traversing manifests, conflicting contract commitments and
stale configuration are rejected before dependency execution. Initial test fixture
path aliasing on macOS produced21errors; resolving the temporary root corrected
the fixture, then the unchanged baseline failed22assertions. Both RED records
remain preserved. No implementation was written before that corrected RED run.

The new configuration is separately immutable. Original contract, source verifier,
proof, v1configuration and all published validation evidence remain unchanged.
The bootstrap and approved configuration are the trust root, not a signed package
or defense against a malicious Python caller/concurrent host mutation. Direct
internal module execution is not an authorized validation entrypoint. All output
remains inactive, live_qualified=false and phase3_accepted=false.


Independent review of the first v2 candidate reproduced one P2: Python could
execute timestamp-valid preexisting bytecode even when every source hash matched.
Both interpreter reproductions are preserved. The successor retains the bytes
read during successful preflight, compiles only those bytes, and loads the finite
pinned dependency order into fresh modules. It neither reads nor deletes existing
bytecode caches and cannot inherit an arbitrary preexisting module implementation.
A new regression seeds eight harmless timestamp-valid raising caches and an
ambient module replacement; validation must load the verified source instead.
The first new regression had stale test-fixture fingerprints; after correcting
only that fixture, the v2 implementation failed with the expected bytecode marker.
The red record and corrected source implementation are retained. No benchmark was
executed. The configuration-v2 file remains immutable; v3 pins the corrected code.


Final independent review of6f134fc7c98704e97e12b754adba1d2cb23a322d accepts
inactive preparation, with the initial P2 resolved and no actionable findings.
Both Python3.11.16/3.12.6 pass53methods,60+16controls,24independent rejection
controls and4CLI refusal checks. All8executed modules withstand stalebytecode,
ambientmodule poisoning and on-disk mutation after verification in a standalone
zero-SQL loading control. Broader repository tests:297pass per interpreter.
Original proof/verifier/contract, v1/v2configurations and all preexisting evidence
remain unchanged. Every verdict stays live_qualified=false and phase3_accepted=false.

Full reviews, failed controls, source-history bundle and raw successor evidence
are preserved locally with the executor report. Automatic approval review
rejected exporting the raw archive to GitHub, including after a content audit;
it is withheld, not uploaded through an alternative route. Publication is limited
to this brief and the scoped code/configuration changes. Previous published
validation artifacts remain unchanged as historical records.
