"""Malformed callback evidence must decline before shared-handler coercion."""

from copy import deepcopy
from pathlib import Path
import unittest

from src.evals.system_benchmark.baselines import (
    DeterministicBaselineDeclined, DeterministicSimpleExecutor,
)
from src.evals.system_benchmark.loader import load_tasks
from src.routing.deterministic_handlers import GROUPED_TEAM_METRICS_SQL


ROOT = Path(__file__).resolve().parents[2]
VALID = {"team": "Synthetic Team", "total_items": 10, "blocked_items": 3,
         "blocker_rate": 30.0, "avg_effort_ratio": 1.2}


class TestRawEvidenceBoundary(unittest.TestCase):
    def setUp(self):
        self.task = next(t for t in load_tasks(
            ROOT / "evals/system_benchmark/development_tasks.json"
        ) if t.case_id == "SB-A01")

    def execute(self, rows):
        self.calls = []

        def query(sql):
            self.calls.append(sql)
            return rows

        return DeterministicSimpleExecutor(query_fn=query)(self.task, 1, None)

    def assert_declines_once(self, rows):
        with self.assertRaises(DeterministicBaselineDeclined):
            self.execute(rows)
        self.assertEqual(self.calls, [GROUPED_TEAM_METRICS_SQL])

    def test_malformed_containers_and_missing_fields_decline(self):
        for rows in (None, True, 3, "rows", {"rows": [VALID]}, (VALID,),
                     [None], [True], [3], ["team"], [[]], [{}]):
            with self.subTest(rows=rows):
                self.assert_declines_once(rows)
        for field in VALID:
            with self.subTest(missing=field):
                self.assert_declines_once([{k: v for k, v in VALID.items() if k != field}])

    def test_invalid_team_types_cannot_become_fabricated_names(self):
        for value in (None, True, 5, 2.5, [], {}, "", " \t"):
            with self.subTest(value=value):
                self.assert_declines_once([dict(VALID, team=value)])

    def test_counts_cannot_be_boolean_fractional_or_invalid(self):
        for field in ("total_items", "blocked_items"):
            for value in (True, False, 10.9, -0.1, None, [], {}, "10.9",
                          "ten", "", float("nan"), float("inf"), 10 ** 400):
                with self.subTest(field=field, value=value):
                    self.assert_declines_once([dict(VALID, **{field: value})])

    def test_metrics_cannot_be_boolean_nonnumeric_or_nonfinite(self):
        for field in ("blocker_rate", "avg_effort_ratio"):
            for value in (True, False, None, [], {}, "many", "", "NaN", "Inf",
                          float("nan"), float("inf"), -float("inf"), 10 ** 400):
                with self.subTest(field=field, value=value):
                    self.assert_declines_once([dict(VALID, **{field: value})])

    def test_malformed_nonwinning_row_cannot_be_ignored(self):
        self.assert_declines_once([VALID, dict(VALID, team=None, blocker_rate=5.0)])

    def test_existing_numeric_representations_keep_output_and_input_unchanged(self):
        for overrides in ({}, {"total_items": "10", "blocked_items": "3"},
                          {"total_items": 10.0, "blocked_items": 3.0},
                          {"blocker_rate": "30.0", "avg_effort_ratio": "1.2"}):
            with self.subTest(overrides=overrides):
                rows = [dict(VALID, **overrides)]
                before = deepcopy(rows)
                result = self.execute(rows)
                self.assertEqual(rows, before)
                self.assertEqual(self.calls, [GROUPED_TEAM_METRICS_SQL])
                self.assertEqual(result.response.answer_text,
                                 "Synthetic Team has the highest blocker rate at 30.0%.")
                self.assertEqual(dict(result.observation.structured_values),
                                 {"team": "Synthetic Team", "blocked_pct": 30.0})
                self.assertEqual(result.observation.tool_call_records, ({
                    "name": "query_clickhouse", "arguments": {"sql": GROUPED_TEAM_METRICS_SQL},
                },))
                self.assertEqual(result.model_calls, 0)

    def test_callback_failure_is_preserved_without_retry(self):
        calls = []
        failure = RuntimeError("synthetic callback failure")

        def query(sql):
            calls.append(sql)
            raise failure

        with self.assertRaises(RuntimeError) as caught:
            DeterministicSimpleExecutor(query_fn=query)(self.task, 1, None)
        self.assertIs(caught.exception, failure)
        self.assertEqual(calls, [GROUPED_TEAM_METRICS_SQL])


if __name__ == "__main__":
    unittest.main()
