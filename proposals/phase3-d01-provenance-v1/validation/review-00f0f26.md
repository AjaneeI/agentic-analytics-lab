# Narrow independent review — revise

Candidate `00f0f26cb3afebf33ea342e8a31b33a64e26943e`, tree `dc2080b44e88d9c9d90e25c3449c63ed1340e2a2`; base `43cf76b0acf64aba4f19eb510af12189b7a4ad04`, tree `39c633e7c59788b7611827bcfa61d7f57d52e419`. Exact diff from independently reviewed2e1bbf3 inspected before reruns. Checkout clean at completion;177base paths checked,176unchanged blob/mode,onlySTATUS.md changed;7inactive proposal files added.

Both required Python versions freshly pass26unit tests plus60named matrix controls,0failures/errors/mismatches. Original20reviewer probes per interpreter now all return expected outcomes:0crashes,0supported-valid false rejections,0unsupported-valid misclassifications and0false acceptances in that set. Source-backed original red receipt shows2failures+2errors for four regression methods before corrections.

Seventeen additional narrow correction-boundary cases per interpreter confirm collision rejection, quoted unsupported alias handling and strict Boolean/string/nonfinite rejection, but expose2false acceptances on each interpreter and3malformed JSON crashes onPython3.11. Each boundary run uses17newin-memory SQLite connections and0guard denials.

## R5 (P2): Unicode lowercasing widens the advertised ASCII result-label equivalence and accepts mismatched capture fields

Location `proposals/phase3-d01-provenance-v1/verifier.py:160`.

Reproduce: SQL canonical with blocked_pct alias renamed k; captured_rows=[{'team':'Amber','K':75}], where K is U+212A KELVIN SIGN. A second case renames team output k and supplies K:'Amber'.

Actual: Both malformed captured results return proven on Python3.11 and3.12 because K.lower()==k. SQLite output for AS k is ASCII k; SQLite case-insensitive identifier matching does not equate Kelvin sign and k.

Expected: contradicted/captured_result_mismatch; restrict captured labels to declared ASCII identifiers before folding or perform ASCII-only case conversion. Preserve raw hashes.

## R6 (P2): Bounded malformed JSON still escapes with RecursionError on required Python3.11

Location `proposals/phase3-d01-provenance-v1/verifier.py:111-113,136-138`.

Reproduce: For each config_json/result_json/snapshot_json replace field with '['*1200+'0'+']'*1200 (2401 characters), pin replaced immutable record using binding, and call verify.

Actual: Python3.11.16 raises uncaught RecursionError during json.loads in all three cases. Python3.12.6 returns explicit outcomes at this depth.

Expected: Explicit invalid_capture/invalid_snapshot/captured_result_mismatch or insufficient result; malformed host data must not crash the verifier. Catch recursion failures or enforce a safe structural depth bound before decode.

## Evidence and limits

Fresh receipts: validation-py311-00f0f26.json and validation-py312-00f0f26.json; adversarial-00f0f26-py311/312.json; alias-controls-00f0f26-py311/312.json; correction-boundary-00f0f26-py311/312.json. Reviewer scripts have only output names changed for the original20probes; correction_boundary_00f0f26.py supplies new bounded cases.

Review status: originalR1-R4reproductions resolved, but revise R5/R6 before closing malformed-evidence/result-reconciliation acceptance. These are host-owned malformed capture failures, not a demonstrated claimant trust bypass. Host resolver/expected independence, synthetic-only proving origin and always-false live qualification remain intact. No candidate file was edited by this reviewer. No live/runtime/heldout/history replay/resource/model/statistical/PR action occurred.
