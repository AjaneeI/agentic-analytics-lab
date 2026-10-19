# Inactive D01 provenance candidate implementation plan

**Goal:** prove or decline bounded D01 computation provenance on separately named synthetic captures, without changing the active benchmark.

**Architecture:** A standard-library bounded SELECT/CTE parser tracks source columns, population and aggregate-expression lineage. A pure verifier checks that proof against a complete independently supplied host snapshot and capture bindings. Trusted-host capture resolution is a separate host-only interface: no agent-envelope deserializer, active runtime integration or live capture adapter is provided. All executable controls are new in-memory SQLite fixtures, explicitly not ClickHouse evidence.

**Spec:** issue95 comment6256182861, authorization aalab-phase3-d01-provenance-v1-preparation-20261018; independent control specification SHA25687428066f569c711444d7fc45ebc995d4b6340ddf022098b547aa78bc4a9f06c.

## Constraints

- Original scorer/task/reference/corpus/generator/runtime/authorization sources remain unchanged. Existing claimed-rate tolerance stays0.2 percentage points.
- All additions remain under this inactive proposal; only a status note may change outside it.
- No live SQL/model/service/resource/held-out work, historical query replay/rescoring, statistical change, paid fallback, automatic review, activation or merge.
- Actual start2026-10-19T17:36:19Z; implementation cutoff22:06:19Z; absolute deadline22:36:19Z. No whole-chat enforced timer available; use bounded commands and explicit clock checks.
- Main agent is sole code integrator; independently specified controls and a separate exact-head reviewer supply independent checks.

## Review focus

1. A literal or decorative aggregate must never gain genuine numerator/denominator/rank provenance through coincidental values.
2. SQL aliases and bounded CTEs must preserve source/scope lineage without shadowing or hidden row restrictions.
3. Snapshot/query/result/config/call identity must refer to the same successful complete host capture; a self-report must stay insufficient.
4. Ties use exact unrounded ratios; near-ties cannot be resolved from rounded percentages.
5. Unsupported valid SQL is insufficient rather than a false semantic contradiction; no live provenance can be claimed from fixture success.

## Tasks

- [ ] Contract and red controls: contract.json defines supported grammar/trust interface/reason codes; test_verifier.py and fixture_capture.py specify synthetic expected results independently before implementation. Run them against a declining baseline and retain meaningful failures.
- [ ] Minimal proof: sql_proof.py implements bounded tokenization, expression/SELECT/CTE parsing and exact aggregate lineage; verifier.py exposes verify(claim, *, resolver, expected) with three-way outcomes. No SQL execution in these modules.
- [ ] Green controls: canonical/equivalent/alias/CTE positives; literals/decorative aggregates/wrong denominator/population/ranking; perturbations, ties/near-ties, missing/nonfinite/mismatched/stale evidence. Inspect each test entry point and retain result/reason counts.
- [ ] Inactivity and review: independently review exact committed candidate, test adversarial gaps, apply in-scope red/green corrections, compare all preexisting Git blobs and selected source hashes; no broad test discovery.
- [ ] Delivery: one draft PR, exact hashes/validation/review and unsupported cases; reconcile issue95/Notion/Asana only after GitHub evidence. Phase gates remain unchanged.

## Rulings

- The owner explicitly approved the entire preparation/implementation/review package and direct autonomous pickup. The skill's extra plan-approval pause is superseded; no repeated approval is requested.
- Base PR98 at43cf76b is the smallest relevant Phase3 audit lineage. PR103 scope lexer and PR117 lineage validator are inspected/referenced but not activated or imported; neither proves aggregate/ranking/host authenticity, so copying them as a proof engine would be unsound.
- Full captured snapshot and query-plan proof can support ORDER BY genuine unrounded rate DESC LIMIT1. A hand-picked team or truncated domain cannot.
- Broad suite discovery is excluded by the approved source/side-effect boundaries. Only inspected new synthetic tests and preservation checks run.
