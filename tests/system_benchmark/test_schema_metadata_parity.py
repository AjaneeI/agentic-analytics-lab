"""Actual model-facing metadata parity for implemented adapters, offline only."""

import json
from pathlib import Path
import unittest

from scripts.audit_baseline_schema_parity import capture


ROOT = Path(__file__).resolve().parents[2]


class TestSchemaMetadataParity(unittest.TestCase):
    def test_actual_delivered_json_matches_approved_reference_for_all_implemented_lanes(self):
        report = capture()
        self.assertEqual(report["capture_count"], 16)
        self.assertTrue(report["local_capture_checks_pass"])
        self.assertEqual({row["lane"] for row in report["captures"]}, {
            "strong_single", "oracle_routed", "natural_language_routed", "simple_heuristic_routed",
        })
        self.assertEqual({row["probe_capability"] for row in report["captures"]}, {
            "none", "structured", "documents", "multi_source",
        })
        for row in report["captures"]:
            with self.subTest(lane=row["lane"], profile=row["probe_capability"]):
                self.assertTrue(row["tool_metadata_matches_approved"])
                self.assertTrue(row["system_prompt_matches_approved"])
                self.assertTrue(row["model_input_contains_request_only"])
                self.assertEqual(row["evidence_tool_calls"], 0)
                if row["lane"] != "strong_single":
                    self.assertEqual(row["selected_capability"], row["probe_capability"])

    def test_reference_provenance_and_query_json_are_exact(self):
        report = capture()
        self.assertEqual(report["approved_metadata_source_commit"], "644a68d75cf6743d3daaace51f42a0571747417c")
        self.assertEqual(report["approved_query_tool_json_sha256"], "0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9")
        for row in report["captures"]:
            for tool in row["delivered_tools"]:
                if tool["name"] == "query_clickhouse":
                    for forbidden in ("17.8", "20.9", "REF-D01", "development_references"):
                        self.assertNotIn(forbidden, json.dumps(tool))

    def test_independent_review_and_unimplemented_lanes_remain_explicit(self):
        report = capture()
        self.assertEqual(report["independent_parity_review"], "pending")
        self.assertFalse(report["comparative_evaluation_approved"])
        self.assertEqual(report["live_model_calls"], 0)
        self.assertEqual(report["external_database_calls"], 0)
        self.assertTrue(report["unverified_lanes"])
        self.assertEqual(report["deterministic_simple"]["model_facing_metadata"], "not_applicable_no_model")
        self.assertFalse(report["deterministic_simple"]["live_data_equivalence_qualified"])


if __name__ == "__main__":
    unittest.main()
