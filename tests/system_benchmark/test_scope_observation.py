"""Offline regression tests for the proposed executed-SQL scope observation."""
from pathlib import Path
import unittest
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
ROOT = Path(__file__).resolve().parents[2]
TABLE = 'agentic_analytics.delivery_work_items'
BASE = 'SELECT team, 100.0 * SUM(blocked) / COUNT(*) AS blocked_pct FROM ' + TABLE
TAIL = ' GROUP BY team ORDER BY blocked_pct DESC LIMIT 1'

class TestScopeObservation(unittest.TestCase):
    def setUp(self):
        self.task = next(t for t in load_tasks(ROOT / 'evals/system_benchmark/development_tasks.json') if t.case_id == 'SB-D01')
    def observe(self, sql, rows=None, initial=None):
        values = dict(initial or {})
        calls = []
        def query(statement):
            calls.append(statement)
            return rows if rows is not None else [{'team': 'Data', 'blocked_pct': 17.7777777778}]
        worker = BoundedLocalExecutor(model=object(), query_fn=query)
        worker._run_query_tool(self.task, {'sql': sql}, values, [])
        self.assertEqual(calls, [sql])
        return values
    def test_executed_active_predicate_supplies_scope_without_row_label(self):
        self.assertEqual(self.observe(BASE + " WHERE status != 'done'" + TAIL).get('scope'), 'active_work_items')
    def test_unverified_returned_label_is_never_scope_proof(self):
        rows = [{'team': 'Data', 'blocked_pct': 17.8, 'scope': 'active_work_items'}]
        self.assertNotIn('scope', self.observe(BASE + TAIL, rows))
    def test_supported_equivalent_predicates_preserve_literal_case(self):
        for predicate in ["status <> 'done'", "NOT (status = 'done')", "status NOT IN ('done')", "((status != 'done'))"]:
            with self.subTest(predicate=predicate):
                self.assertEqual(self.observe(BASE + ' WHERE ' + predicate + TAIL).get('scope'), 'active_work_items')
    def test_alias_and_quoted_identifiers(self):
        sql = 'SELECT w.team, 100.0 * SUM(w.blocked)/COUNT(*) AS blocked_pct FROM `agentic_analytics`.`delivery_work_items` AS w WHERE w.`status` != \'done\' GROUP BY w.team ORDER BY blocked_pct DESC LIMIT 1'
        self.assertEqual(self.observe(sql).get('scope'), 'active_work_items')
    def test_unsupported_or_false_proofs_remain_unknown_and_clear_stale(self):
        predicates = ["status != 'DONE'", "status != 'done' OR 1=1", "status != 'done' AND priority = 'high'", "status IN ('active')", "other.status != 'done'", "status NOT IN ('done', 'cancelled')"]
        statements = [BASE + ' WHERE ' + p + TAIL for p in predicates]
        statements += [BASE + " /* WHERE status != 'done' */" + TAIL,
            BASE + " WHERE status != 'done' UNION ALL " + BASE,
            'WITH active AS (' + BASE + " WHERE status != 'done') SELECT * FROM active",
            "SELECT 'active' AS status, team, 17.8 AS blocked_pct FROM " + TABLE + " WHERE status != 'done' LIMIT 1",
            BASE + " WHERE status != 'done' HAVING count(*) > 0" + TAIL,
            BASE + " WHERE status != 'done'" + TAIL + " BY priority",
            BASE + " WHERE status != 'done'" + TAIL + ";",
            BASE + " WHERE status != 'done'" + TAIL + " SETTINGS max_threads=1"]
        for sql in statements:
            with self.subTest(sql=sql):
                self.assertNotIn('scope', self.observe(sql, initial={'scope': 'active_work_items'}))
    def test_single_quoted_status_alias_remains_unknown(self):
        sql = "SELECT 'active' AS 'status', team,17.8 AS blocked_pct FROM " + TABLE + " WHERE status != 'done' LIMIT 1"
        self.assertNotIn('scope', self.observe(sql))
    def test_empty_success_is_not_scope_evidence(self):
        self.assertNotIn('scope', self.observe(BASE + " WHERE status != 'done'" + TAIL, rows=[]))
    def test_query_failure_does_not_manufacture_observations(self):
        values = {}
        def fail(sql):
            raise RuntimeError('controlled failure')
        worker = BoundedLocalExecutor(model=object(), query_fn=fail)
        with self.assertRaises(RuntimeError):
            worker._run_query_tool(self.task, {'sql': BASE + " WHERE status != 'done'" + TAIL}, values, [])
        self.assertEqual(values, {})
