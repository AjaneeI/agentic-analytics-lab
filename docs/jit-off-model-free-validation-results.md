# PR111 bounded model-free JIT-off validation — results

**The six originally planned synthetic SQL requests completed with HTTP200. The candidate's effective compile_expressions setting is false; the original transport reports true. Existing limits match. The two declared scalar/aggregate fixtures match their expected values and each other, with zero observed numeric difference across15 compared cells. No TreatmentA, failed-SQL replay, model call, application-table read, frozen-scorer change or PR merge occurred.**

This is narrowly scoped runtime-setting and synthetic-value evidence. It does not establish that the original timeout is fixed or accept Phase2.

## Authorization, protocol and checker correction

The owner explicitly approved bounded, model-free validation of PR111's JIT-off configuration using unrelated synthetic SQL, preserving all evidence and limits, without replaying failed SQL, running TreatmentA or merging. The protocol originally specified six requests and fixed SQL, expected values and finite-only relative/absolute1e-12 tolerances before any live query.

V1 at commit `3ad3b85abe7c09cd2c190781a83894361cb1778f` issued only candidate-settings. ClickHouse26.8.4.11 returned HTTP200, compile_expressions="false" and the exact existing resource limits. The checker incorrectly required "0" or "1" strings and stopped with AssertionError: unknown effective compilation mode. **V1 remains failed_stopped_without_retry**, sealed and unchanged. It is not reclassified as passed. This was a diagnostic Boolean representation bug, not a ClickHouse error or benchmark result.

V2 at commit `00bef0e9c416bfaadba0094c49e12772775f9f57` explicitly versions acceptance of the exact false/true Boolean strings alongside0/1 for settings inspection only. No benchmark response parser or scorer was altered. The sealed prior raw response supplies V2's candidate-settings prerequisite without reissuing that request. V2 issued only the five requests not yet issued. Its corrected checker and all remaining SQL were pinned before any numeric live result was observed. Numeric criteria and the five SQL strings are unchanged from the original protocol. The combined ceiling remains six requests, with zero retries or replacement queries. This completes the approved model-free work without treating a diagnostic checker correction as benchmark activation.

V1 protocol SHA256: `d58e98209bcfc43f4dec4c3fed27cc1dbe8e41fe3444bb0a8ec11f1beca9aac6`. V2 protocol SHA256: `0337f0d7ae4d47991b0b4a47a3ebdb0c8cc70900f3de523010f811242edce8ca`. Both protocols, original error, headers, response bodies and manifests are preserved. The earlier offline logging-name collision was also fixed before live entry; its failure log is retained. No live evidence was corrected or overwritten.

## Source and settings pins

| Item | Exact pin |
| --- | --- |
| PR111 proposal head | 7f010f242c9b8bfe10f83f0bfd19650ea8867305 |
| Exact isolated candidate checkout | 2252aed9803d9276934951676b76b889857c411f |
| Original transport SHA256 | 3f4667601120d0a660274a66da5608da4de2461ff4a5b86385a731d3daa5f1c1 |
| Candidate transport SHA256 | aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c |
| Candidate patch SHA256 | 2a8bb4c3c6c8794a1414ab3c51f279e8f7b1a2d74e03326c9df840336c1b6aca |
| Original contract | c58b9f0acb2217fca19f0ea199f167e07bf455ad1865fc727e07239249c8d2bc |
| Candidate contract | 6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4 |

The candidate adds only the fixed HTTP parameter compile_expressions=0. The exact existing original/candidate functions produced all six requests, with unchanged SQL validation, authentication, request limits and error behavior. A passive response wrapper captured request parameters, SQL, response headers and bytes without adding headers or changing SQL. Existing local credential values were not recorded. The original and candidate source trees were verified clean at their pins before and after checks. PR111 remains draft/unmerged; its benchmark configuration remains inactive.

| Effective server setting | Original | Candidate |
| --- | --- | --- |
| Server version | 26.8.4.11 | 26.8.4.11 |
| compile_expressions | true | false |
| readonly | 1 | 1 |
| max_execution_time | 10 seconds | 10 seconds |
| Client HTTP timeout | 15 seconds | 15 seconds |
| max_result_rows | 1000 | 1000 |
| result_overflow_mode | break | break |
| max_rows_to_read | 10000 | 10000 |
| max_bytes_to_read | 10485760 | 10485760 |
| max_memory_usage | 134217728 | 134217728 |
| max_threads | 2 | 2 |

