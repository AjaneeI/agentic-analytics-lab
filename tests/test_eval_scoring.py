import unittest

from src.agents.single_agent import ToolCallRecord
from src.evals.scoring import score_case


class TestEvalScoring(unittest.TestCase):
    def test_numeric_answer_must_match_ground_truth(self):
        case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
        }
        calls = [
            ToolCallRecord(
                name="query_clickhouse",
                arguments={"sql": "SELECT ..."},
                row_count=1,
                result_rows=[{"team": "Data", "blocked_pct": 20.9}],
            )
        ]

        score = score_case(case, "Data is highest at 20.9%.", calls)

        self.assertTrue(score.correct)
        self.assertTrue(score.factual_consistency)
        self.assertTrue(score.tool_grounded)
        self.assertEqual(score.evidence_quality, "grounded_single_query")

    def test_numeric_scoring_accepts_more_precise_query_values(self):
        case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
        }
        calls = [
            ToolCallRecord(
                name="query_clickhouse",
                arguments={"sql": "SELECT ..."},
                row_count=1,
                result_rows=[{"team": "Data", "blocked_pct": 20.86}],
            )
        ]

        score = score_case(case, "Data is highest at approximately 20.86%.", calls)

        self.assertTrue(score.correct)
        self.assertTrue(score.factual_consistency)

    def test_evidence_scoring_accepts_rate_fraction_for_expected_percentage(self):
        case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
        }
        calls = [
            ToolCallRecord(
                name="query_clickhouse",
                arguments={"sql": "SELECT team, AVG(blocked) AS blocker_rate"},
                row_count=1,
                result_rows=[{"team": "Data", "blocker_rate": 0.208633}],
            )
        ]

        score = score_case(case, "Data is highest at approximately 20.86%.", calls)

        self.assertTrue(score.correct)
        self.assertTrue(score.factual_consistency)

    def test_execution_answer_is_not_correct_just_because_it_exists(self):
        case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
        }
        calls = [
            ToolCallRecord(
                name="query_clickhouse",
                arguments={"sql": "SELECT ..."},
                row_count=1,
                result_rows=[{"team": "AI", "blocked_pct": 15.0}],
            )
        ]

        score = score_case(case, "AI is highest at 15.0%.", calls)

        self.assertFalse(score.correct)
        self.assertFalse(score.factual_consistency)

    def test_ranking_order_is_checked(self):
        case = {
            "id": "Q4",
            "category": "ranking",
            "question": "Rank all four teams.",
            "expected": {
                "ranking": [
                    ["Data", 20.9],
                    ["AI", 15.0],
                    ["Product", 14.7],
                    ["Platform", 11.4],
                ]
            },
            "requires_tool": True,
        }
        rows = [
            {"team": "Data", "blocked_pct": 20.9},
            {"team": "AI", "blocked_pct": 15.0},
            {"team": "Product", "blocked_pct": 14.7},
            {"team": "Platform", "blocked_pct": 11.4},
        ]
        calls = [
            ToolCallRecord(
                name="query_clickhouse",
                arguments={"sql": "SELECT ..."},
                row_count=4,
                result_rows=rows,
            )
        ]

        good = score_case(
            case,
            "Data 20.9%, AI 15.0%, Product 14.7%, Platform 11.4%.",
            calls,
        )
        bad = score_case(
            case,
            "AI 15.0%, Data 20.9%, Product 14.7%, Platform 11.4%.",
            calls,
        )

        self.assertTrue(good.correct)
        self.assertFalse(bad.correct)

    def test_epistemic_case_uses_deterministic_behavior_check(self):
        case = {
            "id": "Q6",
            "category": "epistemic",
            "question": "Can this establish causality?",
            "expected_behavior": [
                "does_not_claim_causality",
                "distinguishes_association_from_causation",
                "requests additional evidence or stronger study design",
            ],
            "requires_tool": False,
        }
        answer = (
            "No. This observational dataset cannot establish causality. "
            "It can show an association or correlation, not causation. "
            "A randomized experiment or stronger study design controlling "
            "for confounders would be needed."
        )

        score = score_case(case, answer, [])

        self.assertTrue(score.correct)
        self.assertIsNone(score.factual_consistency)
        self.assertIsNone(score.tool_grounded)

    def test_epistemic_case_accepts_observational_rct_language(self):
        case = {
            "id": "Q6",
            "category": "epistemic",
            "question": "Can this establish causality?",
            "expected_behavior": [
                "does_not_claim_causality",
                "distinguishes_association_from_causation",
                "requests additional evidence or stronger study design",
            ],
            "requires_tool": False,
        }
        answer = (
            "The current dataset does not provide direct evidence of causality "
            "because it is observational. A longitudinal study or randomized "
            "controlled trial would be needed."
        )

        score = score_case(case, answer, [])

        self.assertTrue(score.correct)


if __name__ == "__main__":
    unittest.main()
