"""PR B review regressions over the real retriever and versioned corpus.

The P1 assertions pin reviewed policy-fixture wording; they are not a
natural-language contradiction detector or architecture-performance benchmark.
"""

import json
import os
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools import policy_retrieval as retrieval


class TestPolicyRetrievalRegressions(unittest.TestCase):
    def test_historical_evidence_does_not_disclose_future_definition(self):
        results = retrieval.retrieve_policy(
            "material progress definition", as_of="2025-06-01", top_k=5
        )
        self.assertTrue(results)
        for item in results:
            with self.subTest(section=item.section_id):
                self.assertEqual(item.document_version, "0.9")
                self.assertNotRegex(item.excerpt.lower(), r"material[- ]progress")
                self.assertNotIn("version 1.0", item.excerpt)
                self.assertNotEqual(item.section_id, "historical-note")

    def test_historical_definition_remains_available(self):
        results = retrieval.retrieve_policy(
            "blocked item external dependency", as_of="2025-06-01"
        )
        self.assertEqual(results[0].document_version, "0.9")
        self.assertIn("more than one business day", results[0].excerpt)

    def test_current_definition_remains_available(self):
        results = retrieval.retrieve_policy(
            "blocked item material progress", as_of="2026-01-01"
        )
        self.assertEqual(results[0].document_version, "1.0")
        self.assertIn("material progress", results[0].excerpt)

    def test_source_name_does_not_crowd_out_cross_source_topic(self):
        results = retrieval.retrieve_policy(
            "service-level policy blocker rate comparison"
        )
        identities = {(r.document_id, r.section_id) for r in results}
        self.assertIn(("service-level-policy", "service-target"), identities)
        self.assertIn(("blocker-definition", "blocker-rate"), identities)
        self.assertIn(("kpi-dictionary", "blocker-rate"), identities)
        self.assertNotIn(("service-level-policy", "p1-exception-authority"), identities)

    def test_named_source_only_queries_remain_retrievable(self):
        for query, expected in (
            ("KPI dictionary", "kpi-dictionary"),
            ("analytical interpretation guide", "analytical-interpretation"),
        ):
            with self.subTest(query=query):
                results = retrieval.retrieve_policy(query)
                self.assertTrue(results)
                self.assertEqual({r.document_id for r in results}, {expected})

    def test_irrelevant_named_sections_cannot_displace_topic_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "corpus"
            shutil.copytree(retrieval.DEFAULT_CORPUS_ROOT, root)
            source = root / "service_level_policy_v1.md"
            with source.open("a", encoding="utf-8") as stream:
                for index in range(8):
                    stream.write(f"\n## Administration {index}\nContact directory.\n")
            with patch.object(retrieval, "DEFAULT_CORPUS_ROOT", root):
                results = retrieval.retrieve_policy(
                    "service-level policy blocker rate comparison"
                )
        self.assertIn(
            ("blocker-definition", "blocker-rate"),
            {(r.document_id, r.section_id) for r in results},
        )
        self.assertFalse(any(r.section_id.startswith("administration-") for r in results))

    def test_as_of_rejects_non_calendar_syntax(self):
        for value in (
            "20260101", "2026-W01-1", "2026W011", "2026-1-01", "2026-01-1",
            "2026-01-01T00:00:00", " 2026-01-01", "2026-01-01\n",
            "２０２６-０１-０１", "2026-01-01 ", "", 20260101, True, [],
        ):
            with self.subTest(as_of=value):
                with self.assertRaisesRegex(ValueError, "as_of.*YYYY-MM-DD"):
                    retrieval.retrieve_policy("blocker", as_of=value)

    def test_blank_query_does_not_bypass_argument_validation(self):
        with self.assertRaisesRegex(ValueError, "as_of.*YYYY-MM-DD"):
            retrieval.retrieve_policy("  ", as_of="2026-W01-1")
        with self.assertRaisesRegex(ValueError, "top_k"):
            retrieval.retrieve_policy("  ", top_k=0)
        self.assertEqual(retrieval.retrieve_policy("  ", as_of="2026-01-01"), [])

    def test_as_of_rejects_impossible_calendar_dates(self):
        for value in ("2026-02-29", "2026-13-01", "0000-01-01"):
            with self.subTest(as_of=value):
                with self.assertRaisesRegex(ValueError, "as_of"):
                    retrieval.retrieve_policy("blocker", as_of=value)

    def test_valid_calendar_boundaries_select_correct_version(self):
        for value, expected in (
            ("2025-01-01", "0.9"), ("2025-12-31", "0.9"), ("2026-01-01", "1.0"), ("2028-02-29", "1.0")
        ):
            with self.subTest(as_of=value):
                result = retrieval.retrieve_policy(
                    "blocked item", as_of=value, top_k=1
                )[0]
                self.assertEqual(result.document_version, expected)

    def test_manifest_dates_use_same_calendar_syntax(self):
        for value in ("20250101", "2025-W01-3", " 2025-01-01", "2025-01-01 ", "２０２５-０１-０１"):
            with self.subTest(effective_date=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "corpus"
                shutil.copytree(retrieval.DEFAULT_CORPUS_ROOT, root)
                path = root / "manifest.json"
                manifest = json.loads(path.read_text(encoding="utf-8"))
                old = next(d for d in manifest["documents"] if d["version"] == "0.9")
                old["effective_date"] = value
                path.write_text(json.dumps(manifest), encoding="utf-8")
                with patch.object(retrieval, "DEFAULT_CORPUS_ROOT", root):
                    with self.assertRaisesRegex(retrieval.PolicyCorpusError, "effective_date"):
                        retrieval.retrieve_policy("blocked item")

    def test_p1_rules_conflict_over_same_actor_action_and_condition(self):
        results = retrieval.retrieve_policy(
            "P1 temporary exception authority immediate mitigation", top_k=5
        )
        evidence = {(r.document_id, r.section_id): r for r in results}
        permit = evidence[("escalation-policy", "p1-temporary-authority")]
        prohibit = evidence[("service-level-policy", "p1-exception-authority")]
        condition_and_actor = (
            "When immediate mitigation is required for a customer-facing P1 incident, "
            "an incident commander "
        )
        action = (
            "authorize a temporary exception to the customer-facing P1 service target "
            "before service-owner approval."
        )
        self.assertIn(condition_and_actor + "may " + action, permit.excerpt)
        self.assertIn(condition_and_actor + "must not " + action, prohibit.excerpt)
        self.assertEqual(permit.effective_date, prohibit.effective_date)
        self.assertEqual((permit.status, prohibit.status), ("current", "current"))
        for item in (permit, prohibit):
            self.assertNotRegex(item.excerpt.lower(), r"benchmark|family e|intentional conflict")


    def test_named_source_does_not_hide_a_topic_from_another_document(self):
        results = retrieval.retrieve_policy("delivery operating policy effort ratio")
        self.assertIn(
            ("kpi-dictionary", "effort-ratio"),
            {(item.document_id, item.section_id) for item in results},
        )


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
