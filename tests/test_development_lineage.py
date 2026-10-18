"""Source-integrity tests; fixtures are temporary and no scorer is imported."""
import copy
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class DevelopmentLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = {name: self.root / name for name in ("tasks", "references", "corpus_manifest", "kpi", "scorer")}
        self.task = {"id": "SB-D01", "split": "development", "benchmark_version": "same-label",
                     "reference_solution_id": "REF-D01", "expected_values": [{"name": "scope", "value": "active_work_items"}],
                     "acceptable_source_ids": ["delivery_work_items"]}
        self.ref = {"reference_solution_id": "REF-D01", "required_evidence_refs": ["structured:delivery_work_items", "policy:kpi-dictionary@1.0#blocker-rate"]}
        self.entry = {"document_id": "kpi-dictionary", "version": "1.0", "scope": "analytics", "path": "kpi_dictionary_v1.md"}
        self.section = "Blocked active work divided by all active work."
        self._save_sources()
        self.node = {"node_id": "snapshot:SB-D01", "case_id": "SB-D01", "split": "development",
                     "task": {"path": str(self.sources["tasks"]), "file_sha256": self._sha("tasks"), "json_pointer": "/0", "object_sha256": digest(self.task), "benchmark_version": "same-label"},
                     "reference": {"path": str(self.sources["references"]), "file_sha256": self._sha("references"), "json_pointer": "/0", "object_sha256": digest(self.ref), "reference_solution_id": "REF-D01"},
                     "scorer": {"sha256": self._sha("scorer")}, "expected_values": copy.deepcopy(self.task["expected_values"]),
                     "observation_population_scope_literal": "active_work_items", "structured_source_ref": "structured:delivery_work_items", "structured_source_id": "delivery_work_items",
                     "kpi_reference_required": True,
                     "kpi_binding": {"corpus_manifest_sha256": self._sha("corpus_manifest"), "corpus_version": "policy-v1", "entry_json_pointer": "/documents/0", "entry_object_sha256": digest(self.entry), "kpi_file_sha256": self._sha("kpi"), "section_anchor": "blocker-rate", "section_text_sha256": hashlib.sha256(self.section.encode()).hexdigest(), "evidence_reference": "policy:kpi-dictionary@1.0#blocker-rate"}}
        self.node["binding_id"] = digest({"task": digest(self.task), "reference": digest(self.ref), "corpus_entry": digest(self.entry), "kpi_section": hashlib.sha256(self.section.encode()).hexdigest(), "scorer": self._sha("scorer")})
        self.manifest = {"schema_version": "inactive-source-lineage-v1", "lineages": [self.node], "field_bindings": [{"node_id": "snapshot:SB-D01", "source": str(self.sources["tasks"]), "json_pointer": "/0/id", "value": "SB-D01", "canonical_json_sha256": digest("SB-D01")}]}

    def _save_sources(self):
        self.sources["tasks"].write_text(json.dumps([self.task]))
        self.sources["references"].write_text(json.dumps([self.ref]))
        self.sources["corpus_manifest"].write_text(json.dumps({"corpus_version": "policy-v1", "documents": [self.entry]}))
        self.sources["kpi"].write_text("# KPI\n\n## Blocker rate\n" + self.section + "\n")
        self.sources["scorer"].write_text("raise RuntimeError('must never import the scorer')\n")

    def _sha(self, name):
        return hashlib.sha256(self.sources[name].read_bytes()).hexdigest()

    def _run(self, *, manifest_hash=None):
        try:
            module = importlib.import_module("src.evals.development_lineage")
        except ModuleNotFoundError:
            self.fail("inactive development-lineage validator is missing")
        path = self.root / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        return module.validate_lineage(path, manifest_hash or hashlib.sha256(path.read_bytes()).hexdigest(), "snapshot:SB-D01", self.sources)

    def test_consistent_sources_validate_integrity_without_accepting_a_gate(self):
        before = {name: self._sha(name) for name in self.sources}
        result = self._run()
        self.assertEqual(result["status"], "source_integrity_validated")
        self.assertFalse(result["evaluator_accepted"])
        self.assertFalse(result["selection_authority_verified"])
        self.assertFalse(result["runtime_provenance_verified"])
        self.assertEqual(before, {name: self._sha(name) for name in self.sources})

    def test_same_benchmark_label_does_not_allow_a_different_task_population(self):
        self.task["expected_values"] = []
        self.sources["tasks"].write_text(json.dumps([self.task]))
        with self.assertRaisesRegex(ValueError, "source_hash_mismatch:tasks"):
            self._run()

    def test_reference_or_kpi_or_corpus_or_scorer_substitution_is_rejected(self):
        for name in ("references", "kpi", "corpus_manifest", "scorer"):
            with self.subTest(name=name):
                original = self.sources[name].read_bytes()
                self.sources[name].write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "source_hash_mismatch:" + name):
                    self._run()
                self.sources[name].write_bytes(original)

    def test_interpreter_specific_ast_metadata_does_not_override_exact_scorer_bytes(self):
        self.node["scorer"]["ast_sha256"] = "0" * 64
        self.node["scorer"]["function"] = "not_imported_or_parsed"
        try:
            result = self._run()
        except ValueError as exc:
            self.fail(f"exact scorer bytes were rejected by informational AST metadata: {exc}")
        self.assertEqual(result["status"], "source_integrity_validated")

    def test_manifest_requires_an_external_expected_hash(self):
        with self.assertRaisesRegex(ValueError, "manifest_hash_mismatch"):
            self._run(manifest_hash="0" * 64)

    def test_bad_json_pointer_cannot_fall_back_to_another_array_entry(self):
        for pointer in ("/-1", "/00", "/99", "/0/missing", "/0/~2bad"):
            with self.subTest(pointer=pointer):
                self.node["task"]["json_pointer"] = pointer
                with self.assertRaisesRegex(ValueError, "invalid_json_pointer"):
                    self._run()

    def test_field_digest_mismatch_is_rejected_even_when_file_hash_matches(self):
        self.manifest["field_bindings"][0]["canonical_json_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "field_hash_mismatch"):
            self._run()

    def test_duplicate_node_identity_is_rejected(self):
        self.manifest["lineages"].append(copy.deepcopy(self.node))
        with self.assertRaisesRegex(ValueError, "ambiguous_node_id"):
            self._run()

    def test_document_scope_cannot_substitute_for_population_scope(self):
        self.task["expected_values"][0]["value"] = "analytics"
        self.sources["tasks"].write_text(json.dumps([self.task]))
        self.node["task"]["file_sha256"] = self._sha("tasks")
        self.node["task"]["object_sha256"] = digest(self.task)
        self.node["expected_values"] = copy.deepcopy(self.task["expected_values"])
        self.node["observation_population_scope_literal"] = "analytics"
        with self.assertRaisesRegex(ValueError, "scope_namespace_collision"):
            self._run()

    def test_scope_literal_must_match_the_task_not_only_manifest_metadata(self):
        self.node["observation_population_scope_literal"] = "analytics"
        with self.assertRaisesRegex(ValueError, "population_scope_mismatch"):
            self._run()

    def test_reference_join_is_checked_after_exact_file_pin(self):
        self.ref["reference_solution_id"] = "REF-OTHER"
        self.sources["references"].write_text(json.dumps([self.ref]))
        self.node["reference"]["file_sha256"] = self._sha("references")
        self.node["reference"]["object_sha256"] = digest(self.ref)
        with self.assertRaisesRegex(ValueError, "task_reference_mismatch"):
            self._run()


    def test_cli_without_explicit_inputs_cannot_validate_default_benchmark_paths(self):
        result = subprocess.run([sys.executable, "-m", "src.evals.development_lineage"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)

    def test_cli_reports_integrity_only_for_explicit_pinned_sources(self):
        self._run()
        path = self.root / "manifest.json"
        command = [sys.executable, "-m", "src.evals.development_lineage", "--manifest", str(path), "--manifest-sha256", hashlib.sha256(path.read_bytes()).hexdigest(), "--node-id", "snapshot:SB-D01"]
        for role, source in self.sources.items():
            command.extend(["--" + role.replace("_", "-"), str(source)])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout, "CLI must emit an integrity receipt")
        self.assertEqual(json.loads(result.stdout)["status"], "source_integrity_validated")
        self.assertFalse(json.loads(result.stdout)["runtime_provenance_verified"])


if __name__ == "__main__":
    unittest.main()
