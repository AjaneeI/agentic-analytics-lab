# Independent D01 provenance control specification

Author role: independent control/specification reviewer `/root/d01_independent_controls`; parent executor is the sole implementation integrator. Established from source inspection before candidate implementation, 2026-10-19. Authority: issue #95 comment 6256182861, `aalab-phase3-d01-provenance-v1-preparation-20261018`. This document is an independent proposed test oracle, not an implementation, benchmark result or approval to activate.

## Source inspected and limits

Inspected inactive checkout base `43cf76b0acf64aba4f19eb510af12189b7a4ad04`, root operating/project/decision/architecture records; D01 development task and KPI definition; existing local-worker value extraction and runtime-characterization source/tests (source only); and `work/phase2-scope-proposal/src/evals/system_benchmark/scope_observation_v1.py`.

Existing extraction trusts table occurrence plus returned field names and can retain prior values across calls; population helper deliberately proves only a narrow direct-table predicate and rejects CTEs, not metric lineage. Neither proves genuine numerator/denominator dependence, global ranking or capture authenticity. Historical controls are immutable references. No historical SQL, model, database service, held-out file, resource observation, or statistical simulation was executed for this specification.

## Proposed outcome meaning

- `proven`: supplied claim follows the supported query plan, complete synthetic snapshot and reconciled result, under an independently supplied host-capture trust capability. In this preparation, the capability is expressly a test-fixture authority and establishes offline reference semantics only.
- `contradicted`: available trusted evidence positively conflicts with the claim or required metric/population/binding, e.g. a matching constant in place of a genuine aggregate or a correct rate for the wrong team.
- `insufficient`: a required observation is absent, untrusted, incomplete, unsupported or ambiguous. Unknown syntax is never automatically a false answer. Failed/attempted calls do not count as successful computation.

Reason-code names may differ in implementation; each distinction above must remain inspectable. One mutable/caller-authored dictionary must never be enough to create trusted host provenance. A hash binds bytes only when recomputed from independently resolved bytes; hashes or an `origin: host` field supplied by the claimant are not trust anchors.

## New synthetic ground truth

Construct separately named synthetic rows with unique IDs. All statuses are non-null strings and blocked is exactly integer 0 or 1; no historical seed-42 row is copied. Use active statuses `todo`, `in_progress` and `blocked` as convenient; active membership is solely `status != 'done'`, not status/blocked-label similarity.

| Team | Active blocked | Active total | Completed blocked | Completed total | Active percentage |
|---|---:|---:|---:|---:|---:|
| Amber | 3 | 4 | 0 | 2 | 75 |
| Birch | 2 | 5 | 1 | 1 | 40 |
| Cedar | 0 | 3 | 0 | 0 | 0 |

Total rows 15; total active rows 12; active blocked total 5. Correct winner is Amber, numerator 3, denominator 4, percentage 75, scope `active_work_items`. Compute truths directly from these row definitions, independently of the candidate verifier. Preserve exact rational rates internally; display percentage tolerance is the frozen 0.2 percentage points and is never used to decide the highest team.

## Minimal supported proof grammar recommendation

Use a bounded tokenizer and explicit AST with whole-input consumption; no token-presence regex as proof. A small pure relational evaluator or normalized plan checker is preferable to a general SQL engine/dependency. Explicitly declare AST/CTE/depth/row limits.

