import unittest

from src.routing.deterministic_handlers import (
    GROUPED_TEAM_METRICS_SQL,
    DeterministicHandlerDeclined,
    HandlerKey,
    execute_deterministic_handler,
)
from src.tools.clickhouse_readonly import validate_read_only


# Mirrors the accepted seed-42 grouped metrics closely enough to exercise
# deterministic formatting and selection semantics.
BASE_ROWS = [
    {
        "team": "AI",
        "total_items": 120,
        "blocked_items": 18,
        "blocker_rate": 15.0,
        "avg_effort_ratio": 1.1666802146,
    },
    {
        "team": "Data",
        "total_items": 139,
        "blocked_items": 29,
        "blocker_rate": 20.9,
        "avg_effort_ratio": 1.1387180739,
    },
    {
        "team": "Platform",
        "total_items": 105,
        "blocked_items": 12,
        "blocker_rate": 11.4,
        "avg_effort_ratio": 1.0982895688,
    },
    {
        "team": "Product",
        "total_items": 136,
        "blocked_items": 20,
        "blocker_rate": 14.7,
        "avg_effort_ratio": 1.1113253012,
    },
]


class TestDeterministicAnalyticsHandlers(unittest.TestCase):
    def query(self, rows=None):
        captured = []
        result_rows = list(rows or BASE_ROWS)

        def query_fn(sql):
            captured.append(sql)
            return result_rows

        return query_fn, captured

    def test_fixed_grouped_query_passes_existing_read_only_guard(self):
        self.assertEqual(
            validate_read_only(GROUPED_TEAM_METRICS_SQL),
            GROUPED_TEAM_METRICS_SQL,
        )

    def test_handlers_use_fixed_read_only_grouped_query(self):
        query_fn, captured = self.query()

        result = execute_deterministic_handler(
            HandlerKey.BLOCKER_RATE_LEADER,
            query_fn=query_fn,
        )

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0], GROUPED_TEAM_METRICS_SQL)
        self.assertIn("FROM agentic_analytics.delivery_work_items", captured[0])
        self.assertIn("sum(actual_hours) / sum(planned_hours)", captured[0])
        self.assertNotIn("INSERT", captured[0].upper())
        self.assertEqual(result.query_count, 1)

    def test_blocker_rate_leader_matches_q1_semantics(self):
        query_fn, _ = self.query()
        result = execute_deterministic_handler(
            HandlerKey.BLOCKER_RATE_LEADER,
            query_fn=query_fn,
        )

        self.assertIn("Data", result.answer)
        self.assertIn("20.9", result.answer)

    def test_effort_ratio_leader_matches_q2_query_semantics(self):
        query_fn, _ = self.query()
        result = execute_deterministic_handler(
            HandlerKey.EFFORT_RATIO_LEADER,
            query_fn=query_fn,
        )

        self.assertIn("AI", result.answer)
        self.assertIn("1.17", result.answer)

    def test_blocker_count_rate_consistency_matches_q3_semantics(self):
        query_fn, _ = self.query()
        result = execute_deterministic_handler(
            HandlerKey.BLOCKER_COUNT_RATE_CONSISTENCY,
            query_fn=query_fn,
        )

        self.assertTrue(result.answer.startswith("Yes."))
        self.assertIn("Data", result.answer)
        self.assertIn("29", result.answer)
        self.assertIn("20.9", result.answer)

    def test_blocker_count_rate_consistency_can_answer_no(self):
        rows = [dict(row) for row in BASE_ROWS]
        rows[0]["blocked_items"] = 30
        query_fn, _ = self.query(rows)

        result = execute_deterministic_handler(
            HandlerKey.BLOCKER_COUNT_RATE_CONSISTENCY,
            query_fn=query_fn,
        )

        self.assertTrue(result.answer.startswith("No."))
        self.assertIn("AI", result.answer)
        self.assertIn("Data", result.answer)

    def test_blocker_rate_ranking_matches_q4_order(self):
        query_fn, _ = self.query()
        result = execute_deterministic_handler(
            HandlerKey.BLOCKER_RATE_RANKING,
            query_fn=query_fn,
        )

        positions = [
            result.answer.index(team)
            for team in ["Data", "AI", "Product", "Platform"]
        ]
        self.assertEqual(positions, sorted(positions))
        for value in ("20.9", "15.0", "14.7", "11.4"):
            self.assertIn(value, result.answer)

    def test_dual_metric_leader_matches_q5_when_one_team_dominates(self):
        query_fn, _ = self.query()
        result = execute_deterministic_handler(
            HandlerKey.DUAL_METRIC_LEADER,
            query_fn=query_fn,
        )

        self.assertIn("Platform", result.answer)
        self.assertIn("11.4", result.answer)
        self.assertIn("1.10", result.answer)

    def test_effort_control_means_closest_ratio_to_one(self):
        rows = [dict(row) for row in BASE_ROWS]
        rows[2]["avg_effort_ratio"] = 0.80
        rows[3]["avg_effort_ratio"] = 1.05
        query_fn, _ = self.query(rows)

        with self.assertRaisesRegex(
            DeterministicHandlerDeclined,
            "No single team",
        ):
            execute_deterministic_handler(
                HandlerKey.DUAL_METRIC_LEADER,
                query_fn=query_fn,
            )

    def test_dual_metric_handler_declines_when_metrics_disagree(self):
        rows = [dict(row) for row in BASE_ROWS]
        rows[3]["avg_effort_ratio"] = 1.02
        query_fn, _ = self.query(rows)

        with self.assertRaisesRegex(
            DeterministicHandlerDeclined,
            "No single team",
        ):
            execute_deterministic_handler(
                HandlerKey.DUAL_METRIC_LEADER,
                query_fn=query_fn,
            )

    def test_tied_extreme_declines_instead_of_inventing_tiebreak(self):
        rows = [dict(row) for row in BASE_ROWS]
        rows[0]["blocker_rate"] = 20.9
        query_fn, _ = self.query(rows)

        with self.assertRaisesRegex(DeterministicHandlerDeclined, "No unique"):
            execute_deterministic_handler(
                HandlerKey.BLOCKER_RATE_LEADER,
                query_fn=query_fn,
            )

    def test_missing_metric_field_declines(self):
        rows = [dict(BASE_ROWS[0])]
        rows[0].pop("blocker_rate")
        query_fn, _ = self.query(rows)

        with self.assertRaisesRegex(DeterministicHandlerDeclined, "missing"):
            execute_deterministic_handler(
                HandlerKey.BLOCKER_RATE_LEADER,
                query_fn=query_fn,
            )

    def test_duplicate_team_declines(self):
        rows = [dict(BASE_ROWS[0]), dict(BASE_ROWS[0])]
        query_fn, _ = self.query(rows)

        with self.assertRaisesRegex(DeterministicHandlerDeclined, "unique"):
            execute_deterministic_handler(
                HandlerKey.BLOCKER_RATE_LEADER,
                query_fn=query_fn,
            )

    def test_unknown_handler_fails_closed(self):
        query_fn, captured = self.query()

        with self.assertRaisesRegex(ValueError, "Unsupported deterministic handler"):
            execute_deterministic_handler("admin_bypass", query_fn=query_fn)

        self.assertEqual(captured, [])


if __name__ == "__main__":
    unittest.main()
