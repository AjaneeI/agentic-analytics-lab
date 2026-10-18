#!/usr/bin/env python3
"""Score development-only audit controls without changing the frozen evaluator.

Exit 2 preserves a failed evaluator/preparation gate. Passing unit tests for
this reporting tool must never be interpreted as accepting Phase 3.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.contracts import ResponseDisposition, SystemBenchmarkResponse
from src.evals.system_benchmark.freeze_audit import audit_development_freeze
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.scoring import ScoringObservation, score_response

AUDIT = Path("experiments/evaluator-validation-20261017")


def audit() -> dict:
    controls_path = AUDIT / "controls.json"
    freeze_path = AUDIT / "frozen-inputs.json"
    payload = json.loads((ROOT / controls_path).read_text(encoding="utf-8"))
    freeze = json.loads((ROOT / freeze_path).read_text(encoding="utf-8"))
    tasks = load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")
    references = {ref.reference_solution_id: ref for ref in load_references(
        ROOT / "evals/system_benchmark/development_references.json"
    )}
    by_id = {task.case_id: task for task in tasks}
    if set(by_id) != set(payload["known_good"]):
        raise ValueError("known-good responses must cover exactly the current development tasks")
    control_ids = [item["id"] for item in payload["controls"]]
    if len(control_ids) != len(set(control_ids)):
        raise ValueError("duplicate audit control IDs")

    def score(task_id, candidate):
        task = by_id[task_id]
        response_payload = deepcopy(candidate["response"])
        response_payload["disposition"] = ResponseDisposition(response_payload["disposition"])
        response_payload["evidence_refs"] = tuple(response_payload.get("evidence_refs", ()))
        observation_payload = deepcopy(candidate["observation"])
        observation_payload["tool_calls"] = tuple(observation_payload.get("tool_calls", ()))
        result = score_response(
            task, references[task.reference_solution_id],
            SystemBenchmarkResponse(**response_payload),
            ScoringObservation(**observation_payload),
        )
        return result.to_dict()

    known_good = [{"task_id": task_id, "score": score(task_id, candidate)}
                  for task_id, candidate in sorted(payload["known_good"].items())]
    controls = []
    for control in payload["controls"]:
        candidate = deepcopy(payload["known_good"][control["task_id"]])
        candidate["response"].update(control["response_overrides"])
        candidate["observation"].update(control["observation_overrides"])
        result = score(control["task_id"], candidate)
        matches = (
            result["passed"] == control["expected_pass"]
            and set(control["intended_reason_codes"]).issubset(result["reason_codes"])
        )
        controls.append({**control, "evaluated_candidate": candidate,
                         "score": result, "matches_expectation": matches})

    extra_inputs = [str(controls_path), str(freeze_path),
                    "scripts/audit_system_benchmark_evaluator.py"]
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in sorted(set(freeze["sha256"]) | set(extra_inputs))}
    changed = [path for path, expected in freeze["sha256"].items()
               if hashes[path] != expected]
    counts = Counter(row["kind"] for row in controls)
    unresolved = [row["id"] for row in controls if not row["matches_expectation"]]
    good_passes = sum(row["score"]["passed"] for row in known_good)
    checks_pass = good_passes == len(known_good) and not unresolved and not changed
    return {
        "schema_version": "phase3-evaluator-audit-v1",
        "scope": "development-only, model-free preparation; no Phase 3 gate acceptance",
        "phase2_prerequisite": "not_qualified_by_this_audit",
        "phase3_accepted": False,
        "audit_checks_pass": checks_pass,
        "baseline_commit": freeze["baseline_commit"],
        "freeze_unchanged": not changed,
        "changed_frozen_paths": changed,
        "sha256": hashes,
        "known_good": {"passed": good_passes, "total": len(known_good), "results": known_good},
        "control_counts": dict(sorted(counts.items())),
        "controls_matching_expectations": sum(row["matches_expectation"] for row in controls),
        "unresolved_control_ids": unresolved,
        "controls": controls,
        "development_bank_freeze_audit": audit_development_freeze(tasks, references.values()).to_dict(),
        "benchmark_model_calls": 0,
        "evidence_runtime_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Also preserve this exact JSON report")
    args = parser.parse_args()
    report = audit()
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["audit_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