No SQL SETTINGS clause, global server setting, account permission, cache warm-up, model setting, benchmark budget, policy/task/reference or scorer changed.

## Synthetic SQL and observed values

The settings query reads getSetting values only. The scalar and aggregate queries use four inline UNION ALL rows with x values -2.5,0,1.25,7.75. They contain no FROM application table, table function, failed-query text, benchmark answer or held-out source. The original six-request plan matches actual request IDs/SQL in order exactly; one V1 plus five V2 requests.

| x | affine = 2*x+0.5 | seventh = (x+3)/7 |
| --- | --- | --- |
| -2.5 | -4.5 | 0.07142857142857142 |
| 0 | 0.5 | 0.42857142857142855 |
| 1.25 | 3 | 0.6071428571428571 |
| 7.75 | 16 | 1.5357142857142858 |

Both transports returned these same scalar rows. Both aggregate results were sum_x6.5, min_x-2.5, max_x7.75. Observed absolute difference is zero for all15 returned numeric cells. Fixed expected values and tolerances were declared before any numeric response; no outcome-driven criterion adjustment occurred.

## Request, timing and resource evidence

All six responses are HTTP200; exact server query IDs are in outcome-summary.json and both wire-captures.json artifacts. V1 captured one request and stopped in 0.151646334s. V2 completed five unissued requests in 0.578849459s. Sum of active capture intervals: 0.730495793s. These intervals exclude the intervening engineering/checker-amendment work and are not a contiguous elapsed-time measure or a speed comparison.

V1 start/end UTC: 2026-10-18T03:07:42.487215+00:00 / 2026-10-18T03:07:42.639172+00:00. V2 start/end UTC: 2026-10-18T03:09:09.525005+00:00 / 2026-10-18T03:09:10.104236+00:00. Each request retained10s server/15s client limits; neither stage started new work beyond its120s diagnostic guard. No request timed out. No request or experiment was retried.

The largest returned X-ClickHouse-Summary memory_usage was 1451855 bytes. Exact returned counters are retained, without treating that field as host/GPU memory or guaranteed peak consumption. Headers reported result_rows0 while response bodies contained rows; body parsing is authoritative for returned row counts. No per-request CPU/GPU, energy or peak-model-memory claim is made. There was no model or paid-provider call.

## Offline and postflight verification

V1 harness validation on Python3.11/3.12 exercised fabricated success, bad JIT setting, wrong limit, wrong numeric value and timeout; checked first-error stop, zero retries, duplicate-output refusal and finite-only numeric types with sockets/DNS denied. V2 separately exercised exact Boolean representations and success/wrong-limit/wrong-value/timeout controls on both Python versions before continuation. These checks are engineering fixtures, not live benchmark evidence.

Fresh full repository suites pass364 tests on Python3.11 and3.12. Source/configuration/model/dataset/scoring files remain unchanged. Postflight verification confirms the six actual requests equal the original predeclared SQL plan, all resource limits match, both raw stage seals hold, original20+4+4 failed-run hashes match, and six prior evidence archives remain unchanged. Both previous failure/proposal histories and all three failed experiments remain preserved. Neither V1 nor V2 invokes the benchmark worker, scorer or Ollama.

## Interpretation and next action

Supported: the local server accepts the exact PR111 request-setting amendment; its effective scalar-JIT setting is false, with existing limits; and the two declared synthetic fixtures agree numerically with expected values and the original transport. The diagnostic checker representation issue is explicitly preserved and versioned.

Not established: the original query timeout is resolved; scalar JIT was its exclusive cause; JIT-on compilation engaged for these small/possibly constant-folded fixtures; all-query floating-point equivalence; architecture parity; cold/warm independence; speedup; final model response compliance; Phase2 qualification, Phase3 evaluator acceptance or Phase4 method freeze.

Next authorized preparation is a separately reviewed, hash-pinned benchmark runtime configuration if the owner wants to pursue the candidate. **No TreatmentA is authorized by these diagnostic results.** PR111 is not merged or automatically activated. Architecture comparisons and held-out work remain blocked, and October23 Phase5 entry remains at risk.
