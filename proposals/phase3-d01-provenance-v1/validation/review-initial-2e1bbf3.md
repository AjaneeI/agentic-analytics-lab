# Independent exact-head review — revise

Base `43cf76b0acf64aba4f19eb510af12189b7a4ad04`, tree `39c633e7c59788b7611827bcfa61d7f57d52e419`. Candidate `2e1bbf3b11e1356a90e7b053ef722519b300ba72`, tree `8eef038fb23baed803a8816fa0d6774f39755dc6`, branch `codex/phase3-d01-provenance-v1`. Clean checkout rechecked.

Both required interpreter commands passed: Python3.11.16 and3.12.6 each ran22 unit tests plus44 named matrix cases; no guard denials. Commands used the supplied absolute Python paths and `proposals/phase3-d01-provenance-v1/run_validation.py --output <reviewer/validation-py311-initial.json or validation-py312-initial.json>`. Output paths were fresh and author receipts were untouched.

Reviewer-only `adversarial_initial.py` and `alias_controls.py` each ran under both interpreters. Per interpreter20 cases exposed8 malformed-input crashes,2 supported-valid false rejections and1 unsupported-valid misclassification;9 other outcomes matched expectations. No false acceptance observed. These scripts import the inspected run_validation audit guard before fixture imports;20 in-memory SQLite connections, zero denied side effects per interpreter. An initial reviewer script output-path concatenation typo failed after executing probes; it was corrected before creating receipts, without candidate edits.

## R1 (P2): Large JSON integer claims/results crash instead of producing a verdict

Location: `proposals/phase3-d01-provenance-v1/verifier.py:82,147`.

Reproduction: `check(FixtureHost(), claim(rate=10**400)); captured_rows=[{"team":"Amber","blocked_pct":10**400}]`.

Actual: OverflowError: int too large to convert to float. Expected: Explicit invalid_claim/captured_result_mismatch outcome; no exception.

## R2 (P2): Population fallback loses renamed status lineage and condemns valid unsupported SQL

Location: `proposals/phase3-d01-provenance-v1/sql_proof.py:318-323`.

Reproduction: `WITH renamed AS (SELECT team, blocked, status AS state FROM delivery_work_items) SELECT team, 100.0*SUM(blocked)/COUNT(*) AS rate FROM renamed WHERE NOT NOT(state != 'done') GROUP BY team ORDER BY rate DESC LIMIT 1`.

Actual: contradicted/wrong_population. Expected: insufficient/unsupported_sql; SQLite computes Amber75 and unrenamed NOT NOT already has an insufficient control.

## R3 (P2): Incomplete HostCapture validation crashes hashing of malformed byte fields

Location: `proposals/phase3-d01-provenance-v1/verifier.py:94-102`.

Reproduction: `replace(host.record,result_json=None), expected=dict(host.expected,capture_ref=replaced_record); likewise snapshot_json/config_json None and non-string types`.

Actual: AttributeError in digest before JSON/type checks. Expected: Explicit invalid_capture or binding_mismatch outcome; no exception.

## R4 (P2): Valid unquoted uppercase output aliases are rejected as captured-result mismatch

Location: `proposals/phase3-d01-provenance-v1/sql_proof.py:74; proposals/phase3-d01-provenance-v1/verifier.py:137-146`.

Reproduction: `Canonical SQL with AS RATE / ORDER BY RATE, or team AS SQUAD and secondary ORDER BY SQUAD`.

Actual: contradicted/captured_result_mismatch because interpreter uses lowercase keys while actual SQLite output retains RATE/SQUAD. Expected: proven within advertised unquoted alias grammar; keep quoted mixed-case aliases explicitly unsupported.

## Preservation and boundaries

Compared every base tracked path by Git blob/mode: 177 base files; 176 unchanged; only STATUS.md changed. Seven new proposal files were added. The base/current tree maps and source hashes are in the JSON report.

Inspected root AGENTS/PROJECT/DECISIONS/ARCHITECTURE/STATUS, approved issue95 comment6256182861, PLAN/README/contract, independent-controls.md, all four candidate Python files and their entrypoints/imports before execution. Issue receipt6273598983 remains review-pending and introduces no hold.

The trust claim is correctly conditional: resolver and expected are independent host inputs, object identity blocks serialized self-authentication, synthetic_sqlite is the sole proving origin, and every verdict is live_qualified=false. There is no implemented live host adapter. The malformed HostCapture finding does not demonstrate a claimant trust bypass.

No live service, model, captured failed SQL, historical rescoring, heldout access, resource operation, broad test discovery, simulation, PR action, automatic review, activation or merge occurred. This review supplies offline implementation evidence only.

Disposition: **revise** these four findings with bounded red/green controls, then request a narrow exact-head re-review. Original phase gates and historical evidence remain unchanged.
