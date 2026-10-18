# Phase 3 evaluator-validation preparation — 2026-10-17

**Gate: FAIL / NOT ACCEPTED.** This is independent, model-free preparation
under owner-authorized sprint issues #94/#95, while Phase 2 qualification
remains a separate prerequisite. It neither runs nor qualifies Treatment A.
No model, runtime evidence tool, held-out case, or paid provider was called.

## Evidence and acceptance criteria

Baseline: `58add5e58e581be21d3511fc4cd2cb5be44f49b7`.
The sprint authorization supersedes the older blanket no-Codex engineering
rule for this work only. Frozen evaluation changes still require owner approval.

Issue #95 requires every known-good reference to pass; known-bad controls
to fail for the intended reason; valid alternatives to pass; ambiguity,
policy authority and task-template relationships to be audited; no unresolved
grader defects; and an evidenced scorer/version freeze. Preparation can run
in parallel, but cannot accept Phase 3 before prerequisites.

| Check on the current development bank | Observed | Status |
|---|---|---|
| Authored contract-conforming references | 7/7 pass | Pass for these seven only |
| Negative controls with explicit intended reason codes | 17/17 reject for every targeted reason | Pass for those controls |
| Additional semantic negative controls | 0/5 reject; all five wrongly pass | Fail |
| Valid wording/ordering/numeric alternatives | 5/9 accepted; four rejected | Fail |
| Frozen scorer, contracts, task/reference files, corpus, Q1–Q6, data generator | 18/18 byte-identical to baseline | Pass |
| Full Phase 3 acceptance | Nine unresolved control mismatches; prerequisite not qualified here | Not accepted |

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

Policy identities and section text were inspected against the frozen local
manifest and Markdown corpus, with existing version/scope regression tests
included in the full test run. No policy retrieval runtime was executed.

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
python3 -m unittest tests.system_benchmark.test_evaluator_audit -v
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

Observed locally on Python 3.14.7: four new audit tests pass; all 293
repository tests pass. A test-first probe failed before the audit script
existed. Python 3.11/3.12 hosted CI has not been run for this candidate.
The preserved JSON is deterministic and contains no time-dependent claims.

Source-backed self-review checked each control rationale against task and
corpus text, verified exact reason codes in the saved report, checked every
frozen path against baseline, and reviewed the additive diff. No automatic
Codex review was requested. An independent owner/reviewer still needs to
adjudicate evaluator changes; this is author self-review.

Next bounded action: review the nine mismatches and A01 scope ambiguity,
approve a versioned remedy if appropriate, then rerun the unchanged audit
controls against that approved version. Phase prerequisites and official
benchmark evidence remain separate.
