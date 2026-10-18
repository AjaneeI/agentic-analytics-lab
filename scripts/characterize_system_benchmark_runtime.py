#!/usr/bin/env python3
"""Execute model-free D01 integration controls; unresolved defects exit 2.

SQL runs only on a disposable in-memory SQLite copy of the unchanged seed-42
generator output. This characterizes the worker/scorer boundary, not live
ClickHouse dialect or transport behavior, model quality, or phase acceptance.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.scoring import score_response
from src.tools.clickhouse_readonly import validate_read_only
from src.tools.policy_retrieval import retrieve_policy

AUDIT = Path("experiments/evaluator-validation-20261017")
TABLE = "agentic_analytics.delivery_work_items"
RATE = "100.0 * SUM(blocked) / COUNT(*) AS blocked_pct"
LABEL = ", 'active_work_items' AS scope"
RANK = " GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"

# Expected validity is stated independently of the frozen score. Never change
# these expectations merely to make the characterization command exit zero.
CASES = (
    ("D01-active-unlabelled", True,
     f"SELECT team, {RATE} FROM {TABLE} WHERE status != 'done'{RANK}",
     "The required active-work population is selected; the SQL need not emit a scope label."),
    ("D01-active-negated-equality", True,
     f"SELECT team, {RATE} FROM {TABLE} WHERE NOT (status = 'done'){RANK}",
     "Negated equality selects the same active population on this non-null fixture."),
    ("D01-active-cte", True,
     f"WITH active AS (SELECT * FROM {TABLE} WHERE status != 'done') "
     f"SELECT team, {RATE} FROM active{RANK}",
     "The CTE applies the active predicate before aggregation over the same population."),
    ("D01-active-labelled", True,
     f"SELECT team, {RATE}{LABEL} FROM {TABLE} WHERE status != 'done'{RANK}",
     "The same correct computation happens to include the exact row label required by the extractor."),
    ("D01-all-items-labelled", False,
     f"SELECT team, {RATE}{LABEL} FROM {TABLE}{RANK}",
     "A constant active label cannot make an unfiltered all-work denominator active."),
    ("D01-fabricated-rate-and-scope", False,
     f"SELECT team, 17.8 AS blocked_pct{LABEL} FROM {TABLE} WHERE team = 'Data' LIMIT 1",
     "Neither the literal percentage nor the literal scope is derived from the selected rows; no ranking is computed."),
    ("D01-or-bypass", False,
     f"SELECT team, {RATE}{LABEL} FROM {TABLE} WHERE status != 'done' OR 1 = 1{RANK}",
     "The OR branch includes completed work despite the active predicate and asserted scope label."),
    ("D01-empty-active-result", False,
     f"SELECT team, {RATE}{LABEL} FROM {TABLE} WHERE status != 'done' AND 1 = 0{RANK}",
     "An empty result cannot establish the winning team or supply structured evidence."),
)


class ScriptedModel:
    """A fixed three-step control sequence, never a model client."""

    def __init__(self, sql):
        self.steps = iter((
            {"type": "tool_call", "name": "query_clickhouse", "arguments": {"sql": sql}},
            {"type": "tool_call", "name": "retrieve_policy",
             "arguments": {"query": "Blocker rate percentage KPI dictionary", "top_k": 1}},
            {"type": "final", "content": json.dumps({
                "disposition": "answer",
                "answer_text": (
                    "Among active work items (status != done), Data has the highest blocker rate "
                    "at 17.8%. The KPI divides blocked active work by all active work in scope; "
                    "this does not establish causality."
                ),
            })},
        ))

    def respond(self, messages, tools):
        del messages, tools
        return next(self.steps)


def characterize() -> dict:
    task = next(task for task in load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")
                if task.case_id == "SB-D01")
    reference = next(ref for ref in load_references(ROOT / "evals/system_benchmark/development_references.json")
                     if ref.reference_solution_id == task.reference_solution_id)

    # Execute the original source in a disposable directory; do not import its
    # module-level RNG, cwd writes, or output into the benchmark workspace.
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts/generate_delivery_data.py")],
                       cwd=directory, capture_output=True, text=True, check=True)
        dataset = Path(directory) / "data/delivery_work_items.csv"
        dataset_sha = hashlib.sha256(dataset.read_bytes()).hexdigest()
        with dataset.open(newline="") as stream:
            records = list(csv.DictReader(stream))

    active_totals = Counter(row["team"] for row in records if row["status"] != "done")
    active_blocked = Counter()
    for row in records:
        if row["status"] != "done":
            active_blocked[row["team"]] += int(row["blocked"])

    cases = []
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("ATTACH DATABASE ':memory:' AS agentic_analytics")
        connection.execute(f"CREATE TABLE {TABLE} (team TEXT, status TEXT, blocked INTEGER)")
        connection.executemany(f"INSERT INTO {TABLE} VALUES (?, ?, ?)",
                               ((row["team"], row["status"], int(row["blocked"])) for row in records))
        for case_id, expected_pass, sql, rationale in CASES:
            actual_rows = []

            def execute_local(query):
                # Preserve the production tool's read-only validator and SQL;
                # substitute only its external transport with local execution.
                result = [dict(row) for row in connection.execute(validate_read_only(query))]
                actual_rows.extend(result)
                return result

            execution = BoundedLocalExecutor(
                model=ScriptedModel(sql), query_fn=execute_local, policy_fn=retrieve_policy,
            )(task, 1, None)
            score = score_response(task, reference, execution.response, execution.observation).to_dict()
            cases.append({
                "id": case_id, "expected_pass": expected_pass, "rationale": rationale,
                "sql": sql, "rows": actual_rows,
                "response": asdict(execution.response), "observation": asdict(execution.observation),
                "scripted_model_steps": execution.model_calls,
                "score": score, "matches_expectation": score["passed"] == expected_pass,
            })

    freeze_path = AUDIT / "frozen-inputs.json"
    freeze = json.loads((ROOT / freeze_path).read_text())
    extra_inputs = {
        str(freeze_path), "scripts/characterize_system_benchmark_runtime.py",
        "tests/system_benchmark/test_runtime_characterization.py",
        "src/evals/system_benchmark/local_worker.py", "src/evals/system_benchmark/runner.py",
        "src/evals/system_benchmark/workers.py", "src/evals/system_benchmark/routing.py",
        "src/tools/clickhouse_readonly.py", "src/tools/policy_retrieval.py",
        "src/agents/ollama_client.py",
    }
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for path in sorted(set(freeze["sha256"]) | extra_inputs)}
    changed = [path for path, expected in freeze["sha256"].items() if hashes[path] != expected]
    unresolved = [row["id"] for row in cases if not row["matches_expectation"]]
    return {
        "schema_version": "phase3-runtime-characterization-v1",
        "scope": "development-only deterministic worker/scorer characterization; not phase acceptance",
        "limitations": (
            "SQLite executes the common SELECT subset on temporary seed-42 data. "
            "SQLite arithmetic, types and dialect do not qualify live ClickHouse behavior. "
            "Scripted tool decisions and final prose are authored controls, not observed model behavior."
        ),
        "phase3_accepted": False, "phase2_prerequisite": "not_qualified_by_this_characterization",
        "baseline_commit": freeze["baseline_commit"],
        "freeze_unchanged": not changed, "changed_frozen_paths": changed,
        "sha256": hashes,
        "dataset": {
            "source": "unchanged scripts/generate_delivery_data.py executed in TemporaryDirectory",
            "seed": 42, "row_count": len(records), "csv_sha256": dataset_sha,
            "active_team_counts": {team: {"blocked": active_blocked[team], "total": active_totals[team]}
                                   for team in sorted(active_totals)},
        },
        "cases": cases, "cases_matching_expectations": len(cases) - len(unresolved),
        "unresolved_control_ids": unresolved, "audit_checks_pass": not unresolved and not changed,
        "live_model_calls": 0, "external_database_calls": 0,
        "local_sql_queries": len(cases), "local_policy_retrievals": len(cases),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Preserve the exact report printed to stdout")
    args = parser.parse_args()
    report = characterize()
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["audit_checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
