# ClickHouse timeout diagnosis and inactive fix proposal v1

**The original timeout is confirmed on the server. Scalar-expression JIT is the leading explanation for the long cancellation delay, not a conclusively isolated cause. The fix is inactive and has not been proven against a live server. No captured SQL was replayed, no Treatment A/model call was run, and frozen methods remain unchanged.**

## Observed diagnosis

The preserved response-format-v1 execution at `bd717bb844aba39fd2edba69aa6094d8fe926340` raised `RuntimeError: ClickHouse query failed: timed out`. The captured SQL uses the approved table, existing columns, the active-work filter, grouping by team, a percentage expression, ordering and limit. The SQL is retained byte-for-byte with its UTF-8 hash `9329ce538cfd6c9070a173b2b84d080918312e165d8ab8362940361277073363`. Whitespace-normalized text matches the one existing server query with ID `887e2a23-9b62-4107-b8ae-037a583a3f9c`. No result or expected team/rate is derived or supplied by this diagnosis.

| UTC on October 18, 2026 | Preserved observation |
| --- | --- |
| 02:27:41.746422 | Client query_clickhouse_start |
| 02:27:42.677967 | Server receives HTTP request for matching query ID |
| 02:27:42.952340 | Server executeQuery logs matching SQL |
| 02:27:45.326334 | Read plan: one part/mark, approximately 500 rows; not a completed-read measurement |
| 02:27:45.431840 | Same query thread logs ExpressionJIT compilation of divide(multiply(100., UInt64), UInt64) |
| 02:27:53.622006 | Background CancellationChecker marks this query timed out at 10,000,000 microseconds |
| 02:27:57.136286 | Client tool raises after 15.441581292 seconds |
| 02:28:25.025158 | Query thread finally records code 159, TIMEOUT_EXCEEDED, maximum 10,000 ms |
| 02:28:26.121185 | DynamicQueryHandler records the same query's exception |

The JIT trace-to-error gap is 39.593318 seconds; cancellation mark-to-error gap is 31.403152 seconds. Two error records share one query ID; they are not two attempts. The client had already stopped waiting, so it could not retain the later server HTTP exception body. The server then logs an attempted Request Time-out response; the client did not receive that response. No completed result is present. The server's query peak-memory log is 1.97 MiB, not an out-of-memory exception or host/model memory measurement.

This rules out a missing endpoint, unknown-column failure and a completed successful tool response for this observed query. It establishes a server execution-time cancellation with delayed query-thread handling and a client wait expiring first. It does **not** prove that all SQL alternatives would pass, that scalar arithmetic is scientifically correct under the frozen scorer, or that the overall environment was free of contention.

## Mechanism and uncertainty

