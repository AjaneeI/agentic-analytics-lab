# Phase 2 Treatment A — October 17, 2026

**Gate: NOT QUALIFIED. One authorized attempt completed with an execution error. No retry.**

Authority: [#94](https://github.com/AjaneeI/agentic-analytics-lab/issues/94), [#95](https://github.com/AjaneeI/agentic-analytics-lab/issues/95), and the [pinned #73 continuation](https://github.com/AjaneeI/agentic-analytics-lab/issues/73#issuecomment-6126560476). This is development-only runtime evidence, not a held-out or architecture-comparison result.

## Verified setup

- Existing checkout preserved on its historical branch. A separate detached worktree used immutable `5f36bfd4633c7b80dccefb7179da0c46fbb918f4`; before and after HEAD and clean status matched.
- Existing Ollama and Docker/ClickHouse services were healthy. Initial failures were sandbox access restrictions; scoped local access restored connectivity. No restart, installation, permission change, credential change, or service reconfiguration occurred.
- Repository preflight passed authenticated read-only access to `agentic_analytics.delivery_work_items`: exactly 500 rows.
- Model: `hermes-local:qwen3.5-9b`, digest `0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c`.
- Runtime: Python 3.14.7; Ollama server 0.35.0, CLI 0.34.4. The observed version difference was preserved, not repaired.
- Unchanged executor: `BoundedLocalExecutor`, oracle metadata route, `multi_source`, only `query_clickhouse` and `retrieve_policy`, at most two evidence calls and six model steps.
- Existing mocked Ollama client tests: 5/5 passed. They establish payload regression checks, not live task success.

Exact fixture request:

> Among active work items (status != done) in the seed-42 snapshot, identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.

## Observed outcome

| Field | Result |
|---|---|
| Invocation count / retries / re-prompts | 1 / 0 / 0 |
| Start | October 17, 2026, 20:11:19.638 EDT (`2026-10-18T00:11:19.638056Z`) |
| End | October 17, 2026, 20:12:12.058 EDT (`2026-10-18T00:12:12.057710Z`) |
| Executor/runner wall time | 52.416534 seconds |
| Process exit | 1 |
| Attempt status | `execution_error` |
| Exact terminal error | `RuntimeError: ClickHouse query failed: HTTP Error 404: Not Found` |
| Final response / structured values / evidence references | Not returned |
| Deterministic score and reason codes | Not produced; scorer was not reached |
| Model/tool totals, tokens, model duration | Unavailable because executor raised before returning observations |
| Minimum observable activity | Model response reached query dispatch; at least one query attempt reached the HTTP transport |
| Human intervention minutes | Unmeasured; autonomous invocation, no re-prompt |
| Incremental benchmark provider spend | $0; local-only path, no paid fallback |
| Contract fingerprint | `5957e28d58aebea19eaf93c05db4bdf03c712fe020f7f3e65152f972773996ad` |

The traceback localizes the observed failure to ClickHouse query HTTP transport. It does **not** establish why the server returned 404. The pinned collector did not retain the failed SQL, HTTP response body, or partial model/tool trace; do not reconstruct them or invent a score. A read-only Docker log retrieval for the exact run window returned zero bytes. No query or model request was replayed.

## Resource and evidence limits

Passive snapshots recorded model context 65,536 and reported model/VRAM allocation 7,693,192,396 bytes after execution. System-wide memory free percentage changed from 37% to 14%. Process RSS observations were sampled, not a guaranteed peak or whole-machine utilization measurement.

Independent CPU-only calibration preparation briefly overlapped the run before being paused. Therefore latency and memory are descriptive observations under concurrent preparation, not controlled architecture-comparison evidence. This does not convert the execution error into acceptance.

The local evidence bundle retains the exact manifest, traceback, stdout/stderr, invocation marker, preflight, runtime/model identities, memory/VM snapshots, sampled process observations and SHA-256 inventory. The public companion directory contains reviewed manifests and a traceback with local path prefixes replaced by placeholders; those copies are explicitly path-normalized, not falsely labeled byte-identical raw logs. Local raw files were not edited. Known local credential literals were checked without printing them; no matches occurred in the bundle.

## Stop and next decision

Phase 2 remains active and unqualified. Phase 3–5 outputs are independent model-free preparation and cannot establish advancement. Treatment B, a second A attempt, SQL/prompt changes, provider changes and guard changes were not performed.

Owner authorization is required for a separate versioned next experiment and any changed capture/method/contract. First review this failed result and the independent grader/calibration blockers. A new approved investigation must preserve this outcome and must not silently retry the observed frozen experiment.
