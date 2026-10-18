from pathlib import Path
import json
b=Path(__file__).resolve().parent.parent;o=b/'outputs/jit-off-one-attempt-20261018';s=json.loads((o/'terminal-outcome.json').read_text())
text=f'''# JIT-off Treatment A: terminal timeout, Phase 2 unqualified

**Exactly one new owner-authorized bounded standalone Treatment A was executed. It failed on the first ClickHouse evidence call with HTTP 408, server code 159 (`TIMEOUT_EXCEEDED`). JIT-off did not resolve the timeout in this attempt. No final normalized response or deterministic score was produced; absence is not zero. Phase 2 remains unqualified.**

The authorization is consumed. There was no retry, automatic correction, replacement run, SQL replay, post-outcome service diagnostic, historical rescoring, method change, paid-provider call or PR merge. This report and tracker reconciliation are the end of the authorized work; no other experiment is started.

## Authorization and exact execution pins

Client approval date: October 18, 2026 America/New_York. Raw event timestamps retain their original UTC values. [Draft authorization PR114](https://github.com/AjaneeI/agentic-analytics-lab/pull/114) preserves the new immutable authorization configuration and owner record; [pre-launch verification comment](https://github.com/AjaneeI/agentic-analytics-lab/pull/114#issuecomment-6245560535) records exact parameters/invocation before entry. The parent activation-only configuration and all consumed historical authorizations remain unchanged.

| Item | Exact pin |
| --- | --- |
| Execution commit | 688f62dcedb3116e8ae46579cea0fd135eba94ce |
| Authorization configuration SHA256 | f1afa4f6d3b6238b87155729d63453dd43d7d001f6aeb45c99cd64dd9e8ca27b |
| Runtime version | runtime-clickhouse-expression-jit-off-v1 |
| Complete experimental contract | 6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4 |
| Transport SHA256 | aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c |
| Model-facing query-tool SHA256 | 0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9 |
| Prompt SHA256 | 56fb5a95cd7e471ded2fdbc13f0e0e58ee9939e427f8bc733c0ea6ce60f579ce |
| Frozen scorer SHA256 | 6d3d9c8743fabade1090a7cd9a8c428fb7bbcb5c2b5c605451ac1a6860029f7a |
| Qualification runner SHA256 | be1bd5441bb439a525104c3da5d3ac3918ddb995f6a29bcc91e7a28d7ea27769 |
| Passive capture SHA256 | 28859a2bdbe12d46bfd8e094e033ce96842b5000116f22a7360b5829853224de |

The [authorization execution record](authorization-execution-record.json) contains the full configuration, source-file fingerprint and exact argv. [Final invocation](final-invocation.txt) preserves the absolute shell command. [Final preflight binding](final-preflight-binding.json) binds helper/launcher/CSV hashes. The new source commit changes only three administrative files: new authorization JSON, owner record and status. Every runtime, client, worker, prompt/parser, tool/security guard, scorer, fixture, dataset generator, runner and capture byte matches activation commit4d98b8f. No scientific method or acceptance criterion changed.

## Final offline and local preflight

Full **375 tests passed on Python3.11 and375 on Python3.12**, with sockets/DNS denied; fresh logs are [3.11](full-python311.txt) and [3.12](full-python312.txt). Existing scripted delivery, fixed-option transport, one-entry/zero-retry, type-rejection and passive-capture regressions are included. [Independent authorization review](independent-authorization-review.md) confirms exact pins/command/authorization boundaries and no outstanding must-fix findings.

Two pre-execution engineering findings are retained, without modifying benchmark code. A direct-import preflight-helper path dependency failed offline and was fixed before any services were contacted. Independent review then required binding the original CSV digest rather than accepting mutually changed CSV/database contents; a failing then passing two-case offline regression and independently rechecked guard are preserved. The initial review finding remains saved. Final helper/launcher hashes and exact command were published before the sole attempt; no experimental outcome had been observed during these corrections.

[Final live preflight](final-service-preflight.json) verified:

- Local Ollama `hermes-local:qwen3.5-9b`, exact digest `0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c`.
- Exact13-column schema,500-row count and all500 rows equal the existing pinned seed42 CSV. CSV SHA256 `cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef`; declared-type canonical dataset hash `c447c789b1b8528e1eb8cfae4456078a58d0ea65173a09dadb2783712392fc12`. Integer/Float32/null conversion is dataset attestation only; benchmark responses/parser/scorer are unchanged.
- Effective ClickHouse26.8.4.11 setting compile_expressions=false and every fixed limit. The only approved transport intervention remains compile_expressions=0; no global setting or account change.
- Clean immutable commit/configuration, exact complete experimental contract, unchanged prompt/tool/model/capture pins, exclusive fresh evidence directory and zero-retry policy.

Setup made four read-only SQL requests: schema, count, fixed-setting inspection and full development-data attestation. The unchanged runner repeated its existing two schema/count setup requests and model-catalog check immediately before entry. Setup calls are outside the existing two benchmark evidence-call ceiling; none supplied task answers to the model or changed data. Dataset reads may affect cache state; no cold/warm or causal timing claim is made. No warm-up inference or additional diagnostic experiment was conducted.

## Exact observed outcome and acceptance

Capture start UTC `{s['capture_start_utc']}`; end `{s['capture_end_utc']}`. The first and only model return selected query_clickhouse. Its model-generated SQL is preserved unchanged in raw events; SQL SHA256 `{s['captured_query_sha256']}`. It is byte-identical to the preserved prior timeout SQL, established by string/hash comparison only. It was generated by the newly authorized model call, not manually replayed. No historical score or architecture comparison was computed.

The evidence call began `{s['query_start_utc']}` and raised `{s['query_error_utc']}`: `ClickHouseQueryError: ClickHouse query failed: HTTP 408; server code159 (TIMEOUT_EXCEEDED)`. No tool result reached the worker. Policy retrieval, final response synthesis/validation and scoring were not reached.

| Established requirement | Result |
| --- | --- |
| Exactly one worker entry | Met:1 |
| Preserved raw events/configuration/source provenance | Met |
| Complete collector, no collection errors | Met |
| Clean valid source/config/contract postflight | Met |
| Final normalized response | Not produced |
| Frozen deterministic score / task_success true | Not produced; score and task_success absent, not0/false invented values |
| Phase2 qualification | **Not met: terminal execution error** |

The existing qualification gate is unchanged: frozen task_success must be true, collection complete and postflight valid with exactly one worker entry. Passing preflight or preserving a failure cannot replace the missing successful result. The collector is complete/no errors, and its valid postflight pins remain688f62d/f1afa4/6d6403. The four raw files are `INVOCATION_STARTED.json`, `events.jsonl`, `manifest.json`, `error.json`; no execution.json or raw-result.json exists. The CLI exits1 from the unchanged propagated exception. No score is manufactured.

## Timing, usage and resource observations

| Observation | Value |
| --- | --- |
| Capture wall time | {s['capture_wall_seconds']:.9f} seconds |
| Outer launch wall time | {s['outer_wall_seconds']:.9f} seconds |
| Query wrapper observed wall time | {s['query_observed_wall_seconds']:.9f} seconds |
| Returned model duration | 82.447105417 seconds |
| Input / output tokens | 839 /352 |
| Model attempts / returns | 1 /1 |
| Benchmark tool attempts / returns | 1 /0 |
| Retry / correction / replacement | 0 /0 /0 |
| Benchmark paid-provider calls / incremental spend | 0 /USD0 |

Model settings remain temperature0, num_predict512, num_ctx65536, timeout120s and keep_alive30m. Existing budgets remain6 model steps and2 evidence calls, with zero retries/re-prompts. ClickHouse fixed limits remain readonly1, server10s, HTTP15s, result1000/break, input10000rows, read10485760bytes, memory134217728bytes and2threads. Observed wrapper elapsed includes transport/error handling and does not redefine the configured server/client limits.

Before capture the approved model was absent from `/api/ps`; after capture it reported context65536, size7693192396bytes and size_vram7693192396bytes. The OS llama-server RSS snapshot was7308247040bytes after the attempt. Capture-host CPU deltas were approximately0.013998user and0.072422system seconds; its process-lifetime peak RSS snapshot was32735232bytes. These are shared process/service snapshots and capture-host accounting, not per-query server CPU/GPU, energy or peak model-memory consumption. [Terminal outcome JSON](terminal-outcome.json) retains exact observations. Human hands-on minutes were not measured. Local model usage incurs no paid-provider charge; Codex engineering accounting is outside that benchmark-spend statement.

## Preservation and claim limits

Before/after receipts independently verify all28 raw historical failed-run files, eight prior ZIP archives,98 activation-packet files and92 prior source/configuration files. All original failed runs, configurations, fingerprints and evidence remain unchanged. New raw evidence is sealed in its own SHA256 inventory; captured SQL/errors/metrics are not corrected or reclassified. The execution checkout stays clean at688f62d. A separate results-only branch holds documentation and copies, preserving the execution source.

**Timeout resolved? No.** The sole new evidence query timed out despite approved JIT-off transport and successful preflight. This falsifies a claim that this amendment was sufficient to prevent the observed timeout. It does not identify an exclusive root cause, establish actual expression-compilation behavior inside the failed query, or justify another intervention. No post-failure server logs, SQL diagnostics, alternate settings, extra model calls or replay were authorized or performed.

**Does the attempt qualify? No.** Final response and deterministic score were not produced. Phase2 remains active and unqualified. Neither the prompt's live compliance nor eventual scoring correctness was tested to completion.

**What remains unresolved?** ClickHouse timeout cause and sufficient remediation; final response-format compliance; Phase3 evaluator semantic/valid-SQL/metric-provenance defects; all12 Phase4 decisions and code/document resampling mismatch; strong-single/runtime/schema-parity acceptance; architecture comparisons and held-out gates. No new Phase3/4 evaluation or simulation was run after this outcome. Phase5 entry by October23 remains at risk.

## Closeout and stop

The exact one-attempt authorization is consumed and its exclusive launch/invocation markers remain. Current immutable configuration is a historical approved authorization, not permission to run it again. GitHub, Notion and Asana reconciliation is the final closeout step, recorded separately in reconciliation-receipt.json after the GitHub evidence exists. All PRs remain unmerged; no automatic review is requested.

Further diagnosis, configuration changes or any new experiment require their applicable separate authorization. This session stops after preservation, reconciliation and reporting, as requested.
'''
for a,c in {'Phase2':'Phase 2','Phase3':'Phase 3','Phase4':'Phase 4','Phase5':'Phase 5','Python3':'Python 3','and375':'and 375','Exact13':'Exact 13',',500':', 500','all500':'all 500','seed42':'seed-42','ClickHouse26.8':'ClickHouse 26.8','code159':'code 159','Met:1':'Met: 1','not0/false':'not 0/false','remain688':'remain 688','839 /352':'839 / 352','1 /1':'1 / 1','1 /0':'1 / 0','0 /0 /0':'0 / 0 / 0','USD0':'USD 0','temperature0':'temperature 0','num_predict512':'num_predict 512','num_ctx65536':'num_ctx 65536','timeout120':'timeout 120','keep_alive30':'keep_alive 30','remain6':'remain 6','and2':'and 2','readonly1':'readonly 1','server10':'server 10','HTTP15':'HTTP 15','result1000':'result 1000','input10000':'input 10000','read10485760':'read 10485760','memory134217728':'memory 134217728','context65536':'context 65536','size7693192396':'size 7693192396','size_vram7693192396':'size_vram 7693192396','was7308247040':'was 7308247040','approximately0.013998user':'approximately 0.013998 user','and0.072422system':'and 0.072422 system','was32735232':'was 32735232','all28':'all 28',',98':', 98','and92':'and 92','at688':'at 688','all12':'all 12','October23':'October 23','parent is PR #113 at4d98':'parent is PR #113 at 4d98','commit4d98':'commit 4d98'}.items():text=text.replace(a,c)
(o/'REPORT.md').write_text(text)
print('Wrote terminal report; no service/scorer/experiment invocation.')
