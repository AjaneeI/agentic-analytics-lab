"""Exercise candidate transport with fake HTTP only; never submit captured SQL."""
import io
import unittest
import urllib.error
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
from src.tools.clickhouse_readonly import QueryRejected, query_clickhouse

FIXTURE_SQL = 'SELECT planned_hours + 1 AS probe FROM agentic_analytics.delivery_work_items LIMIT 1'

class TestCandidateTransport(unittest.TestCase):
    def test_success_delivers_expression_jit_off_and_preserves_every_budget_and_sql(self):
        requests = []
        def fake_http(request, *, timeout):
            requests.append((request, timeout))
            return io.BytesIO(b'{"probe":3}\n')
        with patch('urllib.request.urlopen', fake_http):
            result = query_clickhouse(FIXTURE_SQL)
        self.assertEqual(result, [{'probe': 3}])
        self.assertEqual(len(requests), 1)
        request, timeout = requests[0]
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.data, FIXTURE_SQL.encode())
        self.assertEqual(timeout, 15)
        self.assertEqual(parse_qs(urlsplit(request.full_url).query), {
            'default_format': ['JSONEachRow'], 'readonly': ['1'],
            'max_execution_time': ['10'], 'max_result_rows': ['1000'],
            'result_overflow_mode': ['break'], 'max_rows_to_read': ['10000'],
            'max_bytes_to_read': ['10485760'], 'max_memory_usage': ['134217728'],
            'max_threads': ['2'], 'compile_expressions': ['0'],
        })

    def test_client_timeout_still_fails_once_without_retry(self):
        calls = []
        def fake_http(request, *, timeout):
            calls.append((request.data, timeout))
            raise TimeoutError('fixture timeout')
        with patch('urllib.request.urlopen', fake_http):
            with self.assertRaisesRegex(RuntimeError, 'ClickHouse query failed: fixture timeout') as caught:
                query_clickhouse(FIXTURE_SQL)
        self.assertIsInstance(caught.exception.__cause__, TimeoutError)
        self.assertEqual(calls, [(FIXTURE_SQL.encode(), 15)])

    def test_late_server_timeout_is_preserved_without_sql_or_credentials(self):
        calls = []
        def fake_http(request, *, timeout):
            calls.append(request.data)
            raise urllib.error.HTTPError('http://fixture.invalid/', 408, 'Timeout', {},
                io.BytesIO(b'Code: 159. DB::Exception: private-sql credential-secret (TIMEOUT_EXCEEDED)'))
        with patch('urllib.request.urlopen', fake_http):
            with self.assertRaises(RuntimeError) as caught:
                query_clickhouse(FIXTURE_SQL)
        exc = caught.exception
        self.assertEqual((exc.http_status, exc.server_code, exc.server_error_name),
                         (408, 159, 'TIMEOUT_EXCEEDED'))
        self.assertNotIn('private-sql', str(exc))
        self.assertNotIn('credential-secret', str(exc))
        self.assertEqual(calls, [FIXTURE_SQL.encode()])

    def test_body_read_timeout_remains_terminal_and_closes_response(self):
        calls = []
        class TimeoutBody(io.BytesIO):
            def read(self, *args):
                raise TimeoutError('fixture body timeout')
        response = TimeoutBody()
        def fake_http(request, *, timeout):
            calls.append(request.data)
            return response
        with patch('urllib.request.urlopen', fake_http):
            with self.assertRaisesRegex(RuntimeError, 'fixture body timeout'):
                query_clickhouse(FIXTURE_SQL)
        self.assertTrue(response.closed)
        self.assertEqual(calls, [FIXTURE_SQL.encode()])

    def test_forbidden_table_is_rejected_before_http(self):
        def forbidden_http(*args, **kwargs):
            raise AssertionError('query validation failed to guard transport')
        with patch('urllib.request.urlopen', forbidden_http):
            with self.assertRaises(QueryRejected):
                query_clickhouse('SELECT * FROM other_db.secret_table')

    def test_mutation_and_multiple_statements_remain_rejected(self):
        def forbidden_http(*args, **kwargs):
            raise AssertionError('query validation failed to guard transport')
        with patch('urllib.request.urlopen', forbidden_http):
            for sql in ['DROP TABLE agentic_analytics.delivery_work_items', 'SELECT 1; SELECT 2']:
                with self.subTest(sql=sql), self.assertRaises(QueryRejected):
                    query_clickhouse(sql)

if __name__ == '__main__':
    unittest.main()
