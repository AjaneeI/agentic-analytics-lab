import unittest

from src.agents.single_agent import AgentResult, ToolCallRecord
from src.evals.throughput import (
    run_load_level,
    run_throughput_sweep,
    summarize_throughput_sweep,
)


CASE = {
    "id": "Q1",
    "category": "retrieval",
    "question": "Which team has the highest blocker rate?",
    "expected": {"team": "Data", "blocked_pct": 20.9},
    "requires_tool": True,
    "max_tool_calls": 1,
}


class CorrectAgent:
    def run(self, question):
        return AgentResult(
            answer="Data has the highest blocker rate at 20.9%.",
            tool_calls=[
                ToolCallRecord(
                    name="query_clickhouse",
                    arguments={"sql": "SELECT team, 20.9 AS blocked_pct"},
                    row_count=1,
                    result_rows=[{"team": "Data", "blocked_pct": 20.9}],
                )
            ],
            model_call_count=2,
            tool_call_attempt_count=1,
            input_tokens=10,
            output_tokens=5,
        )


class TestThroughputEvaluation(unittest.TestCase):
    def test_load_level_uses_isolated_agent_instances(self):
        created = []

        def factory():
            agent = CorrectAgent()
            created.append(agent)
            return agent

        cases = [dict(CASE, id=f"LOAD{index}") for index in range(1, 5)]
        result = run_load_level(factory, cases, concurrency=2)

        self.assertEqual(len(created), 4)
        self.assertEqual(result["summary"]["requests"], 4)
        self.assertEqual(result["summary"]["task_successful"], 4)
        self.assertGreater(result["summary"]["validated_tasks_per_minute"], 0)
        self.assertGreaterEqual(result["summary"]["p95_queue_wait_seconds"], 0)

    def test_summary_selects_best_goodput(self):
        levels = [
            {
                "concurrency": 1,
                "summary": {"validated_tasks_per_minute": 2.0},
            },
            {
                "concurrency": 2,
                "summary": {"validated_tasks_per_minute": 3.5},
            },
        ]

        summary = summarize_throughput_sweep(levels)

        self.assertEqual(summary["best_observed_concurrency"], 2)
        self.assertEqual(summary["best_validated_tasks_per_minute"], 3.5)
        self.assertIsNone(summary["saturation_concurrency"])

    def test_sweep_stops_when_validated_goodput_falls(self):
        synthetic = {
            1: {
                "concurrency": 1,
                "summary": {
                    "validated_tasks_per_minute": 2.0,
                    "task_success_rate": 1.0,
                    "execution_errors": 0,
                },
            },
            2: {
                "concurrency": 2,
                "summary": {
                    "validated_tasks_per_minute": 4.0,
                    "task_success_rate": 1.0,
                    "execution_errors": 0,
                },
            },
            4: {
                "concurrency": 4,
                "summary": {
                    "validated_tasks_per_minute": 3.8,
                    "task_success_rate": 1.0,
                    "execution_errors": 0,
                },
            },
            6: {
                "concurrency": 6,
                "summary": {
                    "validated_tasks_per_minute": 4.5,
                    "task_success_rate": 1.0,
                    "execution_errors": 0,
                },
            },
        }

        def fake_level_runner(agent_factory, cases, concurrency):
            return synthetic[concurrency]

        result = run_throughput_sweep(
            agent_factory=lambda: CorrectAgent(),
            cases=[CASE],
            concurrency_levels=(1, 2, 4, 6),
            level_runner=fake_level_runner,
        )

        self.assertEqual(
            result["sweep_summary"]["levels_completed"],
            [1, 2, 4],
        )
        self.assertEqual(
            result["sweep_summary"]["best_observed_concurrency"],
            2,
        )
        self.assertEqual(
            result["sweep_summary"]["saturation_concurrency"],
            4,
        )
        self.assertIn(
            "validated_goodput_did_not_improve",
            result["sweep_summary"]["saturation_reasons"],
        )

    def test_concurrency_levels_must_be_increasing_and_unique(self):
        with self.assertRaisesRegex(ValueError, "unique and increasing"):
            run_throughput_sweep(
                agent_factory=lambda: CorrectAgent(),
                cases=[CASE],
                concurrency_levels=(1, 4, 2),
                level_runner=lambda *_: {},
            )


if __name__ == "__main__":
    unittest.main()
