import unittest

from src.tools.clickhouse_readonly import (
    QueryRejected,
    _validate_clickhouse_url,
    validate_read_only,
)


class TestReadOnlyValidation(unittest.TestCase):
    def test_select_allowed(self):
        sql = "SELECT count() FROM agentic_analytics.delivery_work_items"
        self.assertEqual(validate_read_only(sql), sql)

    def test_with_allowed(self):
        sql = "WITH 1 AS x SELECT x"
        self.assertEqual(validate_read_only(sql), sql)

    def test_cte_over_allowed_table_allowed(self):
        sql = (
            "WITH recent AS ("
            "SELECT * FROM agentic_analytics.delivery_work_items"
            ") SELECT count() FROM recent"
        )
        self.assertEqual(validate_read_only(sql), sql)

    def test_other_table_rejected(self):
        with self.assertRaisesRegex(QueryRejected, "Only agentic_analytics"):
            validate_read_only("SELECT * FROM other_db.secret_table")

    def test_join_to_other_table_rejected(self):
        with self.assertRaisesRegex(QueryRejected, "Only agentic_analytics"):
            validate_read_only(
                "SELECT * FROM agentic_analytics.delivery_work_items AS d "
                "JOIN other_db.secret_table AS t ON 1 = 1"
            )

    def test_table_function_rejected(self):
        with self.assertRaisesRegex(QueryRejected, "table functions"):
            validate_read_only("SELECT * FROM url('https://example.com/data.csv')")

    def test_describe_allowed_table_allowed(self):
        sql = "DESCRIBE TABLE agentic_analytics.delivery_work_items"
        self.assertEqual(validate_read_only(sql), sql)

    def test_describe_other_table_rejected(self):
        with self.assertRaisesRegex(QueryRejected, "Only agentic_analytics"):
            validate_read_only("DESCRIBE TABLE other_db.secret_table")

    def test_show_rejected(self):
        with self.assertRaises(QueryRejected):
            validate_read_only("SHOW TABLES")

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


class TestClickHouseUrlValidation(unittest.TestCase):
    def test_local_http_allowed(self):
        _validate_clickhouse_url("http://127.0.0.1:8123")
        _validate_clickhouse_url("http://localhost:8123")
        _validate_clickhouse_url("http://[::1]:8123")

    def test_remote_http_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "must use HTTPS"):
            _validate_clickhouse_url("http://clickhouse.example.com:8123")

    def test_https_allowed(self):
        _validate_clickhouse_url("https://clickhouse.example.com")


if __name__ == "__main__":
    unittest.main()
