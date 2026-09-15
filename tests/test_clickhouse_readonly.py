import unittest

from src.tools.clickhouse_readonly import QueryRejected, validate_read_only


class TestReadOnlyValidation(unittest.TestCase):
    def test_select_allowed(self):
        sql = "SELECT count() FROM agentic_analytics.delivery_work_items"
        self.assertEqual(validate_read_only(sql), sql)

    def test_with_allowed(self):
        sql = "WITH 1 AS x SELECT x"
        self.assertEqual(validate_read_only(sql), sql)

    def test_truncate_rejected(self):
        with self.assertRaises(QueryRejected):
            validate_read_only(
                "TRUNCATE TABLE agentic_analytics.delivery_work_items"
            )

    def test_insert_rejected(self):
        with self.assertRaises(QueryRejected):
            validate_read_only(
                "INSERT INTO agentic_analytics.delivery_work_items VALUES (...)"
            )

    def test_mutation_hidden_after_select_rejected(self):
        with self.assertRaises(QueryRejected):
            validate_read_only(
                "SELECT 1; DROP TABLE agentic_analytics.delivery_work_items"
            )

    def test_mutation_keyword_in_comment_does_not_trigger(self):
        sql = "-- DROP TABLE anything\nSELECT 1"
        self.assertEqual(validate_read_only(sql), "SELECT 1")

    def test_multiple_read_statements_rejected(self):
        with self.assertRaises(QueryRejected):
            validate_read_only("SELECT 1; SELECT 2")

    def test_blocker_rate_complement_rejected(self):
        sql = (
            "SELECT (COUNT(*) - SUM(blocked)) / COUNT(*) AS blocker_rate "
            "FROM agentic_analytics.delivery_work_items"
        )

        with self.assertRaisesRegex(QueryRejected, "blocker_rate"):
            validate_read_only(sql)

    def test_blocker_rate_avg_complement_rejected(self):
        sql = (
            "SELECT 1 - AVG(blocked) AS blocker_rate "
            "FROM agentic_analytics.delivery_work_items"
        )

        with self.assertRaisesRegex(QueryRejected, "blocker_rate"):
            validate_read_only(sql)

    def test_blocker_rate_avg_allowed(self):
        sql = (
            "SELECT AVG(blocked) AS blocker_rate "
            "FROM agentic_analytics.delivery_work_items"
        )

        self.assertEqual(validate_read_only(sql), sql)

    def test_blocker_rate_sum_over_count_allowed(self):
        sql = (
            "SELECT SUM(blocked) / COUNT(*) AS blocker_rate "
            "FROM agentic_analytics.delivery_work_items"
        )

        self.assertEqual(validate_read_only(sql), sql)

    def test_blocker_rate_scaled_safe_expression_allowed(self):
        sql = (
            "SELECT ROUND(1.0 * SUM(blocked) / COUNT(*), 4) AS blocker_rate "
            "FROM agentic_analytics.delivery_work_items"
        )

        self.assertEqual(validate_read_only(sql), sql)


if __name__ == "__main__":
    unittest.main()
