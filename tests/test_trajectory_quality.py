import unittest

from src.evals.trajectory_quality import (
    TrajectoryExpectation,
    evaluate_trajectory,
)


class TestTrajectoryQuality(unittest.TestCase):
    def test_clean_trajectory_passes(self):
        calls = [
            {"name": "retrieve_policy", "arguments": {"query": "blockers"}},
            {"name": "query_clickhouse", "arguments": {"sql": "SELECT 1"}},
        ]
        expectation = TrajectoryExpectation(
            required_tools=("retrieve_policy", "query_clickhouse"),
            allowed_tools=("retrieve_policy", "query_clickhouse"),
            ordered_dependencies=(("retrieve_policy", "query_clickhouse"),),
            max_tool_calls=2,
        )

        result = evaluate_trajectory(calls, expectation)

        self.assertTrue(result.passed)
        self.assertTrue(result.tool_selection_correct)
        self.assertTrue(result.dependency_order_correct)
        self.assertTrue(result.efficiency_ok)

    def test_repeated_call_and_budget_overage_are_visible(self):
        call = {"name": "query_clickhouse", "arguments": {"sql": "SELECT 1"}}
        result = evaluate_trajectory(
            [call, call],
            TrajectoryExpectation(
                required_tools=("query_clickhouse",),
                allowed_tools=("query_clickhouse",),
                max_tool_calls=1,
            ),
        )

        self.assertFalse(result.passed)
        self.assertEqual(result.repeated_calls, 1)
        self.assertEqual(result.unnecessary_calls, 1)
        self.assertFalse(result.efficiency_ok)

    def test_dependency_violation_is_explicit(self):
        calls = [
            {"name": "query_clickhouse", "arguments": {"sql": "SELECT 1"}},
            {"name": "retrieve_policy", "arguments": {"query": "blockers"}},
        ]
        result = evaluate_trajectory(
            calls,
            TrajectoryExpectation(
                required_tools=("retrieve_policy", "query_clickhouse"),
                allowed_tools=("retrieve_policy", "query_clickhouse"),
                ordered_dependencies=(("retrieve_policy", "query_clickhouse"),),
            ),
        )

        self.assertFalse(result.dependency_order_correct)
        self.assertEqual(
            result.dependency_violations,
            ("retrieve_policy->query_clickhouse:wrong_order",),
        )

    def test_forbidden_and_unexpected_tools_are_distinct(self):
        calls = [
            {"name": "admin_sql", "arguments": {}},
            {"name": "web_search", "arguments": {}},
        ]
        result = evaluate_trajectory(
            calls,
            TrajectoryExpectation(
                allowed_tools=("query_clickhouse",),
                forbidden_tools=("admin_sql",),
            ),
        )

        self.assertEqual(result.forbidden_tools_used, ("admin_sql",))
        self.assertEqual(result.unexpected_tools, ("web_search",))


if __name__ == "__main__":
    unittest.main()
