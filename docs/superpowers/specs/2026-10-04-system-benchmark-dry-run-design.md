# System Benchmark execution contract and dry-run rehearsal

Scope: the October 4 conversation-approved model-free milestone after merged
PR C (#68 / issue #66). This narrower rehearsal precedes the live routing/worker
phase in the September 24 roadmap; it does not authorize models or held-out work.

## Decision

Use the existing seven development cases with trusted scripted adapters, actual
repository-local policy retrieval, and an explicitly labelled in-memory SQLite
replay of the unchanged seed-42 CSV. The replay supports only two exact,
read-only aggregate queries after the existing SQL guard; it never contacts
ClickHouse. This proves execution/record/scoring plumbing, not engine parity,
latency, route inference, model quality, or hostile-code containment.

Rejected alternatives: canned evidence could copy expected values and pass
circularly; live ClickHouse plus agents would conflate integration and behavior
and introduce unnecessary service/credential dependencies at this milestone.

## Trust and record boundary

Only case ID, request, and allowed tools reach the scripted adapter. References,
expected values, family, expected route, and forbidden/required answer metadata
stay evaluator-side. Case-specific scripts are explicit oracle scaffolding, NOT
natural-language routing. Trusted adapters receive an allowlisted gateway; they
cannot supply the tool-call observation used by the scorer. This Python interface
is not an OS sandbox for arbitrary malicious Python plugins.

The gateway enforces task + capability tool allowlists, strict argument types,
read-only SQL and exact replay queries, at most eight dispatches, and bounded
request/result sizes BEFORE backend dispatch. Every attempt has a stable ordinal,
arguments, outcome, code, result snapshot and SHA-256. Rejected/failed calls are
not counted as successful tools, and exceptions are redacted to stable codes.
Worker mutation of returned dictionaries must not alter captured evidence.

A record contains schema version, development-only mode, case ID, scripted route
and route origin, normalized existing response envelope, explicit answer values,
trace, the existing PR C score, separate execution/grounding checks, aggregate
outcome, and reason codes. Answer values are worker output; grounding checks must
find those values together in a successful evidence row at the correct scope.
Citations (including handoff citations) must come from actual successful returns.
The prose dimension remains bounded literal checks, not semantic understanding.

## Rehearsal and provenance

Seven known-good controls plus explicitly labelled failure injections exercise
missing/forged/wrong-version citations, omitted and unnecessary handoff, blocked
tools/SQL/arguments, missing calls, wrong values, scope mismatch, and tool errors.
Faults are not benchmark tasks and do not enter a model success denominator.
Each negative must fail with its predeclared reason; unrelated failures cannot
count as detecting the injected defect. No model calls, no held-out loading.

Canonical JSON omits timestamps, elapsed durations, machine paths, and Python
version. Include sorted content hashes for all defining inputs/implementation
and the generated CSV. Repeated executions and supported Python versions must
produce byte-identical records. Verification logs keep environment details apart.
The CLI writes stdout or a new (exclusive-create) output file, never overwrites
input evidence. Invalid fixtures fail before adapter invocation.

## Reference correction exposed by real data

The unchanged generator yields Data 29/139 = 20.8633% over ALL work items, but
8/45 = 17.7778% over ACTIVE items (status != done). PR C's SB-D01 combined the
all-item 20.9% target with an active-work policy. Correct ONLY SB-D01's development
request, expected value (17.8, same tolerance), and explicit scope. Keep SB-A01's
all-item calculation and every frozen Q1-Q6 file unchanged. Record both counts
in the rehearsal and test the correction against generated data, not itself.
No agent is involved in this reference correction; do not weaken the grader.

Bounded PR C defects revealed by negative tests may be fixed with regressions:
extra wrong-version citations must not pass merely because the right version is
also cited; booleans must not pass numeric expectations; huge integers must fail
safely rather than overflow. Do not rewrite the frozen microbenchmark scorer.

## Integration and cost

No Codex task/review, new paid dependency, external database, or credentials.
Ordinary deterministic CI/CodeQL is allowed. PR #68's ready transition DID trigger
a Codex review; absence of an immediate comment was not a safe cost check.
Keep this candidate isolated (or draft) and do not mark ready without a verified
no-Codex trigger path. Never weaken branch protections. Publish evidence first;
a tested candidate and a merge are different milestones.
