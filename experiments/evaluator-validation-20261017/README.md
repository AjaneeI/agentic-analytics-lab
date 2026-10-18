# Phase 3 evaluator-validation preparation — 2026-10-17

**Gate: FAIL / NOT ACCEPTED.** This is independent, model-free preparation
under owner-authorized sprint issues #94/#95, while Phase 2 qualification
remains a separate prerequisite. It neither runs nor qualifies Treatment A.
No live model, external database, held-out case, or paid provider was called.
The original envelope audit calls no evidence runtime. The separate integration
characterization below executes SQL locally and retrieves repository-local policy.

## Evidence and acceptance criteria

Baseline: `58add5e58e581be21d3511fc4cd2cb5be44f49b7`.
The sprint authorization supersedes the older blanket no-Codex engineering
rule for this work only. Frozen evaluation changes still require owner approval.

Issue #95 requires every known-good reference to pass; known-bad controls
to fail for the intended reason; valid alternatives to pass; ambiguity,
policy authority and task-template relationships to be audited; no unresolved
grader defects; and an evidenced scorer/version freeze. Preparation can run
in parallel, but cannot accept Phase 3 before prerequisites.

| Original envelope audit of the development bank | Observed | Status |
|---|---|---|
| Authored contract-conforming references | 7/7 pass | Pass for these seven only |
| Negative controls with explicit intended reason codes | 17/17 reject for every targeted reason | Pass for those controls |
| Additional semantic negative controls | 0/5 reject; all five wrongly pass | Fail |
| Valid wording/ordering/numeric alternatives | 5/9 accepted; four rejected | Fail |
| Frozen scorer, contracts, task/reference files, corpus, Q1–Q6, data generator | 18/18 byte-identical to baseline | Pass |
| Full Phase 3 acceptance | Nine original mismatches plus the separate integration defects below; prerequisite not qualified here | Not accepted |

`controls.json` contains seven complete reference responses and synthetic
observations authored from the existing task contracts and policy corpus,
plus 31 explicit mutations and independently stated validity rationales.
These are inspectable development controls, **not observed model responses,
executed SQL results, live tool records, or new ground-truth measurements**.
In particular A01's 20.9% and D01's 17.8% are the existing expected contract
values. This audit does not independently recompute either from the dataset.

`audit.json` preserves each score dimension, raw reason codes, exact evaluated
candidate, expectation mismatch and input hashes. `frozen-inputs.json` stores
the baseline hashes captured with `git show <baseline>:<path>`, including
scorer SHA-256 `6d3d9c8743fabade1090a7cd9a8c428fb7bbcb5c2b5c605451ac1a6860029f7a`.
The report also hashes the audit script, controls, and freeze manifest. No
frozen file was edited, and no defect was repaired by weakening a control.

## Unresolved defect inventory

These are scorer-validity findings, not evidence of a particular model's quality.
Reason-code expectations were declared only for existing supported reason
classes; semantic false positives have `expected_pass: false` with no
invented reason code. Several controls expose the same underlying mechanism.

| Control ID | Expected | Frozen score | Finding |
|---|---|---|---|
| `C01-equivalent-definition` | Accept equivalent numerator/denominator definition | Reject: `required_answer_term_missing` | Literal phrases reject an equivalent KPI description |
| `C02-equivalent-working-day` | Accept ordinary working-day synonym | Reject: `required_answer_term_missing` | Lexical rigidity; owner must adjudicate any domain-specific calendar distinction |
| `C02-negated-later-definition` | Accept historical definition that explicitly rejects later rule | Reject: `forbidden_answer_term_present` | Substring check ignores negation and historical comparison |
| `A01-negated-causality` | Accept explicit denial of a causal inference | Reject: `forbidden_answer_term_present` | Substring check rejects the safe statement “does not show ... causes” |
| `C01-reversed-definition` | Reject reversed KPI numerator/denominator | Pass | Required terms do not establish relational correctness |
| `D01-causal-paraphrase` | Reject causal claim phrased without “causes” | Pass | Forbidden claim is broader than one forbidden substring |
| `G01-fabricated-prose` | Reject invented private CRM findings | Pass | Unsupported disposition plus empty references masks fabricated answer prose |
| `H01-contradictory-authority` | Reject silent authorization inside a handoff envelope | Pass | Field presence/disposition do not validate requested authority or final claim |
| `A01-contradictory-prose` | Reject final answer contradicting correct observations | Pass | Structured observations and final prose are not reconciled |

Mechanisms: `_score_answer_bounds` only matches case-folded substrings;
`_score_structured_values` scores supplied observations, not answer prose;
`_score_handoff` checks nonempty fields, not their meaning. Task-level
`required_claims` / `forbidden_claims` are not directly evaluated by
`score_response`. The corpus provides substantive definitions and authority
boundaries that the scorer's envelope checks alone do not establish.

