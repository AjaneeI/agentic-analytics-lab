# Phase 2 CPU scheduling diagnosis and pending qualification decision v1

The failed JIT-off request spent substantial time runnable but waiting for CPU.
This is the strongest supported contributor to its timeout. The exact competing
workload, Linux/VM/host boundary and any common cause across all earlier failures
remain unresolved. JIT-off was delivered and recorded; disabling more compiler
paths or increasing frozen budgets is not justified.

## Observed evidence

The single preserved query-log row for `780faff9-7b12-4326-82bb-1ab47353d860`
reports exception159, duration10,583ms, read500rows/1,615bytes, result0rows,
memory1,251,663bytes, participating threads323/93 and peak2. Its recorded settings
include compile_expressions0 and the unchanged10s/128MiB/2thread/read/result limits.
It has no normalized model response or deterministic benchmark score.

| Recorded counter | Value |
|---|---:|
| OSCPUWaitMicroseconds | 7,850,621 µs |
| OSCPUVirtualTimeMicroseconds | 2,862,090 µs |
| RealTimeMicroseconds | 11,941,650 µs |
| DiskReadElapsedMicroseconds | 27,331 µs |
| ContextLockWaitMicroseconds | 64 µs |

These are query-thread aggregates, not a partition of wall time. No wall-time
percentage, counterfactual speedup or causal attribution to a named background
service is claimed. Missing map keys, including OSIOWait, are not zeros. Six hard
page faults were recorded; current swap/pressure observations are not historical
per-query measurements. The current container is native ARM64, has no configured
CPU quota and reports no cgroup throttling/OOM events. These weaken particular
current configuration hypotheses but do not prove historical host conditions.

The ClickHouse source defines CPU wait as runnable time awaiting OS scheduling
and RealTime as summed thread wall time. These current source definitions inform
interpretation, not an independently verified build-symbol match:
https://raw.githubusercontent.com/ClickHouse/ClickHouse/master/src/Common/ProfileEvents.cpp

Concurrent slow system-log flushes in the original window support shared delay.
They do not establish which workload caused it. A separate bounded metadata read
for older query887e2a23 returned HTTP200 with no row under exact filters; no CPU
attribution is extended to that older failure and no broader fallback was used.

## Diagnostic observer finding and permissible correction

Existing logs establish that the previous metadata observer was accepted, read its
356-row system-log part and hit its5s limit at6.226043s. Cancellation requested
05:26:36.727032, execute error05:26:37.452020; the client had timed out and closed
before the server sent its error, producing a broken pipe. Original observer and
all evidence are preserved. The new separately recorded diagnostic uses10s server,
15s socket,18s wall/32KiB capture; it returned the historical row in0.199s. It is
not an experiment, frozen timeout change, or timeout-fixed proof.

The old buffered header reader also loses returned visibility of partial input
when readline raises. The inactive `proposals/phase2-diagnostic-observation-v1/`
helper preserves each returned byte before the next read. Two meaningful legacy
regressions fail before the fix; all7 focused tests pass on Python3.11/3.12.
No benchmark path imports it. It fixes an observation defect, not CPU contention.

## Pending experiment package — not authorized

`configurations/phase2-cpu-scheduling-readiness-v1.pending.json` retains every
model/prompt/schema/tool/SQL/scorer/data/budget value and contract fingerprint
6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4.
It explicitly denies live authorization and contains0 authorized attempts.
The source-only preflight must refuse execution before services or output access.
The execution commit, config hash and exact proposed invocation are sealed in the
review delivery receipt/comment after the commit is created.

Recommended smallest future experiment: one prospectively declared, bounded,
model-free CPU scheduling control on unrelated synthetic inputs under a documented
quiet-resource context, preserving the same per-query limits. Do not replay the
failed SQL or treat it as benchmark qualification. If the owner instead authorizes
one further Treatment A, first review the exact environment-control record and
new immutable authorization config; preserve one observed outcome without retry.
This package executes neither experiment. Model-free nonbenchmark checks are already within the autonomous authorization; any resource-isolation action still needs a concrete justified scope. Treatment A always requires new explicit authorization.

No arbitrary load/PSI threshold, warm-up, optional stopping or statistical rule is
adopted. The exact nonessential workload to quiesce is not established; no service
was stopped, restarted or reconfigured. Changing VM capacity/affinity, ClickHouse
background pools, logging or priority without discriminating evidence would be
speculative. Diagnosis supports addressing scheduling interference first, not a
particular untested server knob.

## Current gates

Phase2 unqualified, no new Treatment A authorization. Phase3 evaluator acceptance,
Phase4 method freeze and all12 decisions, strong-single/schema parity, comparisons
and held-out access remain separate. No historical rescoring, paid provider,
automatic Codex review, merge or deployment. Original raw evidence stays private;
only sanitized observations, fingerprints and selected timeline facts are public.
