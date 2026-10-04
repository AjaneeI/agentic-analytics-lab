import importlib
import json
import unittest

from src.evals.system_benchmark.contracts import parse_task_contract, SystemBenchmarkResponse, ResponseDisposition


def _scoring(testcase):
    try:
        return importlib.import_module("src.evals.system_benchmark.scoring")
    except ModuleNotFoundError as exc:
        testcase.fail(f"System Benchmark scoring module is missing: {exc}")


def task_payload(**updates):
    payload = {
        "id": "SB-D01",
        "benchmark_version": "system-benchmark-v1",
        "family": "D",
        "split": "development",
        "request": "Compare Data blocker rate with the current blocker policy.",
        "expected_route": "local",
        "expected_capability_profile": "multi_source",
        "allowed_dispositions": ["answer"],
        "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
        "required_evidence_source_types": ["structured", "policy"],
        "acceptable_source_ids": [
            "structured:delivery_work_items",
            "policy:blocker-definition@1.0#blocker-rate",
        ],
        "expected_values": [{"name": "blocked_pct", "value": 20.9, "tolerance": 0.2}],
        "required_claims": ["Data has a 20.9% blocker rate"],
        "forbidden_claims": ["blockers caused lateness"],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse", "retrieve_policy"],
        "forbidden_tools": [],
        "reference_solution_id": "REF-D01",
    }
    payload.update(updates)
    return payload


def response(*, disposition="answer", text="Data has a 20.9% blocker rate", refs=None, clarification=None, handoff=None):
    return SystemBenchmarkResponse(
        disposition=ResponseDisposition(disposition),
        answer_text=text,
        evidence_refs=tuple(refs or [
            "structured:delivery_work_items",
            "policy:blocker-definition@1.0#blocker-rate",
        ]),
        clarification=clarification,
        handoff=handoff,
    )


