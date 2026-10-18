# Runtime SQL scope observation v1 — inactive experimental amendment

Status: **proposed for owner review, not activated for an experiment**. No new
Treatment A or live model call has occurred. The exact schema-v1 activation is
preserved separately in PR102; PR101 and the original failed run remain intact.

## Problem and proposed boundary

The frozen SB-D01 task expects `scope=active_work_items`. The current runtime
copies this field from query rows, which rejects legitimate active-population
SQL without a manufactured label and accepts unsupported labels. This amendment
observes population from the actual successful SQL call instead. It changes
runtime observation behavior, so it has a separate version and fingerprint;
it is not silently included in the approved schema-only configuration.

After a successful, nonempty query, the runtime discards any returned `scope`
label. A narrow token-aware recognizer supplies `active_work_items` only for a
single direct-table SELECT with exactly one supported active predicate:
`status != 'done'`, `status <> 'done'`, `NOT(status = 'done')`, or
`status NOT IN ('done')`. Direct aliases and quoted identifiers are supported;
string literal case is preserved. Optional simple team grouping, ordering by
returned rate/team, and a numeric LIMIT must be fully consumed. SELECT aliases
which could shadow status are unknown. Failed queries propagate unchanged;
empty or unknown queries produce no scope observation and clear stale scope.

CTEs, joins/subqueries, extra filters, OR, PREWHERE/HAVING, set operations,
comments, terminal semicolons, unsupported ordering, and other SQL forms remain
**unknown**, including valid alternatives. The runtime does not repair SQL,
requery, retry, prompt the model differently, or infer from task expectations.
Unknown scope retains the frozen scorer's existing missing-value outcome.

## Frozen criteria and remaining limitations

The scorer, development task/reference, policy corpus, numerical tolerance,
seed-42 generator, model configuration, tool metadata, SQL safety guard, evidence
budget and step budget remain unchanged. The query tool JSON is byte-equivalent
to approved schema-v1. This is scope observation only: it does not prove the
metric expression, denominator, ranking, or natural-language explanation.
For example, a fabricated literal percentage can still pass the unchanged
lexical/value scorer even with a genuine active filter. This remains a Phase 3
grader defect; this amendment does not claim overall evaluator validity or
permit an architecture comparison. Unsupported valid alternatives are recorded
for owner adjudication, not relabeled invalid or hidden.

## Validation and approval required

Regression tests were observed failing on the schema-only runtime before the
candidate was implemented. Tests cover successful canonical/equivalent/aliased
SQL, missing or fabricated labels, uppercase literal, OR bypass, extra filters,
CTE/set operations, alias shadowing, unsupported suffixes, empty rows, and query
errors. All checks are offline; no ClickHouse/model calls or held-out data.
Independent executed-SQL controls and review are stored alongside this document.

The owner must approve or revise this exact observation amendment before a new
execution configuration can set its authorization gate to approved. Approval
would qualify the combined versioned configuration for the already-authorized
single bounded standalone Treatment A only after fresh pin/model/schema/data,
offline and passive-capture preflight checks pass. No retry follows any outcome.
Strong-single adapter implementation and independent schema parity remain future
comparison prerequisites, not a prerequisite for this standalone experiment.

The independent report pins its comparison baseline to schema activation `d8fcee6`,
not the moving evidence-branch HEAD. Source hashes identify the candidate runtime
and reproducer; evidence-only commits do not alter the observation fingerprint.
Full suites pass 310 tests on Python 3.11, 3.12 and 3.14.
