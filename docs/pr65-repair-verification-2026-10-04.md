# PR B repair and concurrent-work reconciliation — October 4, 2026

## Scope and provenance

The original policy-retrieval source is `8276df44d2181eab829b5b6bacf23905295862db`.
Two fix commits were created concurrently from it:

- `c065972e63de07352e61b846074700a21da625ad`: isolated no-PR repair, 13 real-corpus regressions, strict input validation, execution-budget documentation, manual Python workflow trigger.
- `82ef40cfb19549b25a29c5f2b18fbe4a462f95ec`: original PR #65 update, 12 regressions including an injected irrelevant-section case and explicit same-condition P1 authorization assertions.

The reconciled commit retains both parents rather than overwriting either history. It keeps the simpler section-first integer ranking from the concurrent revision, its P1 wording and all 12 test methods. Existing tests were strengthened with the isolated revision's assertions; four nonduplicative test methods were retained. Strict raw manifest-date and blank-query top_k validation remain enforced.

## Deterministic verification

No agent model, LLM judge, Codex task, Codex review, or paid model API is part of this verification procedure.

1. Original source snapshot: 195 tests passed on sandbox Python 3.13.
2. Original isolated regression tests failed before production changes.
3. Isolated repair `c065972`: 31 policy tests and 208 full tests passed.
4. Hosted Python 3.11/3.12 both passed 208 tests on `c065972` in [run 37235469789](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/37235469789); [CodeQL run 37235469754](https://github.com/AjaneeI/agentic-analytics-lab/actions/runs/37235469754) succeeded on that same commit.
5. Concurrent source `82ef40c`: 207 tests passed in the isolated sandbox after supplying Git metadata required by the context test.
6. The reconciled regression suite failed on the concurrent source at blank-query top_k validation and untrimmed manifest dates; adding those guards produced 211 passing full tests.
7. For each original defect, temporarily reintroduce only that defect, run the corresponding regression and require an assertion failure, restore the fixed source, then rerun the full suite. All four reintroductions were detected. These are mutation checks, not model-performance measurements.
8. Source compilation, the project-context checker, and whitespace diff checks passed.

A final reconciled commit requires its own Python 3.11/3.12 and CodeQL results. Earlier green commits are not substitutes. The PR checkpoint comment and canonical Notion record identify the final verified commit and run links.

## Reproduction

From a checkout of the reconciled commit:

```bash
python3 -m unittest discover -s tests/system_benchmark -p 'test_policy_retrieval*.py' -v
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
python3 scripts/check_project_context.py
git diff --check
```

The test corpus is repository-local and read-only at runtime. Temporary adversarial corpus mutations occur only in isolated test directories. Cross-process hash-seed comparisons verify stable serialized retrieval results. Exact policy wording assertions pin a reviewed fixture; they do not implement a general natural-language contradiction detector.

## Frozen boundary

`evals/questions.json` remains blob `fd379027496cdb8830bda5967215ea9d7b9c27a4`. The existing Q1–Q6 scorer, dataset, prompts, model adapter, single-agent code, read-only ClickHouse boundary, and accepted benchmark evidence are unchanged. No held-out tasks were added.

## Budget and integration gate

Decision D-010 prohibits Codex-credit consumption for benchmark work. Repository instructions cannot disable external automatic reviews or cancel a running external review. During reconciliation, a separate manual review request appeared on PR #65 (comment 5984572438); its summary (5984574988) reported a running Codex review. This session did not initiate that request. Credit consumption and cancellation are not verified.

Stop external Codex review activity and verify automatic review settings are off before updating a reviewable PR. Do not remove branch protection, skip required checks, or push directly to main as a workaround. Keep the original PR and the isolated branch intact until a current-head-aware integration can proceed safely. PR C / issue #66 remains dependent on PR B merging.
