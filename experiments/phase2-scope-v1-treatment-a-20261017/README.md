# Standalone Phase 2 Treatment A — approved scope observation v1

**Outcome: execution error; Phase 2 remains unqualified.** The single owner-authorized new attempt is consumed. No retry, response correction, rescoring, architecture comparison or held-out evaluation occurred.

The owner explicitly approved `runtime-sql-scope-v1` as a separate observation amendment after the earlier schema-only approval. Draft PR 106 records activation. The original failed run, schema-only configuration, pending proposal and all respective evidence/fingerprints remain preserved. The scope approval is resolved; a further live attempt is outside the consumed authorization.

## Exact experiment

| Field | Value |
|---|---|
| Execution commit | `57c3007a25af4ff21bec42138aa1df7268ee7d95` |
| Configuration | `phase2-runtime-schema-v1-scope-observation-v1` |
| Config file | `configurations/phase2-runtime-schema-v1-scope-observation-v1.approved.json` |
| Config SHA-256 | `832b76234e25d081736893c0eac50258447fb9e2ae17f8d54d6f029da2373c86` |
| Contract fingerprint | `d136b653e8b4bc2ebabfab403b4aef3c85155174719e7e1c40b290ddf29968f2` |
| Query-tool compact JSON SHA-256 | `0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9` |
| Schema / observation versions | `delivery-work-items-schema-v1` / `runtime-sql-scope-v1` |
| Local model | `hermes-local:qwen3.5-9b` |
| Model digest | `0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c` |
| Model configuration | Temperature 0; num_predict 512; num_ctx 65536; timeout 120 seconds; keep_alive 30m |
| Worker / task | Existing BoundedLocalExecutor; SB-D01; oracle metadata; deterministic multi-source route |
| Limits | Six model steps, two evidence calls, zero retries/re-prompts |
| Safe evidence tools | query_clickhouse, retrieve_policy |
| Environment | Existing local Ollama 0.35.0 and authenticated ClickHouse; Python 3.11.16; no service or permission changes |

## Final checks and setup

Fresh complete suites passed 350 tests on Python 3.11 and 3.12. Independent final activation review verifies the only changes from reviewed runner head aa5a511 are the approved configuration, authorization document and STATUS. Runtime, source/corpus/task/reference/scorer, model/client, SQL security and collector sources are unchanged. The schema-only and proposal files are byte-identical to their prior versions.

Approved source preflight returned no blockers. The preserved pending proposal still refuses before runtime/services/output creation. Twelve fake-HTTP captures verified actual request serialization with exact schema and 512/65536 options; no inference occurred in these checks. Independent security/frozen-input checks verified 18 frozen files and unchanged guard functions. Fresh real service checks verified exact model name/digest, all 13 schema columns and 500 rows.

A first setup-only DESCRIBE failed HTTP 401 / code 194 REQUIRED_PASSWORD because the new shell lacked the existing credentials. Only the existing local repository ClickHouse environment settings were loaded, without logging values or changing account permissions. Repeated setup passed before worker entry. This was not a Treatment A attempt. The actual runner separately repeated its fresh two-read schema/count preflight before reservation.

## Exact terminal result

One worker entry ran on October 17, 2026, 9:40:06–9:42:39 PM EDT (October 18 01:40:06–01:42:39 UTC). Both query_clickhouse and retrieve_policy returned. Three model calls returned. Final response contract validation raised:

`LocalWorkerError: clarification must be an object or null`

The retained final worker-returned JSON has a string clarification field. The worker raised before returning TrialExecution; the deterministic scorer was not reached. No normalized response, execution artifact or raw score artifact exists. **The deterministic score is absent, not zero.** The final content string remains unchanged, with stored SHA-256 `47941b092661674ba37aad7298a8cdd2f205dec57cdf6d059b5d1f4ec85a083c` and recorded `content_redacted=false`. No response value was repaired, normalized or rescored.

| Observed quantity | Value |
|---|---|
| Qualification CLI exit | 1 |
| Outer wall time | 153.823651 seconds |
| Capture wall time | 153.149972 seconds |
| Worker-entry-to-error wall time | 149.884235 seconds |
| Returned model-duration seconds | 136.60023775 |
| Returned input / output tokens | 3,031 / 793 |
| Model attempts / returns | 3 / 3 |
| Evidence tool attempts / returns | 2 / 2 |
| Retries / re-prompts | 0 / 0 |
| Incremental benchmark paid spend | USD 0; local Ollama only, excludes Codex engineering-credit accounting |
| Human hands-on minutes | Not measured; no zero inferred |
| Collector | Complete; no collector errors |
| Postflight | Valid; same commit, config hash and contract fingerprint |

The worker host's observed process-lifetime peak RSS after the run was 32,669,696 bytes. Host CPU deltas were approximately 0.021469 user and 0.120644 system seconds. The shared loaded model's after-run API snapshot reported size and size_vram 7,693,192,396 bytes and context length 65,536; its digest matched the approved model. These are host/shared-service snapshots, not per-request peak model memory or GPU/VRAM consumption. Capture and shared-service overhead affect wall times. No matched comparison is made.

## Evidence and claim boundaries

Local raw evidence is sealed in `outputs/treatment-a-scope-v1-20261017`: invocation marker, events, error and manifest, plus a checksum manifest covering those four original files. Both tools' inputs/returns, all returned model usage, final worker-returned content, error, source/config pins and before/after resource observations are preserved. The collector uses public projections; this is not a claim to retain a complete raw provider HTTP payload or hidden reasoning.

The adjacent outcome-summary.json is a reviewed, derived public summary. An independent terminal review verified the four sealed hashes, all 20 original failed-run hashes, exact counts, error, timing, usage and postflight without any model/SQL/scorer call. Raw local trace and stderr were not automatically published. No credential values are included in repository artifacts.

This result does not qualify Phase 2, accept Phase 3, freeze Phase 4 or enter Phase 5. Known valid-SQL-alternative and fabricated-number evaluator findings remain separate Phase 3 issues. Future comparisons remain blocked; no schema-enabled result is compared to schema-less history. No PR was merged, including PR 103.

The next Phase 2 decision is whether to authorize any separate versioned investigation or future experiment concerning response-contract conformance. No such change or run is made by this evidence branch. Independent model-free evaluator and calibration findings remain available for adjudication under PRs 98 and 100.
