# ClickHouse 404 diagnosis and inactive fix proposal v1

**Root cause confirmed from existing server logs. Candidate not activated.
No Treatment A rerun, model call, failed-SQL replay, or frozen-method change.**

## Diagnosis

The preserved client error was `HTTP Error 404: Not Found`, with execution ending
at `2026-10-18T00:12:12.057710Z`. Unlike Docker stdout, the existing server's
`/var/log/clickhouse-server/clickhouse-server.err.log` retains the error:

- At `2026.10.18 00:12:11.983237`, query ID
  `d6e97785-4a0d-4e9c-ae5a-2590c536f194` failed with ClickHouse code **47**,
  `UNKNOWN_IDENTIFIER`: unknown identifier **snapshot**.
- The generated query used the correct qualified table and active-work filter,
  but also added `WHERE snapshot = 'seed-42'`.
- The same query ID appears again in `DynamicQueryHandler` at 00:12:11.989978.
  These are two log records for one failure, not evidence of a second attempt.
- A separately classified, authenticated read-only **DESCRIBE** at
  `2026-10-18T00:22:11.496795Z` returned 13 columns and no `snapshot` column.
  The pinned generator's `fields` list independently corroborates those names;
  seed 42 is its generation parameter, not a row-level column.

This is a model-generated schema error, not evidence of a missing HTTP endpoint
or table. Preflight's count query could pass because it did not use the invented
column. The existing worker tool description named the table and metric alias
but supplied no column schema; its two-call task budget left no additional call
for schema discovery when gathering the required structured and policy evidence.
The transport caught HTTPError as a generic exception and discarded its body,
making the client-only record insufficient for diagnosis.

The log establishes what failed. It does not reveal hidden model reasoning or
prove which wording caused the invented column. Concurrent CPU simulation is
not implicated by this server exception. No query was corrected and replayed.

The failed run remains `execution_error`, with no score. Its original manifest,
traceback, checksum inventory and previous report were not edited. The newly
recovered evidence is a dated addendum, not a replacement for the original record.

## Concrete candidate

`candidate.patch` is an **inactive** patch against immutable
`5f36bfd4633c7b80dccefb7179da0c46fbb918f4`. `manifest.json` pins the patch and
exact before/after source hashes. It changes only:

1. `local_worker.py`: append the verified 13-column schema/types to
   `query_clickhouse`'s description; state that the seed-42 snapshot is provenance,
   not a column/filter. No reference answer, expected team/rate, SQL example or
   oracle answer metadata is supplied.
2. `clickhouse_readonly.py`: retain HTTP status and parsed server code/error name
   in a RuntimeError subclass. Read at most 8,192 error-body bytes; expose only
   identifiers in its message, not raw SQL/body, URLs or credential strings.
   Preserve failure on unreadable bodies. No retry or SQL rewrite is introduced.
3. Six deterministic regression tests for schema metadata delivery, error
   identifiers, bounded/failed reads, unchanged successful SQL/limits and
   fail-closed table scope. HTTP and model responses are controlled test doubles.

The active `src/`, task/reference data, scorer, policy corpus, SQL validation,
model settings, routing, budgets and original capture runbook on this proposal
branch remain byte-identical to the pin. Only a disposable offline copy receives
the patch during verification. No default entry point selects the candidate.

Supplying schema metadata changes the model-visible tool contract; error
identifiers change failure observability. Those are **proposed versioned changes
requiring owner approval before activation**. They are not silently applied to
the frozen experiment. Schema context addresses the observed information gap,
but deterministic tests cannot prove that a future model will avoid hallucination
or pass SB-D01. A future run, if separately authorized, is new versioned evidence.

## Verification

Run `python3 -m unittest tests.test_phase2_fix_proposal -v` from this branch.
The test checks exact baseline hashes, applies the patch in a temporary copy,
checks candidate hashes and runs all six candidate tests with live network
prohibited. It does not execute Treatment A, Ollama, ClickHouse or the benchmark.

Preserved red/green evidence: against the untouched pin, four of six candidate
tests fail for absent schema/diagnostic behavior and two existing-boundary tests
pass. With the patch, all six pass. The complete offline candidate suite passes
296 tests on Python 3.14.7 after using this proposal's reviewed STATUS metadata
and an isolated Git test repository. No frozen test expectation was weakened.

The original pin also has a pre-existing documentation-check failure:
`test_context_check_script_passes` reports a missing last-reviewed marker in
STATUS.md. `baseline-context-failure.txt` preserves that result. This proposal's
dated status addendum supplies that required marker; the pin is unchanged.
Initial scratch full-suite failures caused by an incomplete test copy/missing
Git metadata were corrected in the disposable test environment, not by changing
runtime code or tests.

## Review and activation decisions

Review the recovered server record, schema diagnostic, patch and exact manifest.
If approved, name `phase2-runtime-schema-v1` (or an explicitly revised version),
apply the patch on a new branch from the recorded base, and record a new immutable
execution commit and contract fingerprint. Keep the failed run and scorer version
separate. Approval to apply this patch is **not** approval to rerun Treatment A.

Any further live attempt needs explicit owner authorization naming the new pin,
permitted invocation count, exact task, unchanged scoring/data/security/budgets,
and required failure evidence. No merge, activation, retry, guard relaxation,
data-column addition, reference change or rescore is authorized by this proposal.