class TestSystemBenchmarkScoring(unittest.TestCase):
    def test_conforming_response_passes_all_dimensions(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(),
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 20.9},
            validator_passed=True,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.reason_codes, ())
        self.assertTrue(all(item.passed for item in result.dimensions))

    def test_missing_required_evidence_has_explicit_reason(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(refs=["structured:delivery_work_items"]),
            observed_tools=("query_clickhouse",),
            observed_values={"blocked_pct": 20.9},
        )
        self.assertFalse(result.passed)
        self.assertIn("required_evidence_missing:policy", result.reason_codes)
        self.assertIn("required_tool_missing:retrieve_policy", result.reason_codes)

    def test_wrong_policy_version_is_distinguished(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(refs=[
                "structured:delivery_work_items",
                "policy:blocker-definition@0.9#blocker-rate",
            ]),
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 20.9},
        )
        self.assertIn("wrong_policy_version", result.reason_codes)

    def test_fabricated_source_fails_unsupported_case(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload(
            id="SB-G01",
            family="G",
            expected_route="escalate",
            expected_capability_profile="none",
            allowed_dispositions=["unsupported"],
            forbidden_dispositions=["answer", "clarify", "handoff"],
            required_evidence_source_types=[],
            acceptable_source_ids=[],
            expected_values=[],
            required_claims=["Jira is unavailable"],
            forbidden_claims=["I checked Jira"],
            allowed_tools=[],
            forbidden_tools=["query_clickhouse", "retrieve_policy"],
            reference_solution_id="REF-G01",
        ))
        result = scoring.score_response(
            task,
            response(
                disposition="unsupported",
                text="Jira is unavailable",
                refs=["unsupported:jira"],
            ),
            observed_tools=(),
            observed_values={},
        )
        self.assertIn("fabricated_source", result.reason_codes)

    def test_required_escalation_omitted_is_distinct(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload(
            id="SB-E02",
            family="E",
            expected_route="escalate",
            expected_capability_profile="documents",
            allowed_dispositions=["handoff"],
            forbidden_dispositions=["answer", "clarify", "unsupported"],
            required_evidence_source_types=["policy", "policy"],
            acceptable_source_ids=[
                "policy:escalation-policy@1.0#p1-temporary-authority",
                "policy:service-level-policy@1.0#p1-exception-authority",
            ],
            expected_values=[],
            required_claims=[],
            forbidden_claims=[],
            required_handoff_fields=[
                "trigger", "evidence_refs", "actions_taken",
                "unresolved_uncertainty", "requested_authority",
            ],
            allowed_tools=["retrieve_policy"],
            reference_solution_id="REF-E02",
        ))
        result = scoring.score_response(
            task,
            response(
                text="I resolved the P1 policy conflict directly.",
                refs=[
                    "policy:escalation-policy@1.0#p1-temporary-authority",
                    "policy:service-level-policy@1.0#p1-exception-authority",
                ],
            ),
            observed_tools=("retrieve_policy",),
            observed_values={},
        )
        self.assertIn("required_escalation_missing", result.reason_codes)
        self.assertIn("policy_conflict_silently_resolved", result.reason_codes)

    def test_unnecessary_escalation_is_distinguished(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(disposition="handoff", handoff={
                "trigger": "none",
                "evidence_refs": [],
                "actions_taken": [],
                "unresolved_uncertainty": "none",
                "requested_authority": "none",
            }),
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 20.9},
        )
        self.assertIn("unnecessary_escalation", result.reason_codes)

    def test_historical_policy_expectation_rejects_current_version(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload(
            id="SB-C02",
            family="C",
            expected_capability_profile="documents",
            required_evidence_source_types=["policy"],
            acceptable_source_ids=["policy:blocker-definition@0.9#blocker-rate"],
            expected_values=[],
            required_claims=["historical blocker rate definition"],
            forbidden_claims=[],
            allowed_tools=["retrieve_policy"],
            reference_solution_id="REF-C02",
        ))
        result = scoring.score_response(
            task,
            response(
                text="historical blocker rate definition",
                refs=["policy:blocker-definition@1.0#blocker-rate"],
            ),
            observed_tools=("retrieve_policy",),
            observed_values={},
        )
        self.assertIn("wrong_policy_version", result.reason_codes)

    def test_structured_value_mismatch_reports_reason(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(),
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 19.0},
        )
        self.assertIn("expected_value_mismatch:blocked_pct", result.reason_codes)

    def test_forbidden_claim_is_detected(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        result = scoring.score_response(
            task,
            response(text="Data has a 20.9% blocker rate; blockers caused lateness."),
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 20.9},
        )
        self.assertIn("forbidden_claim_present:blockers caused lateness", result.reason_codes)

    def test_empty_tool_allowlist_rejects_unknown_tool(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload(
            id="SB-F01",
            family="F",
            expected_capability_profile="none",
            required_evidence_source_types=[],
            acceptable_source_ids=[],
            expected_values=[],
            required_claims=[],
            forbidden_claims=[],
            allowed_tools=[],
            forbidden_tools=["query_clickhouse", "retrieve_policy"],
            reference_solution_id="REF-F01",
        ))
        result = scoring.score_response(
            task,
            response(refs=[]),
            observed_tools=("web_search",),
            observed_values={},
        )
        self.assertIn("tool_not_allowed:web_search", result.reason_codes)

    def test_empty_source_allowlist_rejects_unsolicited_evidence(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload(
            id="SB-F02",
            family="F",
            expected_capability_profile="none",
            required_evidence_source_types=[],
            acceptable_source_ids=[],
            expected_values=[],
            required_claims=[],
            forbidden_claims=[],
            allowed_tools=[],
            forbidden_tools=["query_clickhouse", "retrieve_policy"],
            reference_solution_id="REF-F02",
        ))
        result = scoring.score_response(
            task,
            response(refs=["web:invented-source"]),
            observed_tools=(),
            observed_values={},
        )
        self.assertIn("unacceptable_source:web:invented-source", result.reason_codes)

    def test_identical_inputs_have_byte_equivalent_scoring(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        kwargs = dict(
            observed_tools=("query_clickhouse", "retrieve_policy"),
            observed_values={"blocked_pct": 20.9},
            validator_passed=True,
        )
        first = scoring.score_response(task, response(), **kwargs)
        second = scoring.score_response(task, response(), **kwargs)
        a = json.dumps(first.to_dict(), sort_keys=True, separators=(",", ":"))
        b = json.dumps(second.to_dict(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(a, b)

    def test_malformed_scoring_observations_fail_before_scoring(self):
        scoring = _scoring(self)
        task = parse_task_contract(task_payload())
        with self.assertRaisesRegex(ValueError, "observed_tools"):
            scoring.score_response(task, response(), observed_tools=("query_clickhouse", 7))
        with self.assertRaisesRegex(ValueError, "observed_values"):
            scoring.score_response(task, response(), observed_values=["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
