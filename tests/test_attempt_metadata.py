"""Hand-authored metadata regressions; no benchmark execution or scoring."""
from copy import deepcopy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def event(kind, scope, number):
    return {"kind": kind, "scope": scope, "sequence_within_example": number,
            "evidence_locator": "example-only:observation",
            "evidence_authenticity": "hand_authored_example_not_a_real_log"}


def record(label="one", events=None):
    return {
        "example_id": label,
        "planned_slot": {"slot_id": "slot-" + label, "task_id": "EXAMPLE-TASK",
                         "treatment_id": "EXAMPLE-ARM", "repeat_label": label,
                         "pairing_key": None, "pairing_status": "not_selected"},
        "attempt_id": "attempt-" + label,
        "evidence_events": events if events is not None else [event("invocation_started", "worker_invocation", 1)],
        "artifact_evidence": "unknown", "score_evidence": "not_supplied_in_example",
        "timeout_evidence": "unknown", "query_log_export_evidence": "not_available",
        "planned_roster_member": True,
        "statistical_missingness_status": "unassigned_owner_policy_required",
        "analysis_denominator_membership": "unassigned_owner_policy_required",
        "exclusion_adjudication": "unassigned_owner_policy_required", "recovery_relation": None,
    }


class AttemptMetadataTests(unittest.TestCase):
    def validate(self, rows):
        spec = importlib.util.find_spec("src.evals.attempt_metadata")
        self.assertIsNotNone(spec, "inactive metadata validator does not exist")
        return importlib.import_module("src.evals.attempt_metadata").validate_attempt_metadata({"examples": rows})

    def assert_error(self, rows, code):
        self.assertIn(code, {error["code"] for error in self.validate(rows)})

    def test_unknown_evidence_is_accepted_without_assigning_policy(self):
        row = record(events=[])
        row["attempt_id"] = None
        original = deepcopy(row)
        self.assertEqual(self.validate([row]), [])
        self.assertEqual(row, original)

    def test_client_timeout_does_not_require_worker_termination(self):
        row = record(events=[event("invocation_started", "worker_invocation", 1), event("timeout_observed", "client_request", 2)])
        row["timeout_evidence"] = "observed_client_request_timeout"
        self.assertEqual(self.validate([row]), [])

    def test_terminal_evidence_does_not_require_preserved_start_marker(self):
        row = record(events=[event("completion_observed", "worker_invocation", 1)])
        row["artifact_evidence"] = "present_in_example"
        self.assertEqual(self.validate([row]), [])

    def test_timeout_does_not_select_artifact_or_denominator_state(self):
        for availability in ["present_in_example", "absent_in_example", "unknown"]:
            with self.subTest(artifact=availability):
                row = record(events=[event("timeout_terminal", "worker_invocation", 1)])
                row["artifact_evidence"] = availability
                row["timeout_evidence"] = "observed_worker_invocation_timeout"
                self.assertEqual(self.validate([row]), [])

    def test_unavailable_query_log_does_not_invalidate_completion(self):
        row = record(events=[event("completion_observed", "worker_invocation", 1)])
        row["artifact_evidence"] = "present_in_example"
        row["timeout_evidence"] = "not_observed"
        self.assertEqual(self.validate([row]), [])

    def test_duplicate_slot_identifier_is_rejected(self):
        rows = [record("one"), record("two")]
        rows[1]["planned_slot"]["slot_id"] = rows[0]["planned_slot"]["slot_id"]
        self.assert_error(rows, "duplicate_slot_id")

    def test_duplicate_planned_coordinate_is_rejected_even_with_distinct_ids(self):
        rows = [record("one"), record("two")]
        rows[1]["planned_slot"]["repeat_label"] = "one"
        self.assert_error(rows, "duplicate_planned_coordinate")

    def test_duplicate_attempt_id_is_rejected(self):
        rows = [record("one"), record("two")]
        rows[1]["attempt_id"] = rows[0]["attempt_id"]
        self.assert_error(rows, "duplicate_attempt_id")

    def test_pre_invocation_failure_cannot_also_have_worker_events(self):
        row = record(events=[event("launch_failed_before_invocation", "launcher", 1), event("invocation_started", "worker_invocation", 2)])
        self.assert_error([row], "contradictory_stage")

    def test_client_timeout_cannot_be_worker_terminal_event(self):
        row = record(events=[event("timeout_terminal", "client_request", 1)])
        self.assert_error([row], "event_scope_mismatch")

    def test_unscoped_event_is_rejected(self):
        row = record()
        del row["evidence_events"][0]["scope"]
        self.assert_error([row], "event_scope_mismatch")

    def test_reversed_duplicate_or_boolean_event_ordinals_are_rejected(self):
        for orders in [(2, 1), (1, 1), (True, 2)]:
            row = record(events=[event("invocation_started", "worker_invocation", orders[0]), event("completion_observed", "worker_invocation", orders[1])])
            self.assert_error([row], "invalid_event_order")

    def test_two_worker_terminal_events_are_rejected(self):
        row = record(events=[event("completion_observed", "worker_invocation", 1), event("timeout_terminal", "worker_invocation", 2)])
        self.assert_error([row], "duplicate_terminal_event")

    def test_duplicate_lifecycle_markers_are_rejected(self):
        row = record(events=[event("invocation_started", "worker_invocation", 1), event("invocation_started", "worker_invocation", 2)])
        self.assert_error([row], "duplicate_event_kind")

    def test_worker_start_after_terminal_is_rejected(self):
        row = record(events=[event("completion_observed", "worker_invocation", 1), event("invocation_started", "worker_invocation", 2)])
        self.assert_error([row], "event_after_worker_terminal")

    def test_client_timeout_can_be_observed_after_worker_completion(self):
        row = record(events=[event("completion_observed", "worker_invocation", 1), event("timeout_observed", "client_request", 2)])
        row["timeout_evidence"] = "observed_client_request_timeout"
        self.assertEqual(self.validate([row]), [])

    def test_timeout_summary_needs_same_scope_event(self):
        row = record(events=[event("timeout_observed", "client_request", 1)])
        row["timeout_evidence"] = "observed_worker_invocation_timeout"
        self.assert_error([row], "timeout_evidence_mismatch")

    def test_missingness_and_pairing_assignments_are_rejected(self):
        for field in ["statistical_missingness_status", "analysis_denominator_membership", "exclusion_adjudication"]:
            row = record(); row[field] = "included"
            self.assert_error([row], "policy_assignment")
        row = record(); row["planned_slot"]["pairing_key"] = "pair-one"
        self.assert_error([row], "policy_assignment")

    def test_unknown_row_claims_are_rejected_including_worker_termination(self):
        row = record(); row["worker_terminated"] = True
        self.assert_error([row], "unsupported_field")

    def test_malformed_shapes_return_diagnostics_instead_of_crashing(self):
        self.assert_error([None, {"planned_slot": []}], "invalid_record")
        row = record(); row["evidence_events"] = [None]
        self.assert_error([row], "invalid_event")

    def test_score_locator_does_not_require_preserved_raw_artifact(self):
        row = record(); row["artifact_evidence"] = "absent_in_example"
        row["score_evidence"] = "score_locator_present_in_example_no_score_value"
        self.assertEqual(self.validate([row]), [])

    def test_client_timeout_description_cannot_claim_worker_terminal_evidence(self):
        row = record(events=[event("timeout_observed", "client_request", 1)])
        row["timeout_evidence"] = "observed_client_request_timeout"
        row["observability_description"] = "worker_invocation_terminal_timeout_observed"
        self.assert_error([row], "description_evidence_mismatch")

    def test_cli_reports_validity_without_writing_or_modifying_input(self):
        script = ROOT / "scripts/validate_attempt_metadata.py"
        self.assertTrue(script.is_file(), "manual offline CLI does not exist")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            original = json.dumps({"examples": [record()]})
            path.write_text(original)
            result = subprocess.run([sys.executable, str(script), str(path)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertIs(report["valid"], True)
            self.assertEqual(report["errors"], [])
            self.assertEqual(path.read_text(), original)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["input.json"])

    def test_cli_rejects_invalid_metadata_and_json_with_nonzero_exit(self):
        script = ROOT / "scripts/validate_attempt_metadata.py"
        self.assertTrue(script.is_file(), "manual offline CLI does not exist")
        for text in ['{"examples":[null]}', 'not JSON']:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "input.json"; path.write_text(text)
                result = subprocess.run([sys.executable, str(script), str(path)], cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIs(json.loads(result.stdout)["valid"], False)

    def test_cli_does_not_create_bytecode_without_environment_opt_out(self):
        script = ROOT / "scripts/validate_attempt_metadata.py"
        self.assertTrue(script.is_file())
        before = set((ROOT / "src").rglob("*.pyc"))
        env = dict(os.environ); env.pop("PYTHONDONTWRITEBYTECODE", None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps({"examples": [record()]}))
            result = subprocess.run([sys.executable, str(script), str(path)], cwd=ROOT, text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set((ROOT / "src").rglob("*.pyc")), before)


if __name__ == "__main__":
    unittest.main()
