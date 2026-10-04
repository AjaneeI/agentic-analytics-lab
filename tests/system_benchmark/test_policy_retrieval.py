import importlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _retrieval(testcase):
    try:
        return importlib.import_module("src.tools.policy_retrieval")
    except ModuleNotFoundError as exc:
        testcase.fail(f"Policy retrieval module is missing: {exc}")


class TestPolicyRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._write_corpus()

    def tearDown(self):
        self.tmp.cleanup()

    def _retrieve(self, retrieval, query, **kwargs):
        with patch.object(retrieval, "DEFAULT_CORPUS_ROOT", self.root):
            return retrieval.retrieve_policy(query, **kwargs)

    def _write(self, relative_path, text):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _write_corpus(self):
        manifest = {
            "corpus_version": "test-policy-v1",
            "documents": [
                {
                    "document_id": "blocker-definition",
                    "version": "0.9",
                    "status": "superseded",
                    "effective_date": "2025-01-01",
                    "scope": "delivery",
                    "path": "blocker_definition_v0_9.md",
                },
                {
                    "document_id": "blocker-definition",
                    "version": "1.0",
                    "status": "current",
                    "effective_date": "2026-01-01",
                    "scope": "delivery",
                    "path": "blocker_definition_v1.md",
                },
                {
                    "document_id": "delivery-operating",
                    "version": "1.0",
                    "status": "current",
                    "effective_date": "2026-01-01",
                    "scope": "delivery",
                    "path": "delivery_operating_v1.md",
                },
                {
                    "document_id": "service-level",
                    "version": "1.0",
                    "status": "current",
                    "effective_date": "2026-01-01",
                    "scope": "service",
                    "path": "service_level_v1.md",
                },
                {
                    "document_id": "tie-alpha",
                    "version": "1.0",
                    "status": "current",
                    "effective_date": "2026-01-01",
                    "scope": "test",
                    "path": "tie_alpha.md",
                },
                {
                    "document_id": "tie-beta",
                    "version": "1.0",
                    "status": "current",
                    "effective_date": "2026-01-01",
                    "scope": "test",
                    "path": "tie_beta.md",
                },
            ],
        }
        self._write("manifest.json", json.dumps(manifest, indent=2))
        self._write(
            "blocker_definition_v0_9.md",
            """# Blocker Definition Policy

## Blocked item
A blocked item is work waiting more than one business day for an external dependency.

## Blocker rate
Blocker rate is blocked items divided by total active items.
""",
        )
        self._write(
            "blocker_definition_v1.md",
            """# Blocker Definition Policy

## Blocked item
A blocked item is active work that cannot make material progress because a required dependency, approval, or decision is unavailable.

## Blocker rate
Blocker rate is the count of blocked active items divided by all active items in scope.
""",
        )
        self._write(
            "delivery_operating_v1.md",
            """# Delivery Operating Policy

## Blocked work review
Teams review blocked work daily and record the dependency owner and next action.

## Delivery health
Delivery health combines blocker rate, aging work, and service-level risk; blocker rate alone is not a causal measure.
""",
        )
        self._write(
            "service_level_v1.md",
            """# Service-Level Policy

## Blocker response
A high-priority blocker requires an owner response within one business day.

## Service target
Service target performance is measured separately from blocker rate.
""",
        )
        self._write(
            "tie_alpha.md",
            """# Tie Alpha

## Shared phrase
Deterministic tie marker policy evidence.
""",
        )
        self._write(
            "tie_beta.md",
            """# Tie Beta

## Shared phrase
Deterministic tie marker policy evidence.
""",
        )
        self._write(
            "unlisted_secret.md",
            """# Unlisted

## Hidden phrase
unlisted-only-token must never be retrievable.
""",
        )

    def test_public_tool_signature_does_not_expose_corpus_path(self):
        retrieval = _retrieval(self)
        parameters = inspect.signature(retrieval.retrieve_policy).parameters

        self.assertEqual(tuple(parameters), ("query", "as_of", "top_k"))

    def test_public_evidence_envelope_matches_design(self):
        retrieval = _retrieval(self)
        result = self._retrieve(retrieval, "blocker rate", top_k=1)[0]

        self.assertEqual(
            tuple(result.__dataclass_fields__),
            (
                "document_id",
                "document_version",
                "section_id",
                "excerpt",
                "effective_date",
                "status",
            ),
        )

    def test_default_retrieval_prefers_current_policy_version(self):
        retrieval = _retrieval(self)
        results = self._retrieve(
            retrieval,
            "What counts as a blocked item?",
        )

        self.assertTrue(results)
        self.assertEqual(results[0].document_id, "blocker-definition")
        self.assertEqual(results[0].document_version, "1.0")
        self.assertEqual(results[0].status, "current")

    def test_as_of_date_returns_applicable_superseded_version(self):
        retrieval = _retrieval(self)
        results = self._retrieve(
            retrieval,
            "What counts as a blocked item?",
            as_of="2025-06-01",
        )

        self.assertTrue(results)
        self.assertEqual(results[0].document_id, "blocker-definition")
        self.assertEqual(results[0].document_version, "0.9")
        self.assertEqual(results[0].status, "superseded")

    def test_section_level_ranking_disambiguates_overlapping_terms(self):
        retrieval = _retrieval(self)
        results = self._retrieve(
            retrieval,
            "How is blocker rate calculated for active items?",
        )

        self.assertTrue(results)
        self.assertEqual(results[0].document_id, "blocker-definition")
        self.assertEqual(results[0].section_id, "blocker-rate")

    def test_tie_breaking_is_stable(self):
        retrieval = _retrieval(self)
        first = self._retrieve(
            retrieval,
            "deterministic tie marker",
            top_k=2,
        )
        second = self._retrieve(
            retrieval,
            "deterministic tie marker",
            top_k=2,
        )

        first_ids = [(item.document_id, item.section_id) for item in first]
        second_ids = [(item.document_id, item.section_id) for item in second]
        self.assertEqual(first_ids, second_ids)
        self.assertEqual(first_ids[:2], [
            ("tie-alpha", "shared-phrase"),
            ("tie-beta", "shared-phrase"),
        ])

    def test_top_k_is_bounded(self):
        retrieval = _retrieval(self)

        with self.assertRaisesRegex(ValueError, "top_k"):
            self._retrieve(retrieval, "blocker", top_k=0)
        with self.assertRaisesRegex(ValueError, "top_k"):
            self._retrieve(
                retrieval,
                "blocker",
                top_k=retrieval.MAX_TOP_K + 1,
            )

    def test_blank_query_returns_inspectable_empty_result(self):
        retrieval = _retrieval(self)

        self.assertEqual(
            self._retrieve(retrieval, "   "),
            [],
        )

    def test_manifest_requires_corpus_version(self):
        retrieval = _retrieval(self)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest.pop("corpus_version")
        (self.root / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "corpus_version"):
            self._retrieve(retrieval, "blocked item")

    def test_manifest_rejects_multiple_current_versions_for_one_document(self):
        retrieval = _retrieval(self)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["documents"][0]["status"] = "current"
        (self.root / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "current"):
            self._retrieve(retrieval, "blocked item")

    def test_manifest_requires_one_current_version_per_document(self):
        retrieval = _retrieval(self)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["documents"][1]["status"] = "superseded"
        (self.root / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "current"):
            self._retrieve(retrieval, "blocked item")

    def test_manifest_rejects_duplicate_effective_dates_for_one_document(self):
        retrieval = _retrieval(self)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["documents"][0]["effective_date"] = "2026-01-01"
        (self.root / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "effective_date"):
            self._retrieve(retrieval, "blocked item")

    def test_manifest_path_traversal_is_rejected(self):
        retrieval = _retrieval(self)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["documents"][0]["path"] = "../outside.md"
        (self.root / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(retrieval.PolicyCorpusError, "path"):
            self._retrieve(retrieval, "blocked item")

    def test_unlisted_files_are_not_retrievable(self):
        retrieval = _retrieval(self)

        results = self._retrieve(
            retrieval,
            "unlisted-only-token",
        )

        self.assertEqual(results, [])

    def test_excerpt_length_is_bounded(self):
        retrieval = _retrieval(self)
        results = self._retrieve(
            retrieval,
            "blocked item active work dependency approval decision",
        )

        self.assertTrue(results)
        self.assertLessEqual(len(results[0].excerpt), retrieval.MAX_EXCERPT_CHARS)

    def test_evidence_identity_is_complete(self):
        retrieval = _retrieval(self)
        result = self._retrieve(
            retrieval,
            "blocker response owner",
            top_k=1,
        )[0]

        self.assertEqual(result.document_id, "service-level")
        self.assertEqual(result.document_version, "1.0")
        self.assertEqual(result.section_id, "blocker-response")
        self.assertEqual(result.effective_date, "2026-01-01")
        self.assertEqual(result.status, "current")
        self.assertTrue(result.excerpt)

    def test_repository_corpus_is_retrievable_by_default(self):
        retrieval = _retrieval(self)

        results = retrieval.retrieve_policy(
            "How is blocker rate calculated for active items?",
            top_k=1,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, "blocker-definition")
        self.assertEqual(results[0].document_version, "1.0")
        self.assertEqual(results[0].section_id, "blocker-rate")

    def test_invalid_as_of_date_is_rejected(self):
        retrieval = _retrieval(self)

        with self.assertRaisesRegex(ValueError, "as_of"):
            self._retrieve(
                retrieval,
                "blocker",
                as_of="not-a-date",
            )


if __name__ == "__main__":
    unittest.main()
