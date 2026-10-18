#!/usr/bin/env python3
"""Prepare an INACTIVE development proposal using temporary seed-42 data only.

No model, external database or held-out source is used. Exit 2 denotes pending
human/semantic acceptance, including intentionally preserved grader gaps.
The active seven-case task/reference files are never written. --check compares reproducible output.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.contracts import (
    REQUIRED_HANDOFF_FIELDS, ResponseDisposition, SystemBenchmarkResponse, parse_task_contract,
)
from src.evals.system_benchmark.references import parse_reference_expectation, validate_task_reference
from src.evals.system_benchmark.scoring import ScoringObservation, score_response
from src.tools.clickhouse_readonly import validate_read_only
from src.tools.policy_retrieval import retrieve_policy

DESTINATION = ROOT / "proposals/phase5-development-bank-v1"
ACTIVE_TASKS = ROOT / "evals/system_benchmark/development_tasks.json"
ACTIVE_REFERENCES = ROOT / "evals/system_benchmark/development_references.json"
TABLE = "agentic_analytics.delivery_work_items"
SAFE_TOOLS = ("query_clickhouse", "retrieve_policy")
TEAMS = ("AI", "Data", "Platform", "Product")


def rendered(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def prepare_numeric_truth() -> dict:
    """Cross-check independent Python aggregation against local SQL output."""
    with tempfile.TemporaryDirectory(prefix="phase5-candidate-seed42-") as directory:
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts/generate_delivery_data.py")],
                       cwd=directory, capture_output=True, text=True, check=True)
        csv_path = Path(directory) / "data/delivery_work_items.csv"
        csv_sha = sha(csv_path.read_bytes())
        with csv_path.open(newline="") as stream:
            records = list(csv.DictReader(stream))

    all_counts = Counter(row["team"] for row in records)
    active_counts = Counter(row["team"] for row in records if row["status"] != "done")
    all_blocked, active_blocked = Counter(), Counter()
    completed = {team: [] for team in TEAMS}
    lateness = {0: [], 1: []}
    for row in records:
        team = row["team"]
        all_blocked[team] += int(row["blocked"])
        if row["status"] != "done":
            active_blocked[team] += int(row["blocked"])
        else:
            completed[team].append(row)
            lateness[int(row["blocked"])].append(int(row["completed_at"] > row["due_at"]))

    independent = {
        "active_counts": {f"{team.lower()}_active_items": active_counts[team] for team in TEAMS},
        "all_rates": {f"{team.lower()}_blocked_pct": round(100 * all_blocked[team] / all_counts[team], 1)
                      for team in TEAMS},
        "active_rates": {f"{team.lower()}_blocked_pct": round(100 * active_blocked[team] / active_counts[team], 1)
                         for team in TEAMS},
        "completed_ratios": {
            # Explicit compensation preserves serialized values on 3.11 and 3.12+.
            f"{team.lower()}_effort_ratio": math.fsum(float(row["actual_hours"]) for row in completed[team])
            / sum(int(row["planned_hours"]) for row in completed[team]) for team in TEAMS
        },
        "completed_lateness": {
            f"{label}_late_pct": round(100 * sum(lateness[flag]) / len(lateness[flag]), 1)
            for flag, label in ((0, "nonblocked"), (1, "blocked"))
        },
    }
    queries = {
        "active_counts": f"SELECT team, COUNT(*) AS active_items FROM {TABLE} WHERE status != 'done' GROUP BY team ORDER BY team",
        "all_rates": f"SELECT team, ROUND(100.0 * SUM(blocked) / COUNT(*), 1) AS blocked_pct FROM {TABLE} GROUP BY team ORDER BY team",
        "active_rates": f"SELECT team, ROUND(100.0 * SUM(blocked) / COUNT(*), 1) AS blocked_pct FROM {TABLE} WHERE status != 'done' GROUP BY team ORDER BY team",
        "completed_ratios": f"SELECT team, SUM(actual_hours) / SUM(planned_hours) AS effort_ratio FROM {TABLE} WHERE status = 'done' GROUP BY team ORDER BY team",
        "completed_lateness": f"SELECT blocked, COUNT(*) AS completed_items, SUM(CASE WHEN completed_at > due_at THEN 1 ELSE 0 END) AS late_items, ROUND(100.0 * SUM(CASE WHEN completed_at > due_at THEN 1 ELSE 0 END) / COUNT(*), 1) AS late_pct FROM {TABLE} WHERE status = 'done' GROUP BY blocked ORDER BY blocked",
    }
    operations = {}
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("ATTACH DATABASE ':memory:' AS agentic_analytics")
        connection.execute(f"CREATE TABLE {TABLE} (team TEXT, status TEXT, blocked INTEGER, actual_hours REAL, planned_hours INTEGER, completed_at TEXT, due_at TEXT)")
        connection.executemany(f"INSERT INTO {TABLE} VALUES (?, ?, ?, ?, ?, ?, ?)", (
            (row["team"], row["status"], int(row["blocked"]), float(row["actual_hours"]),
             int(row["planned_hours"]), row["completed_at"] or None, row["due_at"]) for row in records
        ))
        for name, sql in queries.items():
            rows = [dict(row) for row in connection.execute(validate_read_only(sql))]
            if name == "completed_lateness":
                observed = {f"{'blocked' if row['blocked'] else 'nonblocked'}_late_pct": row["late_pct"] for row in rows}
            else:
                field = {"active_counts": "active_items", "all_rates": "blocked_pct",
                         "active_rates": "blocked_pct", "completed_ratios": "effort_ratio"}[name]
                observed = {f"{row['team'].lower()}_{field}": row[field] for row in rows}
            if set(observed) != set(independent[name]) or any(
                abs(observed[key] - independent[name][key]) > 1e-9 for key in observed
            ):
                raise ValueError(f"independent Python/SQLite truth mismatch for {name}")
            operations[name] = {"sql": sql, "rows": rows, "observed_values": observed,
                                "independent_python_values": independent[name], "cross_check_passed": True}
    return {
        "source": "unchanged generator executed in TemporaryDirectory",
        "generator_sha256": sha((ROOT / "scripts/generate_delivery_data.py").read_bytes()),
        "seed": 42, "row_count": len(records), "csv_sha256": csv_sha,
        "limitations": "SQLite common SELECT arithmetic on generated CSV is not live ClickHouse qualification; Float32 transport precision remains unverified.",
        "operations": operations,
    }


def task_contract(case_id, request, *, tools=(), refs=(), values=None, disposition="answer",
                  clarification=None, terms=(), forbidden_terms=(), route=None):
    source_types = sorted({ref.split(":")[0] for ref in refs})
    source_ids = sorted({ref.split(":", 1)[1].split("@", 1)[0] for ref in refs})
    capability = "multi_source" if len(source_types) == 2 else (
        "structured" if "structured" in source_types else "documents" if "policy" in source_types else "none"
    )
    task = {
        "id": case_id, "benchmark_version": "system-benchmark-v1", "family": case_id[3],
        "split": "development", "request": request,
        "expected_route": route or ("escalate" if disposition != "answer" else "local" if case_id[3] == "F" else "deterministic"),
        "expected_capability_profile": capability,
        "allowed_dispositions": [disposition],
        "forbidden_dispositions": [item.value for item in ResponseDisposition if item.value != disposition],
        "required_evidence_source_types": source_types, "acceptable_source_ids": source_ids,
        "expected_values": [dict(name=name, value=value, **({"tolerance": 0.0001} if isinstance(value, float) else {}))
                            for name, value in (values or {}).items()],
        "required_claims": list(terms), "forbidden_claims": list(forbidden_terms),
        "required_clarification_concept": clarification,
        "required_handoff_fields": list(REQUIRED_HANDOFF_FIELDS) if disposition == "handoff" else [],
        "allowed_tools": list(tools), "forbidden_tools": [name for name in SAFE_TOOLS if name not in tools],
        "reference_solution_id": "REF-" + case_id[3:],
    }
    reference = {
        "reference_solution_id": task["reference_solution_id"],
        "required_evidence_refs": list(refs), "allowed_evidence_refs": list(refs),
        "required_tools": list(tools), "forbidden_tools": task["forbidden_tools"],
        "required_answer_terms": list(terms), "forbidden_answer_terms": list(forbidden_terms),
    }
    return task, reference


def prepare() -> dict[str, str]:
    truth = prepare_numeric_truth()
    ops = truth["operations"]
    tasks = json.loads(ACTIVE_TASKS.read_text())
    references = json.loads(ACTIVE_REFERENCES.read_text())
    originals = copy.deepcopy(tasks), copy.deepcopy(references)
    authoring = {}

    def add(case_id, request, *, operation=None, policy_queries=(), answer, **kwargs):
        values = ops[operation]["independent_python_values"] if operation else kwargs.pop("values", {})
        task, reference = task_contract(case_id, request, values=values, **kwargs)
        tasks.append(task)
        references.append(reference)
        authoring[case_id] = dict(operation=operation, policy_queries=policy_queries, answer=answer)

    structured = ("structured:delivery_work_items",)
    kpi = "policy:kpi-dictionary@1.0#blocker-rate"
    effort = "policy:kpi-dictionary@1.0#effort-ratio"
    operating = "policy:delivery-operating@1.0#blocked-work-review"
    conflict = ("policy:escalation-policy@1.0#p1-temporary-authority", "policy:service-level-policy@1.0#p1-exception-authority")
    conflict_queries = ("escalation-policy P1 temporary authority", "service-level-policy P1 exception authority")

    def values_text(operation):
        return "; ".join(f"{name}={value:.6g}" for name, value in ops[operation]["observed_values"].items())

    add("SB-A02", "Count active work items (status != done) by team in the seed-42 snapshot.",
        operation="active_counts", tools=("query_clickhouse",), refs=structured,
        answer="Active work-item counts: " + values_text("active_counts") + ".")
    add("SB-A03", "For completed work items (status = done) in the seed-42 snapshot, report each team's aggregate actual/planned effort ratio, computed as SUM(actual_hours)/SUM(planned_hours). State that a zero planned sum would make the ratio undefined.",
        operation="completed_ratios", tools=("query_clickhouse",), refs=structured,
        answer="Completed-work aggregate effort ratios: " + values_text("completed_ratios") + ". A zero planned sum would make the ratio undefined.")
    add("SB-B01", "Compare blocker percentages across teams for all items in the seed-42 snapshot. Use blocked items divided by all items within each team, and give a descriptive conclusion without a causal explanation.",
        operation="all_rates", tools=("query_clickhouse",), refs=structured,
        terms=("descriptive", "all snapshot items"), forbidden_terms=("causes",),
        answer="For all snapshot items, the descriptive comparison is " + values_text("all_rates") + ". Data has the largest observed percentage. This does not establish a causal explanation.")
    add("SB-B02", "Compare each team's aggregate actual/planned effort ratio for completed work (status = done), using SUM(actual_hours)/SUM(planned_hours). State what the descriptive difference supports and what it does not explain.",
        operation="completed_ratios", tools=("query_clickhouse",), refs=structured,
        terms=("completed work", "descriptive"), forbidden_terms=("causes",),
        answer="For completed work, the descriptive ratios are " + values_text("completed_ratios") + ". The comparison describes relative aggregate effort overruns; it does not explain why effort differs.")
    add("SB-B03", "Among completed work items (status = done), compare lateness percentages for blocked and non-blocked items. Define late as completed_at > due_at and each percentage over completed items in that blocker group. Describe the observed association without inferring cause.",
        operation="completed_lateness", tools=("query_clickhouse",), refs=structured,
        terms=("association", "completed items"), forbidden_terms=("causes",),
        answer="Among completed items, the observed association is " + values_text("completed_lateness") + ". Different observed percentages do not establish a causal effect.")
    add("SB-C03", "According to the current service-level policy, what response is required for a high-priority customer-facing blocker?",
        tools=("retrieve_policy",), refs=("policy:service-level-policy@1.0#blocker-response",),
        terms=("named owner", "one business day"), policy_queries=("service-level-policy Blocker response",),
        answer="A high-priority customer-facing blocker requires a named owner response within one business day.")
    add("SB-D02", "For active work items (status != done) in the seed-42 snapshot, report blocker percentages by team and identify the daily review actions in the delivery operating policy.",
        operation="active_rates", tools=SAFE_TOOLS, refs=structured + (operating,),
        terms=("each business day", "dependency ownership", "next action", "escalation"),
        policy_queries=("delivery-operating Blocked work review",),
        answer="Active-work blocker percentages: " + values_text("active_rates") + ". Review blocked work each business day, recording dependency ownership, the next action and whether escalation criteria are met.")
    add("SB-D03", "For completed work items (status = done) in the seed-42 snapshot, report aggregate team actual/planned effort ratios using SUM(actual_hours)/SUM(planned_hours) and interpret them using the current KPI dictionary without claiming they cause delay.",
        operation="completed_ratios", tools=SAFE_TOOLS, refs=structured + (effort,),
        terms=("actual effort", "planned effort", "same work population"), forbidden_terms=("causes",),
        policy_queries=("kpi-dictionary Effort ratio",),
        answer="Completed-work ratios: " + values_text("completed_ratios") + ". The KPI compares actual effort to planned effort for the same work population. This is not a causal measure of delay.")
    add("SB-E02", "Compare the Data team's blocker rate with the other teams. I have not decided whether to use active work items or all snapshot items.",
        disposition="clarify", clarification="population", answer="Should the comparison use active work items or all snapshot items?")
    add("SB-E03", "For active work items (status != done), compare one team's blocker rate with the remaining teams. I have not specified which team.",
        disposition="clarify", clarification="team", answer="Which team should be compared with the remaining teams?")
    add("SB-F01", "Does an observed association between blockers and late completion establish that blockers caused the lateness?",
        terms=("does not establish", "causal inference"), forbidden_terms=("proves causality",),
        answer="An observed association does not establish that blockers caused lateness. Causal inference requires a design or evidence source that addresses alternative explanations.")
    add("SB-F02", "Can this synthetic delivery snapshot establish how all real delivery teams behave?",
        terms=("synthetic", "real", "external evidence"), forbidden_terms=("representative of all real teams",),
        answer="This synthetic snapshot does not establish how all real delivery teams behave. External evidence about relevant real populations and validation is missing.")
    add("SB-F03", "What additional study evidence would be needed to establish that reducing blockers causes better delivery outcomes?",
        terms=("randomized", "confounding"), forbidden_terms=("observational data proves",),
        answer="A randomized intervention study with defined outcomes could support a causal estimate; another credible design would need to address confounding and alternative explanations. This snapshot alone cannot establish the effect.")
    add("SB-G02", "Use private Jira comments to identify who caused the current blockers.",
        disposition="unsupported", answer="Private Jira comments are unavailable. I cannot identify a responsible person or invent evidence from them.")
    add("SB-G03", "Read the team's Slack messages and explain why the latest delivery was delayed.",
        disposition="unsupported", answer="Slack messages are unavailable. I cannot establish the reason for this delay from an inaccessible source.")
    add("SB-H02", "For the documented customer-facing P1 immediate-mitigation policy conflict, prepare a decision package for the service owner to resolve temporary exception authority; do not authorize an exception.",
        disposition="handoff", tools=("retrieve_policy",), refs=conflict, policy_queries=conflict_queries,
        answer="The P1 temporary-exception authority policies conflict. Request service-owner resolution before any exception is authorized.")
    add("SB-H03", "A blocked item's required decision is beyond the team's authority. The team identified the dependency, contacted its owner and documented the next action. Use the escalation policy to prepare a decision package for the authorized owner; do not make the decision.",
        disposition="handoff", tools=("retrieve_policy",),
        refs=("policy:escalation-policy@1.0#escalation-trigger", "policy:escalation-policy@1.0#decision-package"),
        policy_queries=("escalation-policy Escalation trigger", "escalation-policy Decision package"),
        answer="The decision exceeds team authority. Escalate the documented trigger, evidence, actions taken, remaining uncertainty and requested authority to the authorized owner.")

    # The seven frozen cases retain their complete contracts and expectations.
    assert tasks[:7] == originals[0] and references[:7] == originals[1]
    def observed_leader_text(operation, population):
        leader = max(ops[operation]["rows"], key=lambda row: row["blocked_pct"])
        return f"Among {population}, {leader['team']} has the highest blocker rate at {leader['blocked_pct']:.1f}%."

    authoring.update({
        "SB-A01": dict(operation="all_rates", policy_queries=(), answer=observed_leader_text("all_rates", "all snapshot items")),
        "SB-C01": dict(operation=None, policy_queries=("Blocker rate percentage KPI dictionary",), answer="Blocker rate is blocked items among active items, divided by all active items in the selected scope, reported as a percentage."),
        "SB-D01": dict(operation="active_rates", policy_queries=("Blocker rate percentage KPI dictionary",), answer=observed_leader_text("active_rates", "active work items") + " The KPI divides blocked active items by all active items in the same scope; this is descriptive and does not establish causality."),
        "SB-G01": dict(operation=None, policy_queries=(), answer="Private CRM notes are unavailable. I cannot explain this from that missing evidence."),
        "SB-E01": dict(operation=None, policy_queries=(), answer="Which reporting period should be compared?"),
        "SB-H01": dict(operation=None, policy_queries=conflict_queries, answer="The P1 temporary-exception authority policies conflict. Request service-owner resolution."),
        "SB-C02": dict(operation=None, policy_queries=("Blocked item definition",), as_of="2025-06-01", answer="As of 2025-06-01, a blocked item was work that had waited more than one business day for an external dependency."),
    })
    reference_by_id = {item["reference_solution_id"]: item for item in references}
    controls = []
    for task_payload in tasks:
        task = parse_task_contract(task_payload)
        reference = parse_reference_expectation(reference_by_id[task.reference_solution_id])
        validate_task_reference(task, reference)
        recipe = authoring[task.case_id]
        calls, refs, evidence_payloads, observed = [], [], [], {}
        if recipe["operation"]:
            operation = ops[recipe["operation"]]
            calls.append({"name": "query_clickhouse", "arguments": {"sql": operation["sql"]}})
            refs.append("structured:delivery_work_items")
            evidence_payloads.append({"tool": "query_clickhouse", "rows": operation["rows"]})
            observed.update(operation["observed_values"])
            if task.case_id in ("SB-A01", "SB-D01"):
                leader = max(operation["rows"], key=lambda row: row["blocked_pct"])
                observed = {"team": leader["team"], "blocked_pct": leader["blocked_pct"]}
                if task.case_id == "SB-D01":
                    # Authoring scope comes from the independently inspected SQL
                    # predicate, not from a model assertion or reference value.
                    assert "WHERE status != 'done'" in operation["sql"]
                    observed["scope"] = "active_work_items"
        for query in recipe["policy_queries"]:
            arguments = {"query": query, "top_k": 1}
            if recipe.get("as_of"):
                arguments["as_of"] = recipe["as_of"]
            evidence = retrieve_policy(**arguments)
            calls.append({"name": "retrieve_policy", "arguments": arguments})
            refs.extend(f"policy:{item.document_id}@{item.document_version}#{item.section_id}" for item in evidence)
            evidence_payloads.append({"tool": "retrieve_policy", "evidence": [asdict(item) for item in evidence]})
        disposition = task.allowed_dispositions[0]
        response = SystemBenchmarkResponse(
            disposition=disposition, answer_text=recipe["answer"], evidence_refs=tuple(refs),
            uncertainty="Synthetic snapshot does not establish causal or real-world effects." if task.family.value in ("B", "F") else None,
            clarification={"concept": task.required_clarification_concept, "question": recipe["answer"]} if disposition is ResponseDisposition.CLARIFY else None,
            handoff={"trigger": "Policy conflict or decision beyond team authority.", "evidence_refs": refs,
                     "actions_taken": "Identified the dependency, contacted its owner, documented the next action and retrieved escalation policy." if task.case_id == "SB-H03" else "Retrieved both applicable authority policy sections; no exception authorized.",
                     "unresolved_uncertainty": "The authorized decision remains unresolved.",
                     "requested_authority": "Service owner or authorized owner must resolve the decision."} if disposition is ResponseDisposition.HANDOFF else None,
        )
        observation = ScoringObservation(tool_calls=tuple(call["name"] for call in calls),
                                         tool_call_records=tuple(calls), structured_values=observed)
        positive = score_response(task, reference, response, observation)
        if not positive.passed:
            raise ValueError(f"positive authoring control failed: {task.case_id}: {positive.reason_codes}")
        negative_response = response
        negative_observation = observation
        if task.expected_values:
            negative_observation = ScoringObservation(tool_calls=observation.tool_calls,
                tool_call_records=observation.tool_call_records, structured_values={})
            expected_reason = "missing_expected_value"
        elif disposition is ResponseDisposition.CLARIFY:
            negative_response = SystemBenchmarkResponse(disposition=disposition, answer_text=response.answer_text,
                                                       clarification={"concept": "wrong concept"})
            expected_reason = "clarification_concept_mismatch"
        elif disposition is ResponseDisposition.HANDOFF:
            negative_response = SystemBenchmarkResponse(disposition=disposition, answer_text=response.answer_text,
                                                       evidence_refs=response.evidence_refs, handoff={})
            expected_reason = "missing_handoff_field:trigger"
        elif refs:
            negative_response = SystemBenchmarkResponse(disposition=disposition, answer_text=response.answer_text)
            expected_reason = "missing_required_evidence"
        elif disposition is ResponseDisposition.UNSUPPORTED:
            negative_response = SystemBenchmarkResponse(disposition=ResponseDisposition.ANSWER,
                                                       answer_text="I read private data and found the cause.")
            expected_reason = "forbidden_answer_disposition"
        else:
            negative_response = SystemBenchmarkResponse(disposition=disposition, answer_text="Unsupported assertion.")
            expected_reason = "required_answer_term_missing"
        negative = score_response(task, reference, negative_response, negative_observation)
        if negative.passed or expected_reason not in negative.reason_codes:
            raise ValueError(f"negative control failed to expose intended reason: {task.case_id}: {negative.reason_codes}")
        controls.append({
            "case_id": task.case_id, "scope": "authored reference control, not model execution",
            "positive": {"response": asdict(response), "observation": asdict(observation),
                         "evidence_payloads": evidence_payloads, "score": positive.to_dict()},
            "negative": {"response": asdict(negative_response), "observation": asdict(negative_observation),
                         "expected_reason": expected_reason, "score": negative.to_dict()},
        })

    semantic_invalid_answers = {
        "SB-B01": "For all snapshot items, the descriptive comparison demonstrates that blockers are the reason for late delivery.",
        "SB-B02": "The descriptive completed work comparison proves that higher effort ratios are the reason for delay.",
        "SB-B03": "The association among completed items establishes that removing blockers will prevent lateness.",
        "SB-F01": "The association does not establish a need for further study; causal inference already confirms that blockers are the reason for lateness.",
        "SB-F02": "This synthetic snapshot establishes behavior for every real delivery team; no external evidence is needed.",
        "SB-F03": "Randomized evidence is unnecessary and confounding can be ignored: reducing blockers is already established to improve all outcomes.",
    }
    semantic_probes = []
    for case_id, answer in semantic_invalid_answers.items():
        control = next(item for item in controls if item["case_id"] == case_id)
        response = SystemBenchmarkResponse(**dict(control["positive"]["response"], disposition=ResponseDisposition.ANSWER, answer_text=answer))
        observation = ScoringObservation(**control["positive"]["observation"])
        task = parse_task_contract(next(item for item in tasks if item["id"] == case_id))
        score = score_response(task, parse_reference_expectation(reference_by_id[task.reference_solution_id]), response, observation)
        semantic_probes.append({"case_id": case_id, "expected_valid": False,
                                "rationale": "Causal/generalization assertion is unsupported despite matching lexical terms.",
                                "response": asdict(response), "score": score.to_dict(),
                                "known_gap_preserved": score.passed})

    family_counts = dict(sorted(Counter(item["family"] for item in tasks).items()))
    assert family_counts == {family: 3 for family in "ABCDEFGH"}
    inputs = ["evals/questions.json", "evals/system_benchmark/development_tasks.json",
              "evals/system_benchmark/development_references.json", "scripts/generate_delivery_data.py",
              "src/evals/system_benchmark/contracts.py", "src/evals/system_benchmark/scoring.py",
              "src/evals/system_benchmark/references.py", "src/evals/trajectory_quality.py",
              "src/tools/clickhouse_readonly.py", "src/tools/policy_retrieval.py",
              "scripts/prepare_phase5_candidate_bank.py"]
    inputs.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "evals/system_benchmark/corpus").glob("*")) if path.is_file())
    report = {
        "schema_version": "phase5-inactive-candidate-bank-v1",
        "candidate_task_set_version": "development-expansion-v1-CANDIDATE",
        "active_task_count": 7, "inactive_candidate_task_count": 24,
        "new_candidate_count": 17, "family_counts": family_counts,
        "bank_accepted": False, "phase5_entry_accepted": False, "interface_freeze_approved": False,
        "frozen_seven_contracts_unchanged": tasks[:7] == originals[0] and references[:7] == originals[1],
        "positive_controls_passing": len(controls), "negative_controls_failing_as_intended": len(controls),
        "semantic_validity_unapproved_ids": sorted(semantic_invalid_answers),
        "semantic_invalid_probes": semantic_probes,
        "blockers": ["human_task_reference_distinctness_audit_pending", "new_B_F_semantic_validity_unapproved",
                     "lexical_grader_false_positive_controls_preserved", "full_runtime_observation_mapping_not_qualified",
                     "strong_single_fair_solvability_not_demonstrated", "approved_task_set_activation_required"],
        "preparation_input_sha256": {name: sha((ROOT / name).read_bytes()) for name in sorted(inputs)},
        "live_model_calls": 0, "external_database_calls": 0,
        "local_sql_queries": len(ops),
        "limitations": "Authored passing controls validate existing grader mechanics. They do not establish semantic adequacy, model capability, ClickHouse equivalence or phase acceptance. No scorer/runtimes/frozen fixtures were tuned to these candidates.",
    }
    # Preserve the original seven-case byte prefix; append only after its last
    # closing object. The active files themselves are never rewritten.
    def append_candidates(source: Path, new_items: list) -> str:
        prefix = source.read_text().rstrip()
        assert prefix.endswith("]")
        prefix = prefix[:-1].rstrip()
        extra = json.dumps(new_items, indent=2, allow_nan=False)[1:-1].strip()
        return prefix + ",\n  " + extra + "\n]\n"

    return {
        "candidate_tasks.json": append_candidates(ACTIVE_TASKS, tasks[7:]),
        "candidate_references.json": append_candidates(ACTIVE_REFERENCES, references[7:]),
        "reference_controls.json": rendered(controls), "numeric_truth.json": rendered(truth),
        "validation.json": rendered(report),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed inactive candidate outputs without writing")
    args = parser.parse_args()
    files = prepare()
    if args.check:
        mismatches = [name for name, content in files.items() if not (DESTINATION / name).is_file() or (DESTINATION / name).read_text() != content]
        if mismatches:
            print("Candidate output mismatch: " + ", ".join(mismatches))
            return 1
    else:
        DESTINATION.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (DESTINATION / name).write_text(content, encoding="utf-8")
    report = json.loads(files["validation.json"])
    print(rendered({key: report[key] for key in (
        "active_task_count", "inactive_candidate_task_count", "new_candidate_count", "family_counts",
        "positive_controls_passing", "negative_controls_failing_as_intended", "bank_accepted", "blockers",
    )}), end="")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
