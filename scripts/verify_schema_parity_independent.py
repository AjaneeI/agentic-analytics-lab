#!/usr/bin/env python3
"""Passive, model-free independent metadata review of one exact checkout.

No activation, external application, model, database, paid provider or held-out
access is authorized by this script. It writes only the explicit JSON output.
Bytecode writing is disabled. A successful review verifies metadata parity,
not benchmark/model quality or permission to run an architecture comparison.
"""

from __future__ import annotations

import argparse
import ast
import copy
from contextlib import ExitStack, chdir
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ACTIVATION = "644a68d75cf6743d3daaace51f42a0571747417c"
ACTIVATION_SOURCE_SHA = "b0e9c39dbcc868fd6a346778a2a9c6b3418aa828d7b57e8852026623a3b8f289"
QUERY_JSON_SHA = "0a9350a1cf0f467c4f934e1f77f63051085e5efe86b1a64147192eca8ab365c9"


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


def extract_activation_contract(root):
    path = "src/evals/system_benchmark/local_worker.py"
    source = git(root, "show", f"{ACTIVATION}:{path}")
    assert hashlib.sha256(source).hexdigest() == ACTIVATION_SOURCE_SHA
    constants = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("_QUERY_TOOL", "_POLICY_TOOL", "_SYSTEM_PROMPT"):
                    value = node.value
                    constants[target.id] = (ast.literal_eval(value.func.value).strip()
                                            if isinstance(value, ast.Call) else ast.literal_eval(value))
    tools = [constants["_QUERY_TOOL"], constants["_POLICY_TOOL"]]
    assert canonical_digest(tools[0]) == QUERY_JSON_SHA
    return constants["_SYSTEM_PROMPT"], {tool["name"]: tool for tool in tools}


def network_guards(stack, rejected):
    def deny(*args, **kwargs):
        rejected.append("forbidden_network_attempt")
        raise AssertionError("Independent review forbids network access")
    for name in ("connect", "connect_ex", "sendto"):
        stack.enter_context(patch.object(socket.socket, name, deny))
    for name in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        stack.enter_context(patch("socket." + name, deny))


