import unittest

from src.evals.benchmark_preflight import run_preflight


class TestBenchmarkPreflight(unittest.TestCase):
    def test_missing_env_vars_stops_before_query(self):
        called = {"value": False}

        def fake_query(_sql):
            called["value"] = True
            return [{"row_count": 500}]

        code, message = run_preflight(env={}, query_fn=fake_query)

        self.assertEqual(code, 1)
        self.assertIn("Missing required environment variables", message)
        self.assertIn("CLICKHOUSE_URL", message)
        self.assertIn("set -a; source .env; set +a", message)
        self.assertFalse(called["value"])

    def test_authenticated_500_rows_reports_ready(self):
        env = {
            "CLICKHOUSE_URL": "https://example.invalid",
            "CLICKHOUSE_USER": "reader",
            "CLICKHOUSE_PASSWORD": "secret",
        }

        def fake_query(_sql):
            return [{"row_count": 500}]

        code, message = run_preflight(env=env, query_fn=fake_query)

        self.assertEqual(code, 0)
        self.assertIn("PASS: Benchmark preflight ready", message)
        self.assertIn("returned 500 rows", message)

    def test_wrong_row_count_fails(self):
        env = {
            "CLICKHOUSE_URL": "https://example.invalid",
            "CLICKHOUSE_USER": "reader",
            "CLICKHOUSE_PASSWORD": "secret",
        }

        code, message = run_preflight(
            env=env,
            query_fn=lambda _sql: [{"row_count": 499}],
        )

        self.assertEqual(code, 1)
        self.assertIn("Expected 500 synthetic rows", message)
        self.assertIn("Do not treat this attempt as benchmark performance evidence", message)

    def test_unauthorized_failure_is_clear(self):
        env = {
            "CLICKHOUSE_URL": "https://example.invalid",
            "CLICKHOUSE_USER": "reader",
            "CLICKHOUSE_PASSWORD": "secret",
        }

        def fake_query(_sql):
            raise RuntimeError("ClickHouse query failed: HTTP Error 401: Unauthorized")

        code, message = run_preflight(env=env, query_fn=fake_query)

        self.assertEqual(code, 1)
        self.assertIn("authentication failed", message.lower())

    def test_unreachable_failure_is_clear(self):
        env = {
            "CLICKHOUSE_URL": "https://example.invalid",
            "CLICKHOUSE_USER": "reader",
            "CLICKHOUSE_PASSWORD": "secret",
        }

        def fake_query(_sql):
            raise RuntimeError("ClickHouse query failed: [Errno 111] Connection refused")

        code, message = run_preflight(env=env, query_fn=fake_query)

        self.assertEqual(code, 1)
        self.assertIn("could not reach clickhouse", message.lower())


if __name__ == "__main__":
    unittest.main()