1. One approved source identity, optional safe alias; projection and grouping team keys resolve to the original team column.
2. Active predicate equivalent forms: `status != 'done'`, `<>`, reversed literal comparison, `NOT(status = 'done')`, `status NOT IN ('done')`, with harmless parentheses and source qualification. Preserve string literal case. No unproved OR, extra team filter or alias-shadowed status.
3. Binary aggregate metric: `100.0 * SUM(blocked) / COUNT(*)`, equivalent parenthesization/order with floating promotion; `AVG(blocked) * 100` is equivalent under pinned binary/non-null assumptions. SUM/COUNT numerator and denominator must both derive from the same active rows. Optional CASE/count-if alternatives need their own explicit AST/equivalence rule; unsupported alternatives stay insufficient.
4. Bounded acyclic single-consumer CTEs may pass through/project/rename source columns, apply the supported active predicate, or materialize per-team SUM/COUNT and derive percentage. No recursive CTEs, joins, unions, windows, correlated subqueries or source changes in this version. An alias is a binding, never a string replacement. Reject duplicate aliases and shadowed team/status/blocked names if unambiguous lineage cannot be proven.
5. All eligible teams must participate before ranking. Direct full grouped output is supportable. `ORDER BY genuine_unrounded_rate DESC LIMIT 1` is also supportable when the AST proves the full team domain and the independently resolved complete snapshot plus exact terminal result reconcile; do not require every team to be returned if global ordering is actually proven. A team filter, pre-aggregation limit, HAVING cutoff, unproved truncation, ascending sort or sorting on a rounded/literal/unrelated alias cannot establish that proof.
6. Numeric scale 100 is legitimate. Inserting any aggregate in a discarded term, zero multiplier, constant CASE branch or unused CTE does not make a literal final metric data-dependent. A symbolic lineage rule must inspect the expression that feeds the final metric and ranking, not merely collect referenced function names.
7. Keep the verifier inactive and detached from benchmark entry points. A pure offline snapshot supplied to this candidate is not permission to add future verification SQL or reveal evaluator truth to an agent.

## Required controls and independent expected outcomes

### Positive, equivalent and alternative syntax

P01 canonical direct grouped active SUM/COUNT, full results: proven Amber 75.

P02 canonical query with genuine descending unrounded rate and LIMIT 1: proven Amber 75 if complete snapshot and host capture are resolved; missing either becomes insufficient.

P03 each equivalent active predicate in grammar with table qualification, mixed identifier case and harmless parentheses: proven same result. Literal `'Done'` is a different predicate under recorded case-sensitive non-null assumptions; it must not silently become `'done'`.

P04 safe table alias and distinct metric output aliases mapped by explicit contract: proven; alias spelling alone conveys no metric semantics.

P05 bounded active-row CTE plus grouped outer aggregation: proven. P06 aggregate CTE plus outer percentage/ranking projection: proven if included in declared grammar, otherwise insufficient and listed as a remaining valid alternative.

P07 AVG times 100 on binary integer blocked with floating semantics: proven. P08 CASE numerator/count-if alternative: proven only if explicitly supported, otherwise insufficient, never semantically false.

P09 constant 100 scale, harmless multiplication/division reorder and `1.0` promotion: proven if evaluated as equivalent without integer-division defects. Integer-division semantics must be explicitly qualified to the execution dialect; SQLite is only a separately labeled fixture engine.

### Matching answers that do not prove computation

N01 literal team, percentage and scope with successful SELECT: contradicted metric/team provenance even when all values match the synthetic oracle.

N02 `75 + 0 * SUM(blocked)`, `SUM(blocked) * 0 + 75`, unused aggregate CTE, and constant CASE branch: contradicted data dependence; not proven merely because SUM exists.

N03 genuine aggregate with literal `'Amber' AS team`: contradicted team/group lineage, including when Amber is actually highest.

N04 `'active_work_items' AS scope` with absent/wrong active predicate: contradicted population, not supported by label.

N05 blocked count divided by blocked count, all-row count or another team's denominator: contradicted metric even if a specially chosen data set makes its numeric result match.

N06 reversed numerator/denominator: contradicted; no automatic reciprocal/normalization.

N07 correct aggregate after `team='Amber'`, filtered CTE dropping Birch, HAVING threshold, pre-aggregation LIMIT, wrong source, or truncated result presented as complete: contradicted domain when visible; insufficient where unobserved truncation cannot be resolved.

N08 ascending sort/LIMIT1, ORDER BY team, ORDER BY literal or shadowed metric alias: contradicted ranking when lower returned team is proven; insufficient if unsupported syntax prevents semantic determination.

N09 SQL proposed but never executed, attempted/failed call, partial stream, cancelled call, timeout with rows, malformed result: insufficient successful-computation evidence.

N10 runtime query returns correct result but final claimed team/rate belongs to another call: contradicted binding; no fallback to previously accumulated values.

### Binding and trust controls

B01 each independent mutation of query bytes/hash, result bytes/hash, snapshot bytes/hash, configuration bytes/hash, metric version, call ID, execution ID, task ID, source identity or expected commitment: contradicted with field-specific reason. Missing required fields are insufficient.

B02 caller regenerates a perfectly self-consistent envelope and all its hashes: insufficient trust; the resolver must not accept it merely because checksums agree.