class Capture:
    model = "independent-offline"

    def respond(self, messages, tools):
        self.messages = copy.deepcopy(messages)
        self.tools = copy.deepcopy(tools)
        return {"type": "final", "content": json.dumps({
            "disposition": "answer", "answer_text": "Independent metadata capture only.",
        })}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-tests", action="store_true", help="Also run the local suite with network blocked")
    args = parser.parse_args()
    root = args.repository.resolve()
    head = git(root, "rev-parse", "HEAD").decode().strip()
    assert head == args.expected_head, (head, args.expected_head)
    assert git(root, "status", "--porcelain") == b"", "Review requires a clean exact checkout"
    def deny_heldout_source(event, arguments):
        if event == "open" and isinstance(arguments[0], (str, bytes)):
            raw_path = arguments[0].decode() if isinstance(arguments[0], bytes) else arguments[0]
            path = Path(raw_path).resolve()
            if root in path.parents and ("heldout" in str(path).casefold() or "held-out" in str(path).casefold()):
                raise AssertionError("Independent review forbids held-out source access")
    sys.addaudithook(deny_heldout_source)
    prompt, approved_tools = extract_activation_contract(root)
    sys.path.insert(0, str(root))

    from src.evals.system_benchmark.baselines import (
        DeterministicBaselineDeclined, DeterministicSimpleExecutor, StrongSingleExecutor,
    )
    from src.evals.system_benchmark.contracts import ResponseDisposition, StructuredExpectation
    from src.evals.system_benchmark.loader import load_tasks
    from src.evals.system_benchmark.local_worker import BoundedLocalExecutor, DEFAULT_LOCAL_MODEL
    from src.evals.system_benchmark.routing import natural_language_route, oracle_route, simple_heuristic_route

    assert DEFAULT_LOCAL_MODEL == "hermes-local:qwen3.5-9b"
    tasks = {task.case_id: task for task in load_tasks(root / "evals/system_benchmark/development_tasks.json")}
    probes = (
        ("structured", tasks["SB-A01"]), ("documents", tasks["SB-C01"]),
        ("multi_source", replace(tasks["SB-D01"], request=
            "Compare team blocker rates in the dataset and interpret them using the policy dictionary.")),
        ("none", replace(tasks["SB-E01"], request="Use private Slack messages to explain a delivery delay.")),
    )
    profiles = {"structured": ["query_clickhouse"], "documents": ["retrieve_policy"],
                "multi_source": ["query_clickhouse", "retrieve_policy"], "none": []}
    lanes = {"strong_single": None, "oracle_routed": oracle_route,
             "natural_language_routed": lambda task: natural_language_route(task.request),
             "simple_heuristic_routed": lambda task: simple_heuristic_route(task.request)}
    canaries = {"case_id": "SECRET-CASE", "reference_solution_id": "SECRET-REFERENCE",
               "expected_value": "SECRET-TRUTH"}
    records, rejected = [], []

    def denied(*_args, **_kwargs):
        rejected.append("forbidden_live_client_or_tool_attempt")
        raise AssertionError("Independent review forbids live model/database/evidence calls")

    with ExitStack() as stack:
        network_guards(stack, rejected)
        stack.enter_context(patch("src.agents.ollama_client.OllamaModelClient.__init__", denied))
        stack.enter_context(patch("src.agents.ollama_client.OllamaModelClient.respond", denied))
        stack.enter_context(patch("urllib.request.urlopen", denied))
        for lane, route in lanes.items():
            for profile, original in probes:
                task = replace(original, case_id=canaries["case_id"],
                               reference_solution_id=canaries["reference_solution_id"],
                               expected_values=(StructuredExpectation("canary", canaries["expected_value"]),))
                model = Capture()
                kwargs = dict(model=model, query_fn=denied, policy_fn=denied)
                executor = (StrongSingleExecutor(model_id="independent-offline", **kwargs) if lane == "strong_single"
                            else BoundedLocalExecutor(route_fn=route, **kwargs))
                execution = executor(task, 1, None)
                names = ["query_clickhouse", "retrieve_policy"] if lane == "strong_single" else profiles[profile]
                assert model.tools == [approved_tools[name] for name in names], (lane, profile)
                assert model.messages == [{"role": "system", "content": prompt},
                                          {"role": "user", "content": task.request}], (lane, profile)
                serialized = json.dumps([model.messages, model.tools])
                assert all(value not in serialized for value in canaries.values()), (lane, profile)
                assert execution.observation.tool_calls == () and execution.model_calls == 1
                records.append({
                    "lane": lane, "probe_capability": profile, "request": task.request,
                    "expected_tool_names": names, "delivered_messages": model.messages,
                    "delivered_tools": model.tools, "delivered_tools_sha256": canonical_digest(model.tools),
                    "matches_activation_source": True, "hidden_metadata_canaries_absent": True,
                    "scripted_model_steps": execution.model_calls, "evidence_tool_calls": 0,
                })

        handoff_checks = []
        for allow, forbid in (
            (tasks["SB-H01"].allowed_dispositions, tasks["SB-H01"].forbidden_dispositions),
            ((ResponseDisposition.ANSWER,), ()),
        ):
            task = replace(tasks["SB-H01"], request=tasks["SB-A01"].request,
                           allowed_tools=("query_clickhouse",), forbidden_tools=(),
                           allowed_dispositions=allow, forbidden_dispositions=forbid)
            query = Mock(side_effect=denied)
            try:
                DeterministicSimpleExecutor(query_fn=query)(task, 1, None)
            except DeterministicBaselineDeclined:
                pass
            else:
                raise AssertionError("Family H must decline before deterministic evidence gathering")
            assert query.call_count == 0
            handoff_checks.append({"family": "H", "answer_explicitly_allowed": ResponseDisposition.ANSWER in allow,
                                   "declined_before_tools": True, "query_calls": 0})

    assert len(records) == 16 and not rejected
    suite_result = {"executed": False}
    if args.run_tests:
        # Unit tests may construct inert local clients or mock transports. Block
        # actual network entry points, while leaving their own offline mocks valid.
        with ExitStack() as stack:
            network_guards(stack, rejected)
            stack.enter_context(chdir(root))
            suite = unittest.defaultTestLoader.discover(str(root / "tests"))
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
            assert result.wasSuccessful(), (result.failures, result.errors)
            suite_result = {"executed": True, "tests": result.testsRun, "failures": len(result.failures),
                            "errors": len(result.errors), "skipped": len(result.skipped), "network_blocked": True}
    assert not rejected

    snapshot_path = root / "proposals/phase5-schema-integration-v1/local-metadata-captures.json"
    snapshot = json.loads(snapshot_path.read_text())
    assert snapshot["capture_count"] == 16 and snapshot["local_capture_checks_pass"]
    for relative, expected in snapshot["development_input_fingerprint"]["contract_files"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative
    paths = (
        "src/evals/system_benchmark/local_worker.py", "src/evals/system_benchmark/baselines.py",
        "src/evals/system_benchmark/workers.py", "src/evals/system_benchmark/routing.py",
        "src/evals/system_benchmark/contracts.py", "src/evals/system_benchmark/scoring.py",
        "src/evals/system_benchmark/references.py", "src/evals/system_benchmark/runner.py",
        "src/tools/clickhouse_readonly.py", "src/tools/policy_retrieval.py", "src/agents/ollama_client.py",
        "src/routing/deterministic_handlers.py", "evals/system_benchmark/development_tasks.json",
        "evals/system_benchmark/development_references.json", "docs/phase5-baseline-adapters.md",
        "proposals/phase5-schema-integration-v1/approved-tool-contract.json",
        "proposals/phase5-schema-integration-v1/local-metadata-captures.json",
        "scripts/audit_baseline_schema_parity.py", "tests/system_benchmark/test_schema_metadata_parity.py",
        "scripts/prepare_phase5_candidate_bank.py", "proposals/phase5-development-bank-v1/validation.json",
        "proposals/phase5-development-bank-v1/README.md",
    )
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--repository", str(root),
               "--expected-head", head, "--output", str(args.output.resolve())]
    if args.run_tests:
        command.append("--run-tests")
    report = {
        "schema_version": "independent-schema-parity-review-v1", "reviewed_commit": head,
        "independent_metadata_parity_verified": True, "capture_count": len(records), "captures": records,
        "canary_inputs": canaries, "canary_assertion": "All canary values absent from complete actual messages and tool JSON",
        "activation_source": {"commit": ACTIVATION, "path": "src/evals/system_benchmark/local_worker.py",
                              "sha256": ACTIVATION_SOURCE_SHA, "extraction": "AST from git show, independent of proposal reference JSON"},
        "approved_query_tool_json_sha256": QUERY_JSON_SHA,
        "approved_policy_tool_json_sha256": canonical_digest(approved_tools["retrieve_policy"]),
        "review_source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths},
        "independent_reproducer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "commands": {"reproduce_review": shlex.join(command),
                     "inspect_activation_source": "git show " + ACTIVATION + ":src/evals/system_benchmark/local_worker.py",
                     "author_capture_consistency": "python3 -B scripts/audit_baseline_schema_parity.py --check",
                     "author_capture_expected_exit": 2},
        "guards": {"network_connection_and_DNS_blocked": True, "live_model_constructor_and_method_blocked_during_captures": True,
                   "evidence_callbacks_and_HTTP_transport_blocked_during_captures": True,
                   "heldout_source_open_blocked": True, "rejected_attempts": rejected},
        "handoff_pretool_regressions": handoff_checks, "test_suite": suite_result,
        "runtime_default_unchanged": DEFAULT_LOCAL_MODEL, "comparison_anchor": "qwen2.5:7b remains a separate frozen contract",
        "live_model_calls": 0, "external_database_calls": 0, "heldout_access": False,
        "phase2_qualified": False, "phase3_accepted": False, "phase4_accepted": False,
        "phase5_entry_accepted": False, "comparative_evaluation_approved": False,
        "limitations": ["Scripted metadata capture only; no model-quality or live execution evidence.",
                        "Routed lanes receive capability-specific subsets; strong single receives both safe affordances with separate execution permissions.",
                        "Hermes delegated Treatment B and uncaptured architectures remain unverified.",
                        "Scope/metric validity, evaluator acceptance, exact runtime configuration and scientific phase gates remain separate.",
                        "This report is local evidence until its exact bytes and reproducer are versioned by the coordinator."],
    }
    assert git(root, "rev-parse", "HEAD").decode().strip() == head
    assert git(root, "status", "--porcelain") == b"", "Review changed repository state"
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("reviewed_commit", "capture_count", "independent_metadata_parity_verified", "test_suite")}, sort_keys=True))


if __name__ == "__main__":
    main()
