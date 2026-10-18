#!/usr/bin/env python3
"""Capture actual model-facing metadata for implemented development adapters.

No live model, database, provider or held-out calls. Local captures cannot grant
independent parity acceptance or unblock comparative evaluation. Exit 2 means
review/qualification gates remain open; metadata mismatches return 1.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.baselines import StrongSingleExecutor
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.evals.system_benchmark.routing import natural_language_route, oracle_route, simple_heuristic_route
from src.evals.system_benchmark.runner import fingerprint_paths
from src.routing.deterministic_handlers import GROUPED_TEAM_METRICS_SQL

PROPOSAL = ROOT / "proposals/phase5-schema-integration-v1"
REFERENCE = PROPOSAL / "approved-tool-contract.json"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class MetadataCapture:
    """Fixed final response captures inputs, without executing any evidence tool."""

    def respond(self, messages, tools):
        self.messages = copy.deepcopy(messages)
        self.tools = copy.deepcopy(tools)
        return {"type": "final", "content": json.dumps({
            "disposition": "answer", "answer_text": "Offline metadata capture only.",
        })}


def _forbidden_tool(*_args, **_kwargs):
    raise AssertionError("schema capture must not execute an evidence tool")


def capture() -> dict:
    approved = json.loads(REFERENCE.read_text())
    approved_tools = {tool["name"]: tool for tool in approved["tools"]}
    tasks = {task.case_id: task for task in load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")}
    probes = (
        ("structured", tasks["SB-A01"]),
        ("documents", tasks["SB-C01"]),
        ("multi_source", replace(tasks["SB-D01"], request="Compare team blocker rates in the dataset and interpret them using the policy dictionary.")),
        ("none", replace(tasks["SB-E01"], request="Use private Slack messages to explain a delivery delay.")),
    )
    route_functions = {
        "oracle_routed": oracle_route,
        "natural_language_routed": lambda task: natural_language_route(task.request),
        "simple_heuristic_routed": lambda task: simple_heuristic_route(task.request),
    }
    profile_tools = {
        "none": (), "structured": ("query_clickhouse",), "documents": ("retrieve_policy",),
        "multi_source": ("query_clickhouse", "retrieve_policy"),
    }
    records = []
    for lane in ("strong_single", *route_functions):
        for profile, task in probes:
            model = MetadataCapture()
            if lane == "strong_single":
                executor = StrongSingleExecutor(model=model, model_id="offline-metadata-capture",
                    query_fn=_forbidden_tool, policy_fn=_forbidden_tool)
                expected_names = ("query_clickhouse", "retrieve_policy")
            else:
                executor = BoundedLocalExecutor(model=model, route_fn=route_functions[lane],
                    query_fn=_forbidden_tool, policy_fn=_forbidden_tool)
                expected_names = profile_tools[profile]
            execution = executor(task, 1, None)
            expected = [approved_tools[name] for name in expected_names]
            system_prompt = model.messages[0]["content"]
            records.append({
                "lane": lane, "probe_capability": profile,
                "request": task.request, "selected_route": execution.route_decision.route.value,
                "selected_capability": execution.route_decision.capability_profile.value,
                "delivered_tools": model.tools, "expected_tool_names": list(expected_names),
                "delivered_tool_payload_sha256": digest(model.tools),
                "tool_metadata_matches_approved": model.tools == expected,
                "system_prompt_matches_approved": system_prompt == approved["system_prompt"],
                "model_input_contains_request_only": model.messages[1] == {"role": "user", "content": task.request},
                "evidence_tool_calls": len(execution.observation.tool_calls),
                "scope": "scripted metadata capture, not a model response/quality trial",
            })
    paths = (
        "src/evals/system_benchmark/local_worker.py", "src/evals/system_benchmark/baselines.py",
        "src/evals/system_benchmark/workers.py", "src/evals/system_benchmark/routing.py",
        "src/evals/system_benchmark/contracts.py", "src/evals/system_benchmark/scoring.py",
        "src/evals/system_benchmark/references.py", "src/evals/system_benchmark/runner.py",
        "src/tools/clickhouse_readonly.py", "src/tools/policy_retrieval.py",
        "src/agents/ollama_client.py", "src/routing/deterministic_handlers.py",
        "evals/system_benchmark/development_tasks.json", "evals/system_benchmark/development_references.json",
        "proposals/phase5-schema-integration-v1/approved-tool-contract.json",
        "scripts/audit_baseline_schema_parity.py", "tests/system_benchmark/test_schema_metadata_parity.py",
    )
    return {
        "schema_version": "phase5-schema-integration-local-capture-v1",
        "schema_context_version": approved["schema_context_version"],
        "approved_metadata_source_commit": approved["source_commit"],
        "approved_query_tool_json_sha256": digest(approved_tools["query_clickhouse"]),
        "approved_policy_tool_json_sha256": digest(approved_tools["retrieve_policy"]),
        "local_capture_checks_pass": all(record["tool_metadata_matches_approved"]
            and record["system_prompt_matches_approved"] and record["model_input_contains_request_only"]
            and record["evidence_tool_calls"] == 0 for record in records),
        "capture_count": len(records), "captures": records,
        "independent_parity_review": "pending", "comparative_evaluation_approved": False,
        "comparison_blockers": ["independent_metadata_parity_review_pending", "phase3_evaluator_acceptance_pending",
                                "phase4_acceptance_pending", "exact_runtime_and_provenance_configuration_acceptance_pending"],
        "unverified_lanes": ["Hermes delegated Treatment B", "any architecture not explicitly captured here"],
        "deterministic_simple": {
            "model_facing_metadata": "not_applicable_no_model",
            "query_tool": "src.tools.clickhouse_readonly.query_clickhouse",
            "data_table": "agentic_analytics.delivery_work_items",
            "fixed_sql": GROUPED_TEAM_METRICS_SQL,
            "tool_contract": "existing dataset-scoped read-only tool; task permission and budget enforced",
            "live_data_equivalence_qualified": False,
        },
        "development_input_fingerprint": fingerprint_paths(ROOT, paths),
        "fingerprint_scope": "explicit local preparation inputs, not accepted benchmark-contract fingerprint",
        "live_model_calls": 0, "external_database_calls": 0,
        "historical_schema_less_branch": "sprint/phase5-readiness-20261017 at 1cc6fd9",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write this local capture report to the explicit path")
    parser.add_argument("--check", action="store_true", help="Compare against the committed local metadata-capture report")
    args = parser.parse_args()
    if args.output and args.check:
        parser.error("--output and --check are mutually exclusive")
    report = capture()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        expected = PROPOSAL / "local-metadata-captures.json"
        if not expected.is_file() or expected.read_text() != rendered:
            print("Local metadata capture artifact differs")
            return 1
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "schema_version", "local_capture_checks_pass", "capture_count", "approved_query_tool_json_sha256",
        "independent_parity_review", "comparative_evaluation_approved", "comparison_blockers",
    )}, indent=2))
    return 2 if report["local_capture_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