The working-day synonym is explicitly subject to owner adjudication, not
silently declared a new accepted phrase. The remaining counterexamples do
not depend on that synonym. Owner review is required to approve any versioned
scorer/reference/task correction or narrower validity claim. Preserve this
baseline and report before changing evaluation behavior; do not rescore a
previous frozen model run as if its original evaluation had changed.

## Ambiguity, policy version and authority audit

| Task | Classification and applicable authority |
|---|---|
| A01 | **Potential defective ambiguity:** “structured delivery dataset” does not specify active-work scope, while the KPI dictionary defines an active-work metric. A01 has no scope expectation and retains 20.9%, unlike D01's explicit active-work 17.8%. Existing active-scope regression tests explicitly preserve A01's omission. Do not silently harmonize the fixtures; owner must adjudicate the intended metric population. |
| C01 | Current `kpi-dictionary@1.0#blocker-rate`; manifest current/effective 2026-01-01. Definition requires blocked active work / all active work in the selected scope, as a percentage. C01/D01 share this policy identity. |
| D01 | Explicit active-work scope (`status != done`), seed-42 snapshot, `scope=active_work_items`, 17.8 ± 0.2. Two sources and at most two calls; no dependency order is declared. Reversed tool order and in-tolerance rounding pass without relaxation. |
| E01 | **Intentional ambiguity:** “this reporting period” is unspecified. Clarify the reporting period before tools or an answer. Alternative question wording passes with the canonical machine concept; no synonym policy for the concept payload is introduced. |
| G01 | **Intentional unavailable-source request:** private CRM evidence is outside all permitted sources/tools. Unsupported disposition is necessary, but the fabricated-prose control shows it is insufficient for honesty. |
| H01 | **Intentional authority conflict:** `escalation-policy@1.0#p1-temporary-authority` permits incident-commander authorization before service-owner approval; `service-level-policy@1.0#p1-exception-authority` explicitly prohibits it for the same P1 scenario. Both are current/effective 2026-01-01. The manifest supplies no overriding precedence rule. Handoff with both citations is required; do not choose one policy by file order or scope label. |
| C02 | **Intentional temporal selection:** as of 2025-06-01, `blocker-definition@0.9#blocked-item` (effective 2025-01-01) defines more than one business day waiting for an external dependency. Version 1.0 takes effect 2026-01-01 and changes to material-progress semantics. Existing wrong-version control rejects 1.0 with `wrong_policy_version`; the valid historical contrast still exposes a negation defect. |

Policy identities and section text in the original audit were inspected against the frozen local
manifest and Markdown corpus, with existing version/scope regression tests
included in the full test run. That original audit executes no policy retrieval runtime.

## D01 worker/scorer integration characterization

`runtime-characterization.json` adds eight executed SQL controls around the
unchanged real `SB-D01` task/reference, rather than authoring an observation
envelope. The unchanged generator runs in a temporary directory. Its 500-row
CSV has SHA-256 `cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef`.
Independent Python counts show Data has 8 blocked / 45 active items, the highest
active-work rate at 17.7777777778%. SQL executes on an in-memory SQLite copy;
the production read-only SQL validator, `BoundedLocalExecutor` extraction and
frozen scorer execute unchanged. Actual repository-local policy retrieval
supplies `kpi-dictionary@1.0#blocker-rate`.

Tool choices and final answer prose are authored, scripted controls. The
percentage rows, runtime tool records, evidence references and observations
are produced by execution. No live model or ClickHouse service is involved.
SQLite arithmetic, types and dialect do not qualify live ClickHouse behavior.
Source, generator, generated CSV and all 18 frozen-input fingerprints are
preserved. No production implementation file was modified.

| SQL control | Frozen result | Interpretation |
|---|---|---|
| Correct active filter, no scope output column | Reject: `missing_expected_value` | Real query proves the population, but the extractor reads only row fields |
| Equivalent `NOT (status = 'done')`, no scope column | Same incorrect rejection | Equivalent predicate on this non-null generated dataset |
| Active filter inside a CTE, no scope column | Same incorrect rejection | Valid filtered aggregation still lacks an output label |
| Correct active filter plus constant scope column | Pass | Same computation passes when the row contains the exact expected label |
| All-work denominator plus false active label | Reject: `structured_value_mismatch` | Numeric check catches 20.8633%; the label itself remains unchecked |
| Literal 17.8 and active label from an unfiltered Data row | Incorrect pass | Correct-looking constants establish neither computation, population nor ranking |
| Active predicate widened by `OR 1 = 1` plus false active label | Reject: `structured_value_mismatch` | Includes done work; a predicate substring is insufficient scope proof |
| Empty active result | Reject: missing evidence/value | No structured source evidence is fabricated for empty rows |

