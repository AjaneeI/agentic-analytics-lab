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


if __name__ == "__main__":
    unittest.main()
