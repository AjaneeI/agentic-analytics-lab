import unittest

from src.evals.system_benchmark.contracts import parse_task_contract
from src.evals.system_benchmark.freeze_audit import audit_development_freeze
from src.evals.system_benchmark.references import parse_reference_expectation


def make_task(family, index):
    capability = "none" if family in {"E", "F", "G"} else "structured"
    source_types = [] if capability == "none" else ["structured"]
    source_ids = [] if capability == "none" else ["delivery_work_items"]
    allowed_tools = [] if capability == "none" else ["query_clickhouse"]
    allowed = ["unsupported"] if family == "G" else ["answer"]
    forbidden = [x for x in ["answer", "clarify", "unsupported", "handoff"] if x not in allowed]
    return parse_task_contract({
        "id": f"SB-{family}{index:02d}",
        "benchmark_version": "system-benchmark-v1",
        "family": family,
        "split": "development",
        "request": f"Development task {family} {index}",
        "expected_route": "escalate" if family in {"E", "G", "H"} else "deterministic",
        "expected_capability_profile": capability,
        "allowed_dispositions": allowed,
        "forbidden_dispositions": forbidden,
        "required_evidence_source_types": source_types,
        "acceptable_source_ids": source_ids,
        "expected_values": [],
        "required_claims": [],
        "forbidden_claims": [],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": allowed_tools,
        "forbidden_tools": [],
        "reference_solution_id": f"REF-{family}{index:02d}",
    })


class TestFreezeAudit(unittest.TestCase):
    def test_current_style_seven_task_set_cannot_be_called_frozen(self):
        tasks = [make_task(family, 1) for family in "ABCDEFG"]
        audit = audit_development_freeze(tasks, [], expected_per_family=3)

        self.assertFalse(audit.ready)
        self.assertIn("development_task_count_incomplete", audit.reasons)
        self.assertIn("family_H_coverage_incomplete", audit.reasons)
        self.assertEqual(audit.expected_task_count, 24)

    def test_complete_family_coverage_still_requires_references(self):
        tasks = [
            make_task(family, index)
            for family in "ABCDEFGH"
            for index in (1, 2, 3)
        ]
        audit = audit_development_freeze(tasks, [], expected_per_family=3)

        self.assertFalse(audit.ready)
        self.assertEqual(audit.task_count, 24)
        self.assertIn("missing_references", audit.reasons)
        self.assertNotIn("development_task_count_incomplete", audit.reasons)


if __name__ == "__main__":
    unittest.main()