Four of eight controls match their independent validity expectations; four
do not. The new command intentionally exits 2. These four integration
mismatches are separate from the original nine envelope mismatches, whose
saved report remains byte-identical. Neither set is accepted evaluator
evidence, and test success does not repair their defects.

The existing worker tests construct an older D01-like contract with 20.9%
and no scope field; they did not exercise the real post-#80 scope requirement.
The integration tests load the frozen current task and reference directly.
They verify reproducibility, counts and ranking, actual extracted values,
and execution while network connections, the live model constructor/method,
and the external ClickHouse function are blocked.

A retrieval overlap surfaced during setup: `KPI dictionary blocker rate`
with `top_k=1` returns `blocker-definition@1.0#blocker-rate`. The integration
uses the more specific authored query `Blocker rate percentage KPI dictionary`
to retrieve the required KPI identity and isolate extraction. No retrieval
ranking, required citation or frozen scoring rule was changed to make it pass.

The owner selected runtime SQL provenance rather than unchecked scope labels
as the remedy direction. That remedy is separate work requiring approval
before activation. This branch preserves the defect and does not implement,
activate or claim acceptance of a correction.

## Development task-template relationships

This is a documented grouping of the current cases, not a new split or a
claim that their results are statistically independent.

| Template group | Cases | Shared inputs / distinction |
|---|---|---|
| Blocker-rate team ranking | A01, D01 | Same structured source and team identity; D01 adds explicit active scope, a different expected rate and KPI evidence. Avoid counting these as unrelated metric templates. |
| KPI definition / interpretation | C01, D01 | Exact same policy section; C01 asks definition, D01 combines it with ranking. Shared policy creates cross-template overlap. |
| Historical policy selection | C02 | Same policy document family across versions; deliberately requires 0.9, not current 1.0. |
| Missing reporting scope | E01 | Clarification envelope, no evidence/tool use; natural-language ambiguity is intended. |
| Unsupported private source | G01 | Abstention envelope, no evidence/tool use; lack of private access is intended. |
| Policy conflict / human authority | H01 | Two current sources with contradictory authority; mandatory structured handoff. |

Current family counts: A=1, B=0, C=2, D=1, E=1, F=0, G=1, H=1 (7 total).
The existing development freeze audit correctly remains unready for 24
cases / three per family. This preparation neither creates the missing 17
tasks nor uses a seven-case audit to assert the Phase 5 bank-completion gate.
New task IDs alone would not establish independent templates; preserve the
overlaps above when expanding and later reviewing bank relationships.

## Reproduction and verification

Run from repository root:

```bash
python3 scripts/audit_system_benchmark_evaluator.py --output experiments/evaluator-validation-20261017/audit.json
python3 scripts/characterize_system_benchmark_runtime.py --output experiments/evaluator-validation-20261017/runtime-characterization.json
python3 -m unittest tests.system_benchmark.test_evaluator_audit -v
python3 -m unittest tests.system_benchmark.test_runtime_characterization -v
python3 -m unittest discover -s tests -v
python3 scripts/check_project_context.py
```

To independently inspect only mismatches after generating the JSON:

```bash
python3 - <<'PY'
import json
r = json.load(open('experiments/evaluator-validation-20261017/audit.json'))
print('References:', r['known_good']['passed'], '/', r['known_good']['total'])
print('Frozen inputs unchanged:', r['freeze_unchanged'])
for c in r['controls']:
    if not c['matches_expectation']:
        print(c['id'], 'expected_pass=', c['expected_pass'],
              'actual_pass=', c['score']['passed'], c['score']['reason_codes'])
PY
```

The audit deliberately exits **2**, preserving the nine mismatches. An exit
of 0 would mean these audit checks passed, still not automatic phase
acceptance. Unit tests verify defect visibility, intended reason attribution,
byte reproducibility, actual input hashes and model/runtime-free imports.
They do **not** turn a defective scorer green.

Observed locally on Python 3.14.7: four audit tests and four integration
characterization tests pass; all 297 repository tests pass. Test-first probes
failed before their respective scripts existed. Python 3.11/3.12 hosted CI
has not been run for this candidate.
The preserved JSON is deterministic and contains no time-dependent claims.

Source-backed self-review checked each control rationale against task and
corpus text, verified exact reason codes in the saved report, checked every
frozen path against baseline, and reviewed the additive diff. No automatic
Codex review was requested. An independent owner/reviewer still needs to
adjudicate evaluator changes; this is author self-review.

Next bounded action: review the nine original and four integration mismatches
and A01 scope ambiguity, approve a versioned remedy if appropriate, then rerun
the preserved controls against that approved version. Phase prerequisites and
official benchmark evidence remain separate.
