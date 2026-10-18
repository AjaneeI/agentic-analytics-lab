"""Offline candidate contract checks; never invoke a model or live database."""
import io
import unittest
import urllib.error
from unittest.mock import patch

from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.tools.clickhouse_readonly import QueryRejected, query_clickhouse
from tests.system_benchmark.test_local_worker import ScriptedModel, sb_d01, final_payload


class TestSchemaContextCandidate(unittest.TestCase):
    def test_worker_supplies_schema_without_answer_metadata_or_extra_calls(self):
        model = ScriptedModel([{'type': 'final', 'content': final_payload()}])
        with patch.object(model, 'respond', wraps=model.respond) as respond:
            BoundedLocalExecutor(model=model)(sb_d01(), 1, None)
        tools = respond.call_args.args[1]
        query = next(t for t in tools if t['name'] == 'query_clickhouse')
        description = query['description']
        for name in ('work_item_id', 'team', 'priority', 'status', 'created_at',
                     'due_at', 'completed_at', 'planned_hours', 'actual_hours',
                     'blocked', 'blocker_type', 'rework_count', 'customer_impact'):
            self.assertIn(name, description)
        self.assertIn('provenance', description)
        self.assertIn('not a column', description)
        self.assertEqual(tuple(t['name'] for t in tools), ('query_clickhouse', 'retrieve_policy'))
        self.assertEqual(respond.call_count, 1)
        for forbidden in ('17.8', '20.9', 'REF-D01', 'development_references', '"value": "Data"'):
            self.assertNotIn(forbidden, description)

    def test_404_exposes_server_code_without_sql_credentials_or_retry(self):
        body = (b'Code: 47. DB::Exception: Unknown identifier snapshot in scope '
                b'SELECT private_literal. password=do-not-expose. '
                b'(UNKNOWN_IDENTIFIER) (version 26.8.4.11 (official build))')
        error = urllib.error.HTTPError('http://user:do-not-expose@localhost/', 404,
                                      'Not Found', {}, io.BytesIO(body))
        with patch('urllib.request.urlopen', side_effect=error) as transport:
            with self.assertRaises(RuntimeError) as caught:
                query_clickhouse('SELECT count() FROM agentic_analytics.delivery_work_items')
        exc = caught.exception
        self.assertEqual(getattr(exc, 'http_status', None), 404)
        self.assertEqual(getattr(exc, 'server_code', None), 47)
        self.assertEqual(getattr(exc, 'server_error_name', None), 'UNKNOWN_IDENTIFIER')
        self.assertNotIn('do-not-expose', str(exc))
        self.assertNotIn('private_literal', str(exc))
        self.assertEqual(transport.call_count, 1)

    def test_success_preserves_readonly_request_and_does_not_rewrite_sql(self):
        sql = 'SELECT team FROM agentic_analytics.delivery_work_items LIMIT 1'
        response = io.BytesIO(b'{"team":"FixtureTeam"}\n')
        with patch('urllib.request.urlopen', return_value=response) as transport:
            self.assertEqual(query_clickhouse(sql), [{'team': 'FixtureTeam'}])
        request = transport.call_args.args[0]
        self.assertEqual(request.data, sql.encode())
        self.assertIn('readonly=1', request.full_url)
        self.assertIn('max_result_rows=1000', request.full_url)
        self.assertEqual(transport.call_count, 1)

    def test_error_body_read_failure_preserves_original_http_failure(self):
        class BrokenBody(io.BytesIO):
            def read(self, *args):
                raise OSError('body unavailable')
        error = urllib.error.HTTPError('http://localhost/', 404, 'Not Found', {}, BrokenBody())
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                query_clickhouse('SELECT 1')
        self.assertEqual(getattr(caught.exception, 'http_status', None), 404)
        self.assertIsNone(getattr(caught.exception, 'server_code', None))

    def test_error_diagnostic_read_is_bounded(self):
        reads = []
        class RecordingBody(io.BytesIO):
            def read(self, size=-1):
                reads.append(size)
                return super().read(size)
        error = urllib.error.HTTPError('http://localhost/', 404, 'Not Found', {},
            RecordingBody(b'Code: 47. ' + b'x' * 20000))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                query_clickhouse('SELECT 1')
        self.assertEqual(reads, [8192])
        self.assertEqual(getattr(caught.exception, 'server_code', None), 47)
        self.assertLess(len(str(caught.exception)), 100)

    def test_forbidden_query_remains_rejected_before_transport(self):
        with patch('urllib.request.urlopen') as transport:
            with self.assertRaises(QueryRejected):
                query_clickhouse('SELECT * FROM other_db.secret_table')
        transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()
