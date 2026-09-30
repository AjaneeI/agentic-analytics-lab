import importlib
import unittest


def _contracts(testcase):
    try:
        return importlib.import_module("src.evals.system_benchmark.contracts")
    except ModuleNotFoundError as exc:
        testcase.fail(f"System Benchmark contracts module is missing: {exc}")


def valid_task_payload():
    return {
        "id": "SB-A01",
        "benchmark_version": "system-benchmark-v1",
        "family": "A",
        "split": "development",
        "request": "Which team has the highest blocker rate?",
        "expected_route": "deterministic",
        "expected_capability_profile": "structured",
        "allowed_dispositions": ["answer"],
        "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
        "required_evidence_source_types": ["structured"],
        "acceptable_source_ids": ["delivery_work_items"],
        "expected_values": [
            {"name": "blocked_pct", "value": 20.9, "tolerance": 0.2}
        ],
        "required_claims": ["identify the team and blocker rate"],
        "forbidden_claims": ["claim that blockers cause lateness"],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse"],
        "forbidden_tools": ["retrieve_policy"],
        "reference_solution_id": "REF-A01",
    }


class TestSystemBenchmarkTaskContract(unittest.TestCase):
    def test_valid_task_contract_is_typed_and_normalized(self):
        contracts = _contracts(self)
        task = contracts.parse_task_contract(valid_task_payload())

        self.assertEqual(task.case_id, "SB-A01")
        self.assertEqual(task.family.value, "A")
        self.assertEqual(task.split.value, "development")
        self.assertEqual(task.expected_route.value, "deterministic")
        self.assertEqual(task.expected_capability_profile.value, "structured")
        self.assertEqual(
            tuple(item.value for item in task.allowed_dispositions),
            ("answer",),
        )
        self.assertEqual(task.expected_values[0].tolerance, 0.2)

    def test_invalid_family_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["family"] = "Z"

        with self.assertRaisesRegex(ValueError, "family"):
            contracts.parse_task_contract(payload)

    def test_invalid_split_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["split"] = "training"

        with self.assertRaisesRegex(ValueError, "split"):
            contracts.parse_task_contract(payload)

    def test_invalid_route_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["expected_route"] = "admin-bypass"

        with self.assertRaisesRegex(ValueError, "route"):
            contracts.parse_task_contract(payload)

    def test_invalid_capability_profile_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["expected_capability_profile"] = "specialist"

        with self.assertRaisesRegex(ValueError, "capability"):
            contracts.parse_task_contract(payload)

    def test_invalid_disposition_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["allowed_dispositions"] = ["delegate"]

        with self.assertRaisesRegex(ValueError, "disposition"):
            contracts.parse_task_contract(payload)

    def test_allowed_and_forbidden_dispositions_must_be_disjoint(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["forbidden_dispositions"] = ["answer"]

        with self.assertRaisesRegex(ValueError, "disposition"):
            contracts.parse_task_contract(payload)

    def test_malformed_tolerance_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["expected_values"][0]["tolerance"] = "close enough"

        with self.assertRaisesRegex(ValueError, "tolerance"):
            contracts.parse_task_contract(payload)

    def test_negative_tolerance_is_rejected(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["expected_values"][0]["tolerance"] = -0.1

        with self.assertRaisesRegex(ValueError, "tolerance"):
            contracts.parse_task_contract(payload)

    def test_evidence_capability_requires_source_types(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["required_evidence_source_types"] = []

        with self.assertRaisesRegex(ValueError, "evidence source"):
            contracts.parse_task_contract(payload)

    def test_clarify_disposition_requires_clarification_concept(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["allowed_dispositions"] = ["clarify"]
        payload["forbidden_dispositions"] = ["answer", "unsupported", "handoff"]

        with self.assertRaisesRegex(ValueError, "clarification"):
            contracts.parse_task_contract(payload)

    def test_handoff_disposition_requires_complete_handoff_contract(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["allowed_dispositions"] = ["handoff"]
        payload["forbidden_dispositions"] = ["answer", "clarify", "unsupported"]
        payload["required_handoff_fields"] = [
            "trigger",
            "evidence_refs",
            "actions_taken",
            "unresolved_uncertainty",
        ]

        with self.assertRaisesRegex(ValueError, "handoff"):
            contracts.parse_task_contract(payload)

    def test_handoff_contract_accepts_all_canonical_fields(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["allowed_dispositions"] = ["handoff"]
        payload["forbidden_dispositions"] = ["answer", "clarify", "unsupported"]
        payload["required_handoff_fields"] = [
            "trigger",
            "evidence_refs",
            "actions_taken",
            "unresolved_uncertainty",
            "requested_authority",
        ]

        task = contracts.parse_task_contract(payload)

        self.assertEqual(
            set(task.required_handoff_fields),
            set(contracts.REQUIRED_HANDOFF_FIELDS),
        )

    def test_allowed_and_forbidden_tools_must_be_disjoint(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["forbidden_tools"] = ["query_clickhouse"]

        with self.assertRaisesRegex(ValueError, "tool"):
            contracts.parse_task_contract(payload)

    def test_reference_solution_id_is_required(self):
        contracts = _contracts(self)
        payload = valid_task_payload()
        payload["reference_solution_id"] = "   "

        with self.assertRaisesRegex(ValueError, "reference"):
            contracts.parse_task_contract(payload)


class TestSystemBenchmarkResponseContract(unittest.TestCase):
    def test_response_envelope_preserves_disposition_and_evidence(self):
        contracts = _contracts(self)
        response = contracts.SystemBenchmarkResponse(
            disposition=contracts.ResponseDisposition.ANSWER,
            answer_text="Data has the highest blocker rate.",
            evidence_refs=("delivery_work_items:team=Data",),
            uncertainty=None,
        )

        self.assertEqual(response.disposition.value, "answer")
        self.assertEqual(
            response.evidence_refs,
            ("delivery_work_items:team=Data",),
        )
        self.assertIsNone(response.clarification)
        self.assertIsNone(response.handoff)


if __name__ == "__main__":
    unittest.main()