The last query-thread trace before the gap is expression compilation. [ClickHouse's current upstream ExpressionJIT source](https://github.com/ClickHouse/ClickHouse/blob/master/src/Interpreters/ExpressionJIT.cpp) places that trace before synchronous native compilation/cache construction. [The official compile settings reference](https://clickhouse.com/docs/reference/settings/session-settings/compile#compile_expressions) identifies compile_expressions as the scalar-function/operator native-compilation setting. This supports disabling that path as a narrow candidate for review. The source reference is current upstream, not a verified checkout of the deployed 26.8.4.11 binary.

[Official execution-limit documentation](https://clickhouse.com/docs/reference/settings/session-settings/max-execution#max_execution_time) explains that cancellation occurs at designated checkpoints, so observed elapsed time may exceed max_execution_time. A 10-second server setting therefore does not guarantee that an exception reaches a 15-second HTTP client. Here the background checker did fire near the configured limit, while the query thread reported much later.

The logs contain no compilation-end timestamp, CPU profiler stack, JIT-duration metric or controlled comparison. We cannot assign all 39.59 seconds to compilation or distinguish compiler initialization, scheduling, memory pressure and other waits. Shared system-log writes and background merges continued; they are possible contributors, not proven causes. The earlier model memory snapshot does not establish causal resource pressure. No new diagnostic SELECT, EXPLAIN, corrected query or warm-up was issued. Source inspection and fake HTTP cannot validate a live performance fix.

## Concrete versioned candidate — inactive

Proposal ID: **runtime-clickhouse-expression-jit-off-v1**. Patch base: exact execution source `bd717bb844aba39fd2edba69aa6094d8fe926340`; proposal branch starts from evidence-only descendant `87d2eb282cad6849fba346e1b60f65b2a6028040` with identical runtime source.

The patch adds **one HTTP request parameter**, `compile_expressions=0`, inside query_clickhouse's fixed parameter dictionary. It changes no SQL bytes and supplies no answers, expected values or task-specific prompt examples. The model-facing prompt/schema/tool description, parser/scorer, task/reference bank, policy corpus, dataset generator, model and settings remain unchanged. Query validation and error-handling ASTs are unchanged. Server time 10 seconds, HTTP timeout 15 seconds, rows/bytes/memory/thread limits, read-only permission, six model steps, two evidence tools and zero-retry policy stay intact. Aggregate/sort JIT settings are not changed because they were not the observed compilation path.

| Pin | SHA256 |
| --- | --- |
| Candidate patch | `2a8bb4c3c6c8794a1414ab3c51f279e8f7b1a2d74e03326c9df840336c1b6aca` |
| Original transport source | `3f4667601120d0a660274a66da5608da4de2461ff4a5b86385a731d3daa5f1c1` |
| Candidate transport source | `aded909b246939168a6d3e6e3ab9c3622d7058e5fbcb02cb004a726fa3382f9c` |
| Original contract | `c58b9f0acb2217fca19f0ea199f167e07bf455ad1865fc727e07239249c8d2bc` |
| Candidate contract | `6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4` |
| Inactive configuration | `75b2519ce5c24779f414a5afb9dfa6ca4277973d7cda3fbba58668964e2e93c2` |

The inactive configuration contains a new configuration ID, active=false, zero live attempts, no activation authorization and an unpassed runtime gate. It is under proposals/, not configurations/. Existing production source and approved/historical configurations on the proposal branch are byte-identical to the evidence base. Only the disposable offline-validation checkout receives candidate.patch. No live runner is wired for the new ID. The existing approved configuration's fingerprint will reject the candidate transport; it cannot be silently reused.

This changes an execution setting and may affect latency, compilation cache behavior or floating-point details. No numerical equivalence, timeout resolution, architecture parity or scientific acceptance is claimed. The request setting is tested as delivered; the live server's effective setting, possible SQL SETTINGS interactions and constraint permissions are unverified. The observed SQL had no SETTINGS clause. Activation requires a separately reviewed execution configuration and explicit authorization, including any numerical-equivalence and environment/parity checks appropriate to that version. No timeout increase, SQL rewrite, scorer change, cache warm-up or server-global tuning is proposed.

## Offline validation

Baseline proposal checkout passed 363 tests before changes. The six focused transport probes were run against the original source: **one failure**, specifically absent compile_expressions=0; five unchanged-boundary controls passed. Against the disposable candidate, all six pass on Python 3.11 and 3.12. They submit only unrelated synthetic SQL to fake urllib HTTP, with socket/DNS access denied. The preserved task SQL is only read, hashed and compared as text.

Focused controls verify exact request SQL/POST/options, unchanged 15-second wait and all existing resource limits; timeout failure after one call with no retry; safe preservation of a fabricated code159 HTTP error; terminal body-read timeout and response close; rejection of other-table, mutation and multi-statement input before transport. The candidate does not correct invalid responses or change scoring.

Final full suites pass **364 tests on Python 3.11 and 3.12** for the inactive proposal, including a disposable patch/application-and-inactivity wrapper. The candidate checkout passes all **363 original tests on each version**, plus the six focused candidate tests separately. Counts are not additive independent experiments. Main-targeted hosted Python/CodeQL workflows do not run for this stacked draft; these results are local offline evidence.

## Evidence and research boundaries

All **20 original**, **4 scope-v1** and **4 response-format-v1** raw-file hashes match their sealed inventories. Five earlier evidence archives match their original hashes. All three execution checkouts remain clean at their original immutable commits. The failed response-format run remains execution_error, no final response and no score; absence is not zero. No experiment was repaired, repeated or rescored.

Newly recovered logs are a dated addendum. The copied complete error log and 20,000-line main-log tail are retained locally in work/clickhouse-timeout-log-snapshots, with file hashes/byte counts and extraction line numbers in diagnosis.json. Full unrelated service logs are not published. Matched query records and complete exception stacks are preserved separately for review. The tail is bounded and is not a claim of complete lifetime server history. Docker metadata was read without changing containers, settings, accounts or permissions; no environment secrets were logged. All subsequent tests and analysis were offline.

Phase 2 remains unqualified. Phase 3's valid-SQL-alternative/fabricated-value defects, Phase 4's twelve decisions and statistical freeze, held-out access, architecture comparisons and Phase 5 entry remain separate gates. The October 23 Phase 5 target remains at risk. Existing draft PRs remain unmerged. No paid provider, automatic Codex review, deployment or live attempt is authorized by this proposal.

Next: review this inactive setting change and the evidence/uncertainty. Acceptance would require a new reviewed runtime configuration; this diagnosis does not request or consume a live attempt. The current authorization remains **zero live runs**.

## Inactivity and source review

The clean offline validation checkout is pinned at 2252aed9803d9276934951676b76b889857c411f. Default source-only preflight refuses the inactive configuration with configuration_scope_version_or_standalone_boundary_differs and runtime_offline_validity_gate_not_passed; services_contacted=false, no worker entry. A deterministic source-backed review confirms 70 frozen files unchanged on the proposal branch and only the one added parameter in the candidate; removing that dictionary entry makes the entire transport AST identical. This is reproducible source review, not an independent human/agent review or live validation.
