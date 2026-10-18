#!/usr/bin/env python3
"""Read-only, model-free Phase 5 preparation; never grants phase acceptance.

Exit 2 means readiness remains blocked, not that contract validation crashed.
Only the two explicit development files and repository-local policy corpus
are read. No model, database, held-out bank, or worker executor is called.
The existing routing package also imports inert single-agent/tool definitions.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.contracts import BenchmarkSplit, SystemBenchmarkTask
from src.evals.system_benchmark.freeze_audit import audit_development_freeze
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import (
    ReferenceExpectation, load_references, parse_policy_evidence_ref,
    validate_task_reference,
)
from src.evals.system_benchmark.routing import (
    evaluate_route_decisions, natural_language_route, oracle_route,
    simple_heuristic_route,
)
from src.evals.system_benchmark.workers import (
    build_strong_single_invocation, build_worker_invocation,
)
from src.tools.policy_retrieval import MAX_TOP_K, retrieve_policy


def build_readiness_report(
    tasks: list[SystemBenchmarkTask], references: list[ReferenceExpectation],
) -> dict:
    """Inspect development interfaces; execution and human gates stay unverified."""
    if not tasks or any(task.split is not BenchmarkSplit.DEVELOPMENT for task in tasks):
        raise ValueError("readiness audit is development-only and requires tasks")
    audit = audit_development_freeze(tasks, references)
    by_id = {reference.reference_solution_id: reference for reference in references}
    valid_contracts = 0
    for task in tasks:
        reference = by_id.get(task.reference_solution_id)
        if reference is not None:
            try:
                validate_task_reference(task, reference)
            except ValueError:
                continue
            valid_contracts += 1

    policy_refs = sorted({
        ref for reference in references for ref in reference.allowed_evidence_refs
        if parse_policy_evidence_ref(ref) is not None
    })
    manifest = json.loads((ROOT / "evals/system_benchmark/corpus/manifest.json").read_text())
    policy_failures = []
    for ref in policy_refs:
        document_id, version, section_id = parse_policy_evidence_ref(ref)
        documents = [doc for doc in manifest["documents"]
            if (doc["document_id"], doc["version"]) == (document_id, version)]
        # Probe the public retriever at this version's effective date. This
        # checks identity reachability, not ranking for the task's user text.
        results = retrieve_policy(document_id, as_of=documents[0]["effective_date"],
            top_k=MAX_TOP_K) if len(documents) == 1 else []
        if not any((item.document_id, item.document_version, item.section_id)
            == (document_id, version, section_id) for item in results):
            policy_failures.append(ref)

    worker_failures = []
    for task in tasks:
        routed = build_worker_invocation(task, oracle_route(task))
        strong = build_strong_single_invocation(task)
        if not set(routed.allowed_tools).issubset(task.allowed_tools):
            worker_failures.append(f"{task.case_id}:routed_tools_outside_task")
        if set(strong.allowed_tools) != {"query_clickhouse", "retrieve_policy"}:
            worker_failures.append(f"{task.case_id}:strong_single_tools_incomplete")

    route_diagnostics = {}
    for name, classifier in (("oracle", oracle_route),
        ("natural_language", lambda task: natural_language_route(task.request)),
        ("simple_heuristic", lambda task: simple_heuristic_route(task.request))):
        route_diagnostics[name] = asdict(evaluate_route_decisions(
            (task, classifier(task)) for task in tasks))

    missing = {family: max(0, 3 - count) for family, count in audit.family_counts.items()}
    orphan_refs = sorted(set(by_id) - {task.reference_solution_id for task in tasks})
    blockers = ["phase2_to_4_acceptance_not_verified", *audit.reasons]
    if policy_failures:
        blockers.append("policy_reference_not_retrievable")
    if worker_failures:
        blockers.append("worker_contract_failure")
    if orphan_refs:
        blockers.append("orphan_references")
    blockers.extend(("known_good_responses_not_validated", "baseline_execution_not_verified",
        "human_task_reference_trial_audit_pending", "interface_freeze_not_approved"))
    return {
        "evidence_scope": "model_free_development_readiness_only",
        "phase5_ready": False,
        "phase2_to_4_acceptance": "not_verified_by_this_audit",
        "freeze_audit": audit.to_dict(),
        "missing_tasks_by_family": missing,
        "additional_tasks_required": sum(missing.values()),
        "reference_contracts_valid": valid_contracts,
        "orphan_reference_ids": orphan_refs,
        "policy_reference_identities_checked": len(policy_refs),
        "policy_reference_failures": policy_failures,
        "worker_contract_failures": worker_failures,
        "route_diagnostics": route_diagnostics,
        "known_good_response_validation": "not_performed",
        "baseline_execution": "not_performed",
        "blockers": blockers,
    }


def main() -> int:
    report = build_readiness_report(
        load_tasks(ROOT / "evals/system_benchmark/development_tasks.json"),
        load_references(ROOT / "evals/system_benchmark/development_references.json"),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
