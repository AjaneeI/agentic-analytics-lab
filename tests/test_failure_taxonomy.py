import unittest

from src.evals.failure_taxonomy import taxonomy_codes


class TestFailureTaxonomy(unittest.TestCase):
    def test_maps_reason_codes_to_hierarchical_tags(self):
        codes = taxonomy_codes(
            reason_codes=(
                "missing_required_evidence",
                "forbidden_tool_used",
                "required_handoff_omitted",
            )
        )

        self.assertIn("grounding.missing_evidence", codes)
        self.assertIn("tool_use.forbidden_tool", codes)
        self.assertIn("authority.failed_to_handoff", codes)

    def test_maps_trajectory_reason_codes(self):
        codes = taxonomy_codes(
            reason_codes=(
                "trajectory_dependency_violation",
                "trajectory_repeated_call",
                "trajectory_call_budget_exceeded",
            )
        )

        self.assertIn("tool_use.dependency_order", codes)
        self.assertIn("tool_use.repeated_call", codes)
        self.assertIn("tool_use.call_budget_exceeded", codes)

    def test_combines_diagnostic_stage_and_recovery(self):
        codes = taxonomy_codes(
            diagnostic_stage="tool_execution",
            recovered=False,
        )

        self.assertEqual(
            codes,
            ("execution.tool_error", "recovery.unrecovered"),
        )

    def test_unknown_observation_remains_explicit(self):
        self.assertEqual(
            taxonomy_codes(reason_codes=("future_reason_code",)),
            ("unknown.unclassified",),
        )


if __name__ == "__main__":
    unittest.main()
