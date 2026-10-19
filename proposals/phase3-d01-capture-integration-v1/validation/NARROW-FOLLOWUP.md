# Narrow failure-provenance follow-up

Reviewed source remains HEAD 67fa0d1cf6773d41ffa61fa401956ef73fa5906e, tree 34caf1eb1cc33078ec01c29630cefbdd3d095bbe. Original REVIEW.md and original runner results are preserved unchanged. This new evidence qualifies the earlier acceptance: request in-scope corrections before accepting failure-provenance completeness.

P2 — Lone-surrogate query leaves a partially registered capture. `h.query('SELECT \ud800 AS bad')` reaches SQLite and raises UnicodeEncodeError. In finally, capture is stored in `_records`, but `verifier.binding(record)` hashes the SQL with UTF-8 and raises again before `_expected` or the event is recorded. Observed: capture present, zero events, and `h.verify(claim, call=h.calls[0])` raises KeyError. A malformed string is within the callback input-validation boundary; no adversarial Python host is needed. No false acceptance was observed. Rejecting non-UTF-8 input before allocating a call, with a zero-execute failure event whose digest handling cannot itself fail, would preserve the intended boundary without changing the old verifier.

P2 — Execute cancellation omits its error provenance. A test-only connection proxy raises KeyboardInterrupt on execute, with the real memory connection restored and closed afterward. The BaseException propagates and the capture correctly remains success=false, complete=false; verification returns insufficient/execution_not_successful, live_qualified=false. However, the event has error_type=null and error_message=null because the handler catches Exception only. This is an evidence omission, not a promotion or actual process-interruption test. Recording the caught BaseException and re-raising it would satisfy the same failure-event promise without swallowing cancellation.

The fault-injection proxy is exclusively a reproducibility mechanism; this finding does not assume a malicious host is within the threat model. It represents a normal execute interruption at the callback boundary. No signal, subprocess, network, active import, service, or external database was used.

Executed once with Python 3.11.16:

```sh
/Users/ajaneeigharo/.local/share/uv/python/cpython-3.11.16-macos-aarch64-none/bin/python3.11 /Users/ajaneeigharo/Documents/Codex/2026-10-17/execute-the-phase-2-5-acceleration/outputs/phase3-d01-capture-integration-v1-20261019/reviewer/narrow-failure-probes.py
```

The inspected probe imports the existing guarded runner before importing the adapter or constructing memory SQLite. Receipt: narrow-failure-probes.json. Guard recorded two memory connections and zero blocked side-effect attempts. No broad rerun or additional test scope. Parent integrates corrections; this reviewer made no implementation edits. D01-TIE-ORDER-01 remains unchanged and independently blocks full semantic acceptance.
