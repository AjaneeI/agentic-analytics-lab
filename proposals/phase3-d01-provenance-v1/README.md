# phase3-d01-provenance-v1 — inactive offline candidate

This proposal checks a bounded **D01 aggregate/ranking provenance predicate** on separately named synthetic captures. It does not replace the frozen scorer, qualify Phase2, accept Phase3, select a Phase4 method, activate a benchmark path or authorize any live attempt.

Owner authority: [issue95 preparation package](https://github.com/AjaneeI/agentic-analytics-lab/issues/95#issuecomment-6256182861), reaffirmed directly in the executor chat. Source base: PR98 `43cf76b0acf64aba4f19eb510af12189b7a4ad04`. PR103 `f65b3af5f84aee7fb8b86ea0977669a8f65729f8` supplies the scope-lexer precedent; this proposal preserves string literal case and whole-input consumption while adding explicit AST/lineage checks. PR117 `da6fcf1be815d42816167cb6a88ba48ffd89bcdf` establishes why matching source hashes alone cannot prove metric computation or authority. Neither proposal is activated or imported.

## Files and entry points

- `contract.json`: versioned inactive evidence contract and reason codes.
- `sql_proof.py`: bounded tokenizer, SELECT/CTE parser and pure relational interpreter; no SQL connection or runtime imports.
- `verifier.py`: independently supplied capture binding, source validation, query/metric/rank reconciliation and three-way verdict.
- `test_verifier.py`: newly authored synthetic rows, explicitly in-memory SQLite fixture execution and deterministic assertions.
- `run_validation.py`: inspected unit entry point plus named outcome matrix, with network/process/file-database/runtime-import denial guards.
- `PLAN.md`: implementation plan, authority and scope rulings.
- `validation/`: pinned source, test/control and review receipts. Retained original red/green logs are local delivery evidence, not historical experiments.

Run only the scoped controls from the checkout root, choosing a NEW output path:

```sh
python3 proposals/phase3-d01-provenance-v1/run_validation.py --output /tmp/d01-validation-new.json
```

The output path is explicit and refuses overwrite. No default benchmark bank, SQLite file, service, model or failed SQL is loaded. Broad repository test discovery is intentionally excluded: existing entry points can replay historical characterization SQL or expanded statistical simulations. Main-only hosted CI is not claimed for this stacked draft.

## Trusted host boundary

The API is `verify(claim, *, resolver, expected)`. **Only claim is claimant-controlled.** The resolver and expected commitment must be held independently by the host/evaluator; they must never be reconstructed from a model response. A resolver returns an immutable `HostCapture` from its own execution registry. The independently expected `capture_ref` pins the same nonserializable object identity, with execution/call/task/metric/config/snapshot/query/result/contract commitments. A dictionary containing the right fields or checksums cannot supply that identity through the claim API.

`capture(...)` freezes host-provided query/result/snapshot/config bytes as immutable strings. It does not execute SQL or authenticate its Python caller. In this proposal it is called only by the **test-only FixtureHost after actual new in-memory SQLite execution**, with deliberate corruptions clearly labeled in negative controls. Original inputs can be mutated afterward without changing the issued capture. `binding(record)` is a host helper, not a way for agent evidence to authenticate itself. A malicious Python caller that controls both host arguments is outside this trust boundary; object identity is not cryptographic attestation or a process sandbox.

**Only origin `synthetic_sqlite` can receive proven in this candidate.** `live_host`, agent origins, serialized envelopes, absent/failed/incomplete captures and unsupported origins remain insufficient. Every result sets `live_qualified=false`. No live resolver/capture adapter is implemented, and even proven means conditional offline computation proof within the declared synthetic fixture trust boundary. It does not establish live host provenance.

A future runtime integration would require its own reviewed host-owned resolver and complete snapshot/result evidence interface, independently pinned configuration and capture source, and activation approval. This proposal adds no verification SQL, model/tool calls, prompt fields or budgets and exposes no evaluator truth to an agent under test.

## What is proved

The input snapshot must be complete, contain unique integer IDs, nonempty team/status strings and integer blocked values in `{0,1}`. Boolean, null, missing and nonfinite source values are not coerced. Active membership is exactly case-sensitive `status != 'done'`; historical A01 all-work semantics are unchanged.

The parser consumes the complete input, resolves lexical source/column aliases and at most three acyclic CTEs. Projection/filter CTEs can retain or rename source columns; aggregate CTEs can retain genuine numerator and denominator expressions for later arithmetic. Team grouping must originate in the original team column. A polynomial proof checks the final percentage expression as `100*N/D` where N and D derive from the SAME active population. Decorative aggregates, zero multipliers and matching constants cannot establish that identity. Division cannot hide an unsafe raw-blocked or numerator denominator through cancellation; mixed ungrouped source columns remain unsupported.

Complete per-team results or a genuine unrounded descending-rate query over the complete domain can establish ranking, including LIMIT1. A limit that retains all grouped rows also preserves full output. CTE limits remain unsupported; no plan can silently use a hand-picked team/subset. The complete trusted snapshot provides exact rational counts for every eligible team. Ties are exact co-max sets; a singular selected member is allowed only with `unique_winner=false`. A claimed team must occur in THIS capture's returned rows; a tied member absent from a LIMIT1 result is not borrowed from another call. Rounded near-ties never decide the winner.

Query result fields and values must reconcile with the pure interpreter. The `1e-12` absolute/relative comparison is floating computation reconciliation, not a winner or scoring tolerance. Claimed percentage uses the preserved **0.2 percentage-point tolerance**, without converting invalid types. A false winner cannot pass because its rounded rate is close. Zero blocked with a positive denominator is distinct from empty/no active population.

Unquoted ASCII output aliases resolve case-insensitively under the fixture SQL dialect; original capture bytes remain untouched and colliding labels are rejected. Quoted case-sensitive identifiers stay unsupported. Oversized/nonfinite numbers and malformed capture/config fields produce explicit verdicts rather than exceptions. Serialized capture inputs are capped at2MiB locally before parsing; this offline bound does not alter any benchmark/model/server budget.

## Unsupported cases and scientific limits

This is intentionally not general SQL validation. Valid `TOTAL`, COUNT_IF/countIf, arbitrary CASE variants, nested/recursive WITH, limited CTEs, subqueries, joins, unions, windows, HAVING, post-aggregate filters, SELECT*, quoted mixed-case output aliases, ORDER BY expressions rather than selected aliases and rounding functions may remain insufficient. They are not automatically semantically false. Unknown population predicates that happen to select the same synthetic rows remain insufficient without an equivalence proof; an observed different population is contradicted. Unsupported controls are reported separately from supported-valid false rejections.

The interpreter uses exact rational division for the declared percentage computation. The actual fixture engine is SQLite: integer-only division or other dialect differences can produce a captured-result contradiction. Floating promotion/AVG controls are supported; SQLite success never establishes ClickHouse behavior, integer-division semantics, server settings or live capture integrity. All known historical SQL and original outcomes remain immutable references and were not executed/rescored.

This predicate does not validate the full natural-language answer, causality, KPI retrieval/authority, all nine original evaluator defects, A01 population policy or C02 synonym policy. Those remain separate gates. An inactive valid alternative may still need a future capture/interface amendment; this proposal does not supply one automatically.

## Evidence and decision

Acceptance requires no false acceptance in the named negative/insufficient controls, no rejection among explicitly supported valid controls, explicit unsupported-case reporting, independent exact-head review and unchanged preexisting source/evidence blobs. These are candidate preparation criteria, not scientific phase acceptance.

The five-hour maximum window starts2026-10-19T17:36:19Z (13:36:19 Eastern), implementation stops22:06:19Z and closeout ends22:36:19Z. No enforceable whole-chat timer exists in the exposed host interface; actual time and bounded commands are recorded. Work stops earlier when this package is complete.

**Next owner decision after review:** accept/revise/defer the inactive contract and proposed future trusted-host capture boundary. Activation, live validation, scorer replacement and any new experiment remain unauthorized.
