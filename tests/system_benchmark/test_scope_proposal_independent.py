"""Independent executed-SQL review of the inactive runtime scope proposal.

Run normally with unittest; use --output PATH to preserve the same review.
Known grader gaps must remain visible even when scope-specific checks pass.
"""

import argparse
from collections import Counter
from contextlib import closing
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.scoring import score_response
from src.tools.clickhouse_readonly import validate_read_only
from src.tools.policy_retrieval import retrieve_policy

TABLE = "agentic_analytics.delivery_work_items"
RATE = "100.0 * SUM(blocked) / COUNT(*) AS blocked_pct"
TAIL = " GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"
FORGED = f"SELECT 'Data' AS team,17.8 AS blocked_pct,'active_work_items' AS scope FROM {TABLE}"

# The scope expectation and task validity are intentionally separate. Unknown
# supportedness must not be reclassified as an invalid answer to hide a gap.
CASES = (
    ("canonical", True, "active_work_items",
     f"SELECT team,{RATE} FROM {TABLE} WHERE status != 'done'{TAIL}"),
    ("qualified-alias", True, "active_work_items",
     f'SELECT w.team,100.0*SUM(w.blocked)/COUNT(*) AS blocked_pct FROM "agentic_analytics"."delivery_work_items" AS w '
     "WHERE w.status <> 'done' GROUP BY w.team ORDER BY blocked_pct DESC LIMIT 1"),
    ("not-equality", True, "active_work_items",
     f"SELECT team,{RATE} FROM {TABLE} WHERE NOT (status = 'done'){TAIL}"),
    ("not-in", True, "active_work_items",
     f"SELECT team,{RATE} FROM {TABLE} WHERE status NOT IN ('done'){TAIL}"),
    ("forged-all-items", False, None, FORGED + " LIMIT 1"),
    ("uppercase-literal", False, None, FORGED + " WHERE status != 'DONE' LIMIT 1"),
    ("or-bypass", False, None, FORGED + " WHERE status != 'done' OR 1=1 LIMIT 1"),
    ("valid-cte-unknown", True, None,
     f"WITH active AS (SELECT * FROM {TABLE} WHERE status != 'done') "
     f"SELECT team,{RATE} FROM active{TAIL}"),
    ("active-literal-metric-gap", False, "active_work_items",
     f"SELECT 'Data' AS team,17.8 AS blocked_pct FROM {TABLE} WHERE status != 'done' LIMIT 1"),
)


class ScriptedControl:
    def __init__(self, sql):
        self.steps = iter((
            {"type": "tool_call", "name": "query_clickhouse", "arguments": {"sql": sql}},
            {"type": "tool_call", "name": "retrieve_policy",
             "arguments": {"query": "Blocker rate percentage KPI dictionary", "top_k": 1}},
            {"type": "final", "content": json.dumps({
                "disposition": "answer", "answer_text": (
                    "Data has the highest active-work blocker rate at 17.8%. "
                    "The KPI divides blocked active work by all active work in scope. "
                    "This does not establish causality."
                ),
            })},
        ))

    def respond(self, messages, tools):
        return next(self.steps)


def denied(*args, **kwargs):
    raise AssertionError("Independent review forbids live network/model/database calls")


