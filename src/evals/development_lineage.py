"""Inactive development source-integrity validation; no runtime/scorer imports.

Callers must supply every source path and an independently expected manifest hash.
A successful check establishes only that the selected bytes/joins are consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _pointer(value: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("invalid_json_pointer")
    try:
        for token in pointer[1:].split("/"):
            if re.search(r"~(?![01])", token):
                raise ValueError("invalid_json_pointer")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError("invalid_json_pointer")
                value = value[int(token)]
            elif isinstance(value, dict):
                value = value[token]
            else:
                raise ValueError("invalid_json_pointer")
        return value
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("invalid_json_pointer") from exc


def validate_lineage(
    manifest_path: str | Path,
    manifest_sha256: str,
    node_id: str,
    sources: Mapping[str, str | Path],
) -> dict[str, Any]:
    """Check a single explicitly selected, pinned inactive lineage.

    This neither approves the selection nor validates answers, population meaning,
    dataset identity, SQL, effective settings, or metric/ranking derivation.
    """
    raw_manifest = Path(manifest_path).read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != manifest_sha256:
        raise ValueError("manifest_hash_mismatch")
    try:
        manifest = json.loads(raw_manifest)
        if manifest["schema_version"] != "inactive-source-lineage-v1":
            raise ValueError("unsupported_manifest_schema")
        nodes = [node for node in manifest["lineages"] if node["node_id"] == node_id]
        if len(nodes) != 1:
            raise ValueError("ambiguous_node_id")
        node = nodes[0]
        expected_hashes = {
            "tasks": node["task"]["file_sha256"],
            "references": node["reference"]["file_sha256"],
            "corpus_manifest": node["kpi_binding"]["corpus_manifest_sha256"],
            "kpi": node["kpi_binding"]["kpi_file_sha256"],
            "scorer": node["scorer"]["sha256"],
        }
        if set(sources) != set(expected_hashes):
            raise ValueError("source_roles_mismatch")
        raw_sources = {}
        for role, expected in expected_hashes.items():
            raw_sources[role] = Path(sources[role]).read_bytes()
            if hashlib.sha256(raw_sources[role]).hexdigest() != expected:
                raise ValueError("source_hash_mismatch:" + role)
        parsed = {role: json.loads(raw_sources[role]) for role in ("tasks", "references", "corpus_manifest")}
        task = _pointer(parsed["tasks"], node["task"]["json_pointer"])
        reference = _pointer(parsed["references"], node["reference"]["json_pointer"])
        kpi = node["kpi_binding"]
        entry = _pointer(parsed["corpus_manifest"], kpi["entry_json_pointer"])
        for role, value, expected in (
            ("tasks", task, node["task"]["object_sha256"]),
            ("references", reference, node["reference"]["object_sha256"]),
            ("corpus_manifest", entry, kpi["entry_object_sha256"]),
        ):
            if _digest(value) != expected:
                raise ValueError("object_hash_mismatch:" + role)
        if task["split"] != "development" or node["split"] != "development":
            raise ValueError("development_only")
        if task["id"] != node["case_id"] or task["benchmark_version"] != node["task"]["benchmark_version"]:
            raise ValueError("task_identity_mismatch")
        if task["reference_solution_id"] != reference["reference_solution_id"] or reference["reference_solution_id"] != node["reference"]["reference_solution_id"]:
            raise ValueError("task_reference_mismatch")
        if task["expected_values"] != node["expected_values"]:
            raise ValueError("expected_values_mismatch")
        scopes = [v["value"] for v in task["expected_values"] if v["name"] == "scope"]
        if len(scopes) > 1 or (scopes[0] if scopes else None) != node["observation_population_scope_literal"]:
            raise ValueError("population_scope_mismatch")
        if scopes and scopes[0] == entry["scope"]:
            raise ValueError("scope_namespace_collision")
        if parsed["corpus_manifest"]["corpus_version"] != kpi["corpus_version"] or entry["path"] != "kpi_dictionary_v1.md" or kpi["section_anchor"] != "blocker-rate":
            raise ValueError("kpi_identity_mismatch")
        policy_ref = f"policy:{entry['document_id']}@{entry['version']}#{kpi['section_anchor']}"
        if policy_ref != kpi["evidence_reference"] or (policy_ref in reference["required_evidence_refs"]) != node["kpi_reference_required"]:
            raise ValueError("kpi_reference_mismatch")
        if node["structured_source_ref"] != "structured:" + node["structured_source_id"] or node["structured_source_ref"] not in reference["required_evidence_refs"] or node["structured_source_id"] not in task["acceptable_source_ids"]:
            raise ValueError("structured_source_mismatch")
        text = raw_sources["kpi"].decode("utf-8")
        if text.count("## Blocker rate\n") != 1:
            raise ValueError("kpi_section_mismatch")
        section = text.split("## Blocker rate\n", 1)[1].split("\n## ", 1)[0].strip()
        if hashlib.sha256(section.encode()).hexdigest() != kpi["section_text_sha256"]:
            raise ValueError("kpi_section_mismatch")
        paths_to_roles = {node["task"]["path"]: "tasks", node["reference"]["path"]: "references"}
        for field in manifest["field_bindings"]:
            if field["node_id"] != node_id:
                continue
            role = paths_to_roles.get(field["source"])
            if role is None:
                raise ValueError("field_source_mismatch")
            value = _pointer(parsed[role], field["json_pointer"])
            if value != field["value"] or _digest(value) != field["canonical_json_sha256"]:
                raise ValueError("field_hash_mismatch")
        binding = _digest({"task": _digest(task), "reference": _digest(reference), "corpus_entry": _digest(entry), "kpi_section": kpi["section_text_sha256"], "scorer": expected_hashes["scorer"]})
        if binding != node["binding_id"]:
            raise ValueError("binding_id_mismatch")
    except (KeyError, TypeError, IndexError, AttributeError, SyntaxError, UnicodeError) as exc:
        raise ValueError("malformed_lineage") from exc
    return {"status": "source_integrity_validated", "node_id": node_id, "binding_id": binding,
            "evaluator_accepted": False, "selection_authority_verified": False,
            "runtime_provenance_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "manifest-sha256", "node-id", "tasks", "references", "corpus-manifest", "kpi", "scorer"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        result = validate_lineage(args.manifest, args.manifest_sha256, args.node_id,
                                  {role: getattr(args, role) for role in ("tasks", "references", "corpus_manifest", "kpi", "scorer")})
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "source_integrity_rejected", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
