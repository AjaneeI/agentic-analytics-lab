"""Inactive, offline consistency checks for proposed attempt metadata.

This module has no benchmark/runtime imports. It checks evidence assertions;
it does not score outcomes or assign an analysis population or denominator.
"""
from __future__ import annotations

from typing import Any


CLAIM_BOUNDARY = (
    "Metadata consistency only; no evidence authenticity, worker termination, "
    "score, estimand, denominator, pairing or missingness policy is established."
)
_UNASSIGNED = "unassigned_owner_policy_required"
_FIELDS = {
    "example_id", "planned_slot", "attempt_id", "evidence_events",
    "observability_description", "artifact_evidence", "score_evidence",
    "timeout_evidence", "query_log_export_evidence", "planned_roster_member",
    "statistical_missingness_status", "analysis_denominator_membership",
    "exclusion_adjudication", "recovery_relation",
}
_SCOPES = {
    "launch_failed_before_invocation": "launcher",
    "invocation_started": "worker_invocation",
    "completion_observed": "worker_invocation",
    "timeout_terminal": "worker_invocation",
    "timeout_observed": "client_request",
}


def validate_attempt_metadata(payload: Any) -> list[dict[str, str]]:
    """Return diagnostics without mutating input or deriving statistical states.

    Input is the proposed hand-authored ``{"examples": [...]}`` format. Unknown
    observations remain unknown; a missing start marker does not invalidate
    independently recorded terminal evidence. This is not a runtime validator.
    """
    errors: list[dict[str, str]] = []

    def error(path: str, code: str) -> None:
        errors.append({"path": path, "code": code})

    if not isinstance(payload, dict) or not isinstance(payload.get("examples"), list):
        error("examples", "invalid_examples")
        return errors
    policies = payload.get("no_selected_policy", {})
    if not isinstance(policies, dict) or any(value is not None for value in policies.values()):
        error("no_selected_policy", "policy_assignment")

    slot_ids: set[str] = set()
    coordinates: set[tuple[str, str, str]] = set()
    attempt_ids: set[str] = set()
    for index, row in enumerate(payload["examples"]):
        path = f"examples[{index}]"
        if not isinstance(row, dict) or not isinstance(row.get("planned_slot"), dict):
            error(path, "invalid_record")
            continue
        if set(row) - _FIELDS:
            error(path, "unsupported_field")
        slot = row["planned_slot"]
        identity_fields = ("slot_id", "task_id", "treatment_id", "repeat_label")
        if any(not isinstance(slot.get(key), str) or not slot[key].strip() for key in identity_fields):
            error(path + ".planned_slot", "invalid_identity")
        else:
            if slot["slot_id"] in slot_ids:
                error(path + ".planned_slot", "duplicate_slot_id")
            slot_ids.add(slot["slot_id"])
            coordinate = tuple(slot[key] for key in identity_fields[1:])
            if coordinate in coordinates:
                error(path + ".planned_slot", "duplicate_planned_coordinate")
            coordinates.add(coordinate)
        if slot.get("pairing_key") is not None or slot.get("pairing_status") != "not_selected":
            error(path + ".planned_slot", "policy_assignment")
        if row.get("planned_roster_member") is not True:
            error(path + ".planned_roster_member", "invalid_record")
        if any(row.get(key) != _UNASSIGNED for key in (
            "statistical_missingness_status", "analysis_denominator_membership", "exclusion_adjudication"
        )) or row.get("recovery_relation") is not None:
            error(path, "policy_assignment")
        attempt = row.get("attempt_id")
        if attempt is not None:
            if not isinstance(attempt, str) or not attempt.strip():
                error(path + ".attempt_id", "invalid_identity")
            elif attempt in attempt_ids:
                error(path + ".attempt_id", "duplicate_attempt_id")
            else:
                attempt_ids.add(attempt)

        for key, allowed in (
            ("artifact_evidence", ("unknown", "present_in_example", "absent_in_example")),
            ("score_evidence", ("not_supplied_in_example", "score_locator_present_in_example_no_score_value")),
            ("query_log_export_evidence", ("not_available", "present_in_example", "unknown")),
            ("timeout_evidence", ("unknown", "not_observed", "observed_client_request_timeout", "observed_worker_invocation_timeout")),
        ):
            if row.get(key) not in allowed:
                error(path + "." + key, "invalid_evidence_state")
        events = row.get("evidence_events")
        if not isinstance(events, list):
            error(path + ".evidence_events", "invalid_events")
            continue
        if events and attempt is None:
            error(path + ".attempt_id", "missing_attempt_identity")
        kinds: list[str] = []
        ordinals: list[int] = []
        for offset, item in enumerate(events):
            event_path = f"{path}.evidence_events[{offset}]"
            if not isinstance(item, dict):
                error(event_path, "invalid_event")
                continue
            kind = item.get("kind")
            if not isinstance(kind, str) or kind not in _SCOPES:
                error(event_path, "invalid_event")
                continue
            if item.get("scope") != _SCOPES[kind]:
                error(event_path, "event_scope_mismatch")
            kinds.append(kind)
            number = item.get("sequence_within_example")
            if type(number) is not int or number < 1:
                error(event_path, "invalid_event_order")
            else:
                ordinals.append(number)
            locator = item.get("evidence_locator")
            if not isinstance(locator, str) or not locator.strip():
                error(event_path, "missing_evidence_locator")
        if ordinals != sorted(set(ordinals)):
            error(path + ".evidence_events", "invalid_event_order")
        if "launch_failed_before_invocation" in kinds and any(kind != "launch_failed_before_invocation" for kind in kinds):
            error(path, "contradictory_stage")
        if len(kinds) != len(set(kinds)):
            error(path, "duplicate_event_kind")
        terminals = [kind for kind in kinds if kind in ("completion_observed", "timeout_terminal")]
        if len(terminals) > 1:
            error(path, "duplicate_terminal_event")
        if terminals and "invocation_started" in kinds and kinds.index("invocation_started") > kinds.index(terminals[0]):
            error(path, "event_after_worker_terminal")
        timeout = row.get("timeout_evidence")
        if ((timeout == "observed_client_request_timeout" and "timeout_observed" not in kinds)
                or (timeout == "observed_worker_invocation_timeout" and "timeout_terminal" not in kinds)
                or (timeout == "not_observed" and any(k in kinds for k in ("timeout_observed", "timeout_terminal")))):
            error(path + ".timeout_evidence", "timeout_evidence_mismatch")
        description = row.get("observability_description")
        descriptions = {
            "planned_slot_only_execution_unknown": not events,
            "explicit_pre_invocation_failure_observed": kinds == ["launch_failed_before_invocation"],
            "invocation_start_observed_completion_unknown": kinds == ["invocation_started"],
            "client_request_terminal_worker_completion_unknown": "timeout_observed" in kinds and not terminals,
            "worker_invocation_terminal_timeout_observed": "timeout_terminal" in kinds,
            "worker_completion_observed": "completion_observed" in kinds,
            "worker_completion_and_score_locator_observed": "completion_observed" in kinds and row.get("score_evidence") == "score_locator_present_in_example_no_score_value",
        }
        if description is not None and (not isinstance(description, str) or not descriptions.get(description, False)):
            error(path + ".observability_description", "description_evidence_mismatch")
    return errors
