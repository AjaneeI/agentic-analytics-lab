# System Benchmark dry-run rehearsal v1

**Evidence class:** scripted development integration, not agent performance.  
**Date:** 2026-10-04. **Tracking:** #71; parent #49.  
**Source base:** `6982f6753bdbcbc4cb547a3db0e1695cd87a2c72` (merged PR C).  
**Candidate state:** implementation and sandbox verification complete; not merged.

## Verified result

Seven of seven scripted controls passed. Fourteen of fourteen deliberately
corrupted executions failed with their predeclared reason. A test also substitutes
an unrelated failure for every execution and confirms it counts as zero detected
faults. These are 7 controls + 14 negative controls, NOT 21 evaluated agent tasks.

The full suite passed **278 tests** on Python **3.11.16, 3.12.14 and 3.13.13**.
The focused System Benchmark suite passed **130 tests**. Compilation, the project
context checker, and whitespace checks passed. Cross-process hash-seed tests and
three independently executed Python-version rehearsals produced byte-identical
JSON. Required hosted CI/CodeQL results are recorded against the published commit
in the PR/issue checkpoint, not inferred from these sandbox results.

Canonical report: `rehearsal.json` (53416 bytes).  
SHA-256: `001afe68932bb95fd3f623b0012b01f326d4c89b1f922e42f3c165d47108efc7`.

## What actually executed

Policy evidence comes from the real repository-local `retrieve_policy` function.
Structured evidence is computed from all 500 rows of the unchanged seed-42 CSV,
using two allowlisted read-only aggregate queries in in-memory SQLite. The logical
tool retains its existing `query_clickhouse` capability name; the result explicitly
identifies **`sqlite_seed42_replay`**. No live ClickHouse server was contacted.
This is not a claim of ClickHouse engine parity or live-database portability.

Each attempt records its ordinal, normalized arguments, success/rejection/failure,
canonical returned evidence, and result hash. Rejected requests never reach the
backend. Worker-declared answer values and citations are checked against successful
backend returns; mutating a returned Python dictionary cannot rewrite the trace.
Handoff citations are checked too. Reference metadata stays evaluator-side.

## Negative controls

| Deliberate defect | Required reason | Result |
| --- | --- | --- |
| missing_evidence | `missing_required_evidence` | detected |
| wrong_policy_version | `wrong_policy_version` | detected |
| extra_wrong_policy_version | `wrong_policy_version` | detected |
| fabricated_source | `unsupported_evidence_source` | detected |
| omitted_handoff | `required_handoff_omitted` | detected |
| unnecessary_handoff | `unnecessary_escalation` | detected |
| forbidden_tool | `forbidden_tool` | detected |
| write_sql | `sql_rejected` | detected |
| invalid_arguments | `invalid_tool_arguments` | detected |
| missing_tool | `missing_required_tool` | detected |
| wrong_values | `ungrounded_answer_values` | detected |
| scope_mismatch | `scope_mismatch` | detected |
| tool_error | `tool_execution_failed` | detected |
| forged_handoff_evidence | `unobserved_evidence_ref` | detected |

## Reference defect found before model execution

PR C's SB-D01 mixed an all-item expected rate with an active-work policy:

| Population | Data blocked / total | Computed rate |
| --- | --- | --- |
| All work items (SB-A01 unchanged) | 29 / 139 | 20.8633093525% |
| Active work, status != done (SB-D01) | 8 / 45 | 17.7777777778% |

The initial rehearsal passed six controls and failed SB-D01 with
`structured_value_mismatch`. Its scope-mismatch negative was also not detectable
under the old underspecified expectation. Only SB-D01's development request,
expected percentage (17.8, original tolerance 0.2), and explicit active scope were
corrected. The generator, policy corpus, SB-A01, frozen Q1–Q6 and accepted historical
results were NOT changed. This is an oracle/reference correction, not model tuning.

Three additional PR C scorer defects were reproduced as failing tests before their
minimal fixes: an extra wrong policy version alongside the right version, bool/int
coercion, and overflow from enormous observed integers. The frozen microbenchmark
scorer was not modified. Self-review then reproduced and fixed missing-output reason
codes, unexpected backend evidence fields/types, and malformed whole-suite preflight.

## Reproduction

From a checkout of the candidate:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests/system_benchmark -v
python3 -m compileall -q src tests
python3 scripts/check_project_context.py
python3 scripts/run_system_benchmark_dry_run.py --include-faults > /tmp/rehearsal.json
cmp experiments/system-benchmark-dry-run-v1/rehearsal.json /tmp/rehearsal.json
```

The CLI also accepts `--output NEW_FILE`; it refuses to overwrite an existing file.
The report fingerprints every defining contract, fixture, scorer/harness/tool module,
policy file, and the generated CSV. Timestamps, elapsed time, host paths and Python
version are deliberately excluded from canonical bytes. Environment/test metadata
belongs in verification logs, not deterministic event records.

## Boundaries and limitations

No model calls, held-out cases, paid inference, LLM judge, or hidden-reasoning fields.
Scripts deliberately select by case ID and cannot demonstrate route inference or
unseen-task generalization. Prose checks remain bounded literals; they are not a
universal semantic correctness judge. Trusted Python adapters/backend implementations
are NOT an OS sandbox for malicious plugin code. The call limit bounds gateway
activity; this is not a process time limit for arbitrary untrusted Python adapters.

Frozen questions retain SHA-256
`0dc047fbc378f0cf75f1c488e92fcb18dddcbfe976c79b1f16281e4b428654d1`.
The original microbenchmark scorer, dataset generator, policy retriever, read-only
ClickHouse tool and agent/model code are byte-identical to the source base.

**Cost correction:** PR #68's draft-ready transition did start an automatic Codex
review (GitHub comment 5985148807), contrary to the earlier premature no-review claim.
This candidate does not repeat that transition. No Codex task/review is invoked by
this rehearsal; historical account credit usage is not verified. Keep integration
separate from implementation and do not weaken branch protection to avoid a trigger.