B03 strings such as `origin='host'`, serialized HostCapture dicts, copied object IDs or stale capability from another resolver session: insufficient authority or contradicted binding as appropriate.

B04 trusted captured result from call A combined with SQL/snapshot/config from call B: contradicted. Identical result values cannot erase call identity. A failed current call plus prior successful result is insufficient for the current call.

B05 mutation after capture: changed row, result, SQL or config cannot alter an issued immutable capture silently; deep-copy/freeze or recomputation makes this detectable. Shallow frozen dataclass around mutable list/dict is not immutable.

B06 capture status must be successful and result complete; a matching response payload cannot override host failure/truncation flags. Bind snapshot/config to actual trusted host state, not an agent assertion.

### Data perturbations, with independently calculated truths

M01 row permutation: same numerator, denominator and winner, no dependence on row insertion order.

M02 consistent rename Amber→Zulu, Birch→Able, Cedar→Mango: winner Zulu at75; alias and lexicographic ordering cannot override metric rank.

M03 add any completed blocked/unblocked rows: active result remains Amber75. A completed-only team does not become eligible. Do not infer invariance from unchanged stored hashes; update snapshot commitment consistently.

M04 add one active blocked Amber row: Amber4/5=80. Retaining75 must contradict current computation even though former evidence was valid.

M05 add one active unblocked Amber row: Amber3/5=60. Retaining75 must contradict.

M06 add eight active blocked Birch rows: Birch10/13×100=76.923076923..., now exceeds Amber75. A stable Amber claim is contradicted. This is the crucial competitor-dependence control.

M07 duplicate the whole population with distinct row IDs: every numerator/denominator doubles, percentages and winner remain unchanged. Duplicate identity keys, in contrast, are invalid/ambiguous snapshot evidence unless schema explicitly permits them.

M08 add seven active blocked Birch rows: Birch9/12=75 ties Amber3/4. Proposed rule: return exact co-max set; a singular final claim can identify one member only if it does not assert unique superiority. Do not resolve ties through task expected team or source row order. If the future final-answer interface lacks tie/uniqueness fields, report this limitation explicitly.

M09 rounded near-tie independent fixture: Low97/129 and High94/125; percentages≈75.19379845 and75.2 both display75.2 at one decimal; exact winner High because94×129=12126 >97×125=12125. Picking Low is contradicted even though its displayed rate lies within frozen tolerance. ORDER BY rounded displayed rate then lexical name cannot prove High. Ranking uses exact ratios, display matching uses unchanged tolerance.

### Empty, invalid and malformed cases

E01 empty snapshot/all rows completed: no eligible team and no nonzero denominator; answer claim insufficient or contradicted as explicitly classified, never proven0% or an arbitrary winner.

E02 zero active blocked but positive active total: valid0%; distinguish from empty/zero denominator. E03 only one active team: valid global winner if evidence domain complete.

E04 null/missing status, null/nonbinary/boolean/string/NaN/infinity blocked, missing team/identity fields, duplicate IDs, nonfinite returned/claimed numbers, duplicate output aliases/teams, duplicate result rows and structurally malformed records: explicit invalid/insufficient evidence. Never silently coerce or drop invalid rows to manufacture a valid denominator. A finite matching rate cannot rescue an invalid source snapshot.

E05 missing numerator/denominator output columns need not fail if the declared AST, complete snapshot and captured result establish them independently; missing final team/rate mapping does fail. Extra unrecognized fields cannot stand in for required evidence.

E06 result missing eligible rows can be valid only when the supported query plan explicitly orders/limits the complete population correctly; unexplained truncation is insufficient. Duplicate output teams or rows cannot count as independent observations or establish ranking completeness.

## Independent review checklist for the candidate

Inspect exact candidate commit/tree, diff and imports. Verify inactive contract is used rather than decorative, expected source/config pins come from independent verifier input, hashes are recomputed, captured objects are deeply immutable, source rows are validated, AST consumes all tokens, aliases resolve by lexical scope, and proof checks symbolic dependencies plus perturbed numerical behavior. Count false acceptance separately from supported-valid false rejection and documented unsupported alternatives.

Run only bounded new synthetic tests after side-effect inspection; record actual command/interpreter, results and source hashes. Never run historical characterization script or broad discovery. Preserve original author red/green evidence. Tests using SQLite/mocks prove offline behavior only. A source-backed independent review does not establish authentic live host-capture integration or general SQL completeness.
