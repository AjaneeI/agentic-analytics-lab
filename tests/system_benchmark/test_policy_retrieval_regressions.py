"""PR B correctness regressions using the actual repository policy corpus.

These are development regression tests, not held-out agent performance evidence.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.tools import policy_retrieval as retrieval


class TestRepositoryPolicyRegressions(unittest.TestCase):
    def test_historical_evidence_does_not_reveal_future_policy_semantics(self):
        results = retrieval.retrieve_policy(
            "blocker definition material progress", as_of="2025-06-01", top_k=5
        )
        self.assertTrue(results)
        for item in results:
            with self.subTest(section=item.section_id):
                self.assertEqual(item.document_version, "0.9")
                self.assertNotEqual(item.section_id, "historical-note")
                self.assertNotIn("material-progress", item.excerpt.lower())
                self.assertNotIn("version 1.0", item.excerpt.lower())

    def test_current_blocker_definition_retains_material_progress_semantics(self):
        results = retrieval.retrieve_policy("blocked item material progress")
        evidence = next(item for item in results if item.section_id == "blocked-item")
        self.assertEqual(evidence.document_version, "1.0")
        self.assertIn("material progress", evidence.excerpt)

    def test_mixed_source_query_keeps_both_blocker_rate_definitions(self):
        results = retrieval.retrieve_policy("service-level policy blocker rate comparison")
        identities = {(item.document_id, item.section_id) for item in results}
        self.assertIn(("blocker-definition", "blocker-rate"), identities)
        self.assertIn(("kpi-dictionary", "blocker-rate"), identities)
        self.assertIn(("service-level-policy", "service-target"), identities)

    def test_named_source_does_not_hide_a_topic_from_another_document(self):
        results = retrieval.retrieve_policy("delivery operating policy effort ratio")
        self.assertIn(
            ("kpi-dictionary", "effort-ratio"),
            {(item.document_id, item.section_id) for item in results},
        )

    def test_source_name_only_queries_remain_retrievable(self):
        for query, document_id in (
            ("KPI dictionary", "kpi-dictionary"),
            ("analytical interpretation guide", "analytical-interpretation"),
        ):
            with self.subTest(query=query):
                results = retrieval.retrieve_policy(query)
                self.assertTrue(results)
                self.assertTrue(all(item.document_id == document_id for item in results))

    def test_noncanonical_as_of_dates_are_rejected(self):
        for value in (
            "20260101", "2026-W01-1", "2026W011", "2026-1-01", "2026-01-1",
            " 2026-01-01", "2026-01-01 ", "2026-01-01\n",
            "2026-01-01T00:00:00", "2026-02-29", "2026-13-01", "0000-01-01",
            "", 20260101, True, [],
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "as_of"):
                    retrieval.retrieve_policy("blocked item", as_of=value)

    def test_blank_query_does_not_bypass_argument_validation(self):
        with self.assertRaisesRegex(ValueError, "as_of"):
            retrieval.retrieve_policy(" ", as_of="2026-W01-1")
        with self.assertRaisesRegex(ValueError, "top_k"):
            retrieval.retrieve_policy(" ", top_k=0)
        self.assertEqual(retrieval.retrieve_policy(" ", as_of="2026-01-01"), [])

    def test_calendar_cutoff_boundary_and_valid_leap_day(self):
        for cutoff, expected_version in (
            ("2025-01-01", "0.9"), ("2025-12-31", "0.9"), ("2026-01-01", "1.0")
        ):
            with self.subTest(cutoff=cutoff):
                item = retrieval.retrieve_policy("blocked item", as_of=cutoff, top_k=1)[0]
                self.assertEqual(item.document_version, expected_version)
        self.assertEqual(retrieval.retrieve_policy("blocked item", as_of="2024-02-29"), [])

    def test_noncanonical_manifest_dates_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "corpus"
            shutil.copytree(retrieval.DEFAULT_CORPUS_ROOT, root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for value in ("20260101", "2026-W01-4", " 2026-01-01", "2026-01-01 "):
                with self.subTest(value=value):
                    manifest["documents"][0]["effective_date"] = value
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with patch.object(retrieval, "DEFAULT_CORPUS_ROOT", root):
                        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "effective_date"):
                            retrieval.retrieve_policy("KPI dictionary")

    def test_newer_superseded_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "corpus"
            shutil.copytree(retrieval.DEFAULT_CORPUS_ROOT, root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest["documents"]:
                if entry["document_id"] == "blocker-definition" and entry["status"] == "superseded":
                    entry["effective_date"] = "2027-01-01"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(retrieval, "DEFAULT_CORPUS_ROOT", root):
                with self.assertRaisesRegex(retrieval.PolicyCorpusError, "latest effective_date"):
                    retrieval.retrieve_policy("blocked item")

    def test_p1_rules_disagree_on_the_same_authorization_in_the_same_context(self):
        results = retrieval.retrieve_policy("P1 exception authority immediate mitigation", top_k=5)
        by_identity = {(item.document_id, item.section_id): item.excerpt for item in results}
        permitted = by_identity[("escalation-policy", "p1-temporary-authority")]
        forbidden = by_identity[("service-level-policy", "p1-exception-authority")]
        action = "authorize an exception to a customer-facing P1 service target before service-owner approval"
        self.assertIn("An incident commander may " + action, permitted)
        self.assertIn("An incident commander must not " + action, forbidden)
        self.assertIn("when immediate mitigation is required", permitted)
        self.assertIn("when immediate mitigation is required", forbidden)

    def test_retrievable_corpus_omits_benchmark_construction_labels(self):
        for path in sorted(retrieval.DEFAULT_CORPUS_ROOT.glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                for label in ("benchmark", "held-out", "intentional conflict", "expected behavior"):
                    self.assertNotIn(label, text)

    def test_retrieval_is_identical_across_hash_seeds_and_repeats(self):
        code = (
            "import json; from dataclasses import asdict; "
            "from src.tools.policy_retrieval import retrieve_policy; "
            "print(json.dumps([asdict(x) for x in retrieve_policy("
            "'service-level policy blocker rate comparison')],sort_keys=True))"
        )
        root = Path(__file__).resolve().parents[2]
        outputs = [
            subprocess.check_output(
                [sys.executable, "-c", code], cwd=root,
                env={**os.environ, "PYTHONHASHSEED": seed}, timeout=10,
            )
            for seed in ("1", "7", "42", "42")
        ]
        self.assertTrue(all(output == outputs[0] for output in outputs))


if __name__ == "__main__":
    unittest.main()