def build_review():
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts/generate_delivery_data.py")],
                       cwd=directory, capture_output=True, check=True)
        csv_path = Path(directory) / "data/delivery_work_items.csv"
        csv_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        with csv_path.open(newline="") as stream:
            records = list(csv.DictReader(stream))
    totals, blocked = Counter(), Counter()
    for row in records:
        if row["status"] != "done":
            totals[row["team"]] += 1
            blocked[row["team"]] += int(row["blocked"])
    task = next(t for t in load_tasks(ROOT / "evals/system_benchmark/development_tasks.json") if t.case_id == "SB-D01")
    reference = next(r for r in load_references(ROOT / "evals/system_benchmark/development_references.json")
                     if r.reference_solution_id == task.reference_solution_id)
    cases = []
    with patch.object(socket.socket, "connect", denied), \
         patch.object(socket.socket, "connect_ex", denied), \
         patch("socket.create_connection", denied), \
         patch("src.agents.ollama_client.OllamaModelClient.__init__", denied), \
         patch("src.agents.ollama_client.OllamaModelClient.respond", denied), \
         patch("src.tools.clickhouse_readonly.query_clickhouse", denied), \
         closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("ATTACH DATABASE ':memory:' AS agentic_analytics")
        connection.execute(f"CREATE TABLE {TABLE} (team TEXT, status TEXT, blocked INTEGER)")
        connection.executemany(f"INSERT INTO {TABLE} VALUES (?,?,?)",
                               ((r["team"], r["status"], int(r["blocked"])) for r in records))
        for case_id, valid, expected_scope, sql in CASES:
            rows = []

            def local_query(statement):
                result = [dict(row) for row in connection.execute(validate_read_only(statement))]
                rows.extend(result)
                return result

            execution = BoundedLocalExecutor(model=ScriptedControl(sql), query_fn=local_query,
                                             policy_fn=retrieve_policy)(task, 1, None)
            score = score_response(task, reference, execution.response, execution.observation).to_dict()
            observed_scope = execution.observation.structured_values.get("scope")
            cases.append({
                "id": case_id, "contract_valid": valid, "expected_scope": expected_scope,
                "observed_scope": observed_scope, "scope_check_pass": observed_scope == expected_scope,
                "matches_contract_validity": score["passed"] == valid,
                "sql": sql, "rows": rows, "observation": asdict(execution.observation),
                "response": asdict(execution.response), "score": score,
                "scripted_steps": execution.model_calls,
            })

    frozen = ["evals/questions.json", "evals/system_benchmark/development_tasks.json",
              "evals/system_benchmark/development_references.json", "scripts/generate_delivery_data.py",
              "src/evals/system_benchmark/contracts.py", "src/evals/system_benchmark/freeze_audit.py",
              "src/evals/system_benchmark/loader.py", "src/evals/system_benchmark/references.py",
              "src/evals/system_benchmark/scoring.py", "src/evals/trajectory_quality.py"]
    frozen += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "evals/system_benchmark/corpus").iterdir()) if path.is_file()]
    source = ["src/evals/system_benchmark/scope_observation_v1.py", "src/evals/system_benchmark/local_worker.py",
              "tests/system_benchmark/test_scope_proposal_independent.py", "src/tools/clickhouse_readonly.py",
              "src/tools/policy_retrieval.py", "src/agents/ollama_client.py",
              "src/evals/system_benchmark/runner.py", "src/evals/system_benchmark/workers.py",
              "src/evals/system_benchmark/routing.py"]
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sorted(set(frozen + source))}
    changed = [path for path in frozen if hashlib.sha256(subprocess.run(
        ["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True,
    ).stdout).hexdigest() != hashes[path]]
    return {
        "schema_version": "independent-runtime-scope-v1-review",
        "phase3_accepted": False, "proposal_approved": False,
        "review_scope": "Inactive scope-observation correction; independent offline integration controls",
        "baseline_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                           text=True, check=True).stdout.strip(),
        "frozen_input_count": len(frozen), "frozen_unchanged": not changed, "changed_frozen_paths": changed,
        "sha256": hashes, "python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
        "dataset": {"seed": 42, "rows": len(records), "csv_sha256": csv_sha,
                    "active_team_counts": {team: {"blocked": blocked[team], "total": totals[team]}
                                           for team in sorted(totals)}},
        "cases": cases, "scope_checks_pass": all(row["scope_check_pass"] for row in cases),
        "grader_checks_pass": all(row["matches_contract_validity"] for row in cases),
        "unresolved_grader_controls": [row["id"] for row in cases if not row["matches_contract_validity"]],
        "live_model_calls": 0, "external_database_calls": 0,
        "network_and_live_clients_blocked": True,
        "limitations": [
            "SQLite common-subset execution does not verify ClickHouse dialect or global alias behavior.",
            "Tool decisions and final prose are authored controls, not model observations.",
            "Valid active CTE remains unknown and rejects under frozen scoring; supported SQL coverage is incomplete.",
            "A truthful active predicate does not establish metric computation or team ranking; literal 17.8 still passes.",
            "Passing scope checks is not evaluator validity, Phase 2 qualification or Phase 3 acceptance.",
        ],
    }


class TestScopeProposalIndependent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_review()
        cls.cases = {row["id"]: row for row in cls.report["cases"]}

    def test_canonical_and_equivalent_sql_pass_real_worker_and_frozen_scorer(self):
        for case_id in ("canonical", "qualified-alias", "not-equality", "not-in"):
            with self.subTest(case_id=case_id):
                case = self.cases[case_id]
                self.assertTrue(case["score"]["passed"], case["score"])
                self.assertEqual(case["observed_scope"], "active_work_items")
                self.assertAlmostEqual(case["rows"][0]["blocked_pct"], 100 * 8 / 45)
                self.assertNotIn("scope", case["rows"][0])

    def test_forged_labels_and_false_predicates_never_supply_scope(self):
        for case_id in ("forged-all-items", "uppercase-literal", "or-bypass"):
            with self.subTest(case_id=case_id):
                case = self.cases[case_id]
                self.assertEqual(case["rows"][0]["scope"], "active_work_items")
                self.assertIsNone(case["observed_scope"])
                self.assertFalse(case["score"]["passed"])
                self.assertEqual(case["score"]["reason_codes"], ["missing_expected_value"])

    def test_valid_cte_unknown_and_literal_metric_false_positive_stay_visible(self):
        cte = self.cases["valid-cte-unknown"]
        self.assertTrue(cte["contract_valid"])
        self.assertAlmostEqual(cte["rows"][0]["blocked_pct"], 100 * 8 / 45)
        self.assertEqual(cte["score"]["reason_codes"], ["missing_expected_value"])
        literal = self.cases["active-literal-metric-gap"]
        self.assertFalse(literal["contract_valid"])
        self.assertTrue(literal["score"]["passed"])
        self.assertEqual(set(self.report["unresolved_grader_controls"]),
                         {"valid-cte-unknown", "active-literal-metric-gap"})
        self.assertFalse(self.report["grader_checks_pass"])
        self.assertFalse(self.report["phase3_accepted"])

    def test_independent_truth_and_frozen_sources_are_preserved(self):
        self.assertTrue(self.report["frozen_unchanged"])
        self.assertEqual(self.report["frozen_input_count"], 18)
        self.assertEqual(self.report["dataset"]["rows"], 500)
        self.assertEqual(self.report["dataset"]["csv_sha256"],
                         "cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef")
        counts = self.report["dataset"]["active_team_counts"]
        self.assertEqual(counts["Data"], {"blocked": 8, "total": 45})
        self.assertEqual(max(counts, key=lambda team: counts[team]["blocked"] / counts[team]["total"]), "Data")
        self.assertTrue(self.report["scope_checks_pass"])
        self.assertTrue(self.report["network_and_live_clients_blocked"])


if __name__ == "__main__":
    if "--output" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(build_review(), indent=2, sort_keys=True, allow_nan=False) + "\n")
    else:
        unittest.main()
