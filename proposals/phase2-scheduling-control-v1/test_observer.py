"""Offline contract tests: no network, Docker, SQL execution or model calls."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('scheduling_observer', HERE / 'observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class ObserverTests(unittest.TestCase):
    def test_consumed_directory_cannot_be_reused_even_after_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'capture'
            observer.reserve(out, {'resource_window': 'verified-reference'})
            with self.assertRaises(FileExistsError):
                observer.reserve(out, {'resource_window': 'another-reference'})
            self.assertEqual(json.loads((out / 'CONSUMED.json').read_text())['remaining_launches'], 0)

    def test_missing_window_refuses_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'capture'
            with self.assertRaises(ValueError):
                observer.reserve(out, {})
            self.assertFalse(out.exists())

    def test_partial_status_is_retained_when_transport_times_out(self):
        class Partial:
            data = iter([b'H', b'T', b'T', b'P'])
            def read(self, size):
                try:
                    return next(self.data)
                except StopIteration:
                    raise TimeoutError('scripted timeout')
        captured = bytearray()
        with self.assertRaises(TimeoutError):
            observer.read_line(Partial(), captured)
        self.assertEqual(captured, b'HTTP')

    def test_cumulative_header_limit_stops_before_an_extra_read(self):
        captured = bytearray(b'x' * 4095)
        source = io.BytesIO(b'yz')
        with self.assertRaises(RuntimeError):
            observer.read_line(source, captured)
        self.assertEqual(len(captured), 4096)
        self.assertEqual(source.read(), b'z')

    def test_output_limit_never_writes_a_partial_or_oversized_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            observer.save(out, 'a.bin', b'a' * 28671)
            with self.assertRaises(RuntimeError):
                observer.save(out, 'b.bin', b'xx')
            self.assertFalse((out / 'b.bin').exists())
            observer.save(out, 'receipt.json', b'{}')
            self.assertTrue((out / 'receipt.json').exists())

    def test_metadata_sql_targets_only_new_probe_and_bounded_window(self):
        sql = observer.metadata_sql('aal-scheduling-control-v1-abc', 1000000, 2000000)
        self.assertIn("query_id = 'aal-scheduling-control-v1-abc'", sql)
        self.assertIn('query_start_time_microseconds >= fromUnixTimestamp64Micro(1000000)', sql)
        self.assertIn('query_start_time_microseconds <= fromUnixTimestamp64Micro(2000000)', sql)
        self.assertIn('LIMIT 1', sql)
        self.assertNotIn('query,', sql)
        self.assertNotIn('delivery_work_items', sql)

    def test_metadata_sql_rejects_injected_id_and_overwide_window(self):
        for query_id, start, end in [("x' OR 1=1", 1, 2), ('x', 1, 40000002), ('x', 2, 1)]:
            with self.subTest(query_id=query_id, end=end), self.assertRaises(ValueError):
                observer.metadata_sql(query_id, start, end)

    def test_missing_profile_counter_stays_unknown(self):
        result = observer.interpret([{'query_id': 'probe', 'ProfileEvents': {'RealTimeMicroseconds': 200},
            'Settings': {'compile_expressions': '0'}, 'query_duration_ms': 1}], 'probe')
        self.assertIsNone(result['profile_events']['OSCPUWaitMicroseconds'])
        self.assertIn('OSCPUWaitMicroseconds', result['missing_profile_events'])
        self.assertFalse(result['phase2_qualified'])
        self.assertNotIn('cpu_wait_wall_time_percent', result)

    def test_metadata_missing_is_inconclusive_and_duplicate_or_wrong_rows_rejected(self):
        self.assertEqual(observer.interpret([], 'probe')['status'], 'metadata_unavailable')
        for rows in [[{'query_id': 'other'}], [{'query_id': 'probe'}, {'query_id': 'probe'}]]:
            with self.assertRaises(ValueError):
                observer.interpret(rows, 'probe')

    def test_synthetic_result_mismatch_stops_before_metadata(self):
        calls = []
        def exchange(sql, query_id):
            calls.append(sql)
            return [{'scheduling_probe': 7}]
        with self.assertRaises(ValueError):
            observer.sequence(exchange, 'aal-scheduling-control-v1-abc', lambda: 1000000)
        self.assertEqual(len(calls), 1)

    def test_transport_failure_is_propagated_without_retry(self):
        calls = []
        def exchange(sql, query_id):
            calls.append(sql)
            raise TimeoutError('scripted timeout')
        with self.assertRaises(TimeoutError):
            observer.sequence(exchange, 'aal-scheduling-control-v1-abc', lambda: 1000000)
        self.assertEqual(len(calls), 1)

    def test_exact_two_request_sequence_retains_effective_settings(self):
        calls = []
        def exchange(sql, query_id):
            calls.append((sql, query_id))
            if len(calls) == 1:
                return [{'scheduling_probe': 41541750, **observer.SETTINGS}]
            return []
        result = observer.sequence(exchange, 'aal-scheduling-control-v1-abc', iter([1000000, 2000000]).__next__)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['probe']['scheduling_probe'], 41541750)
        self.assertEqual(result['metadata']['status'], 'metadata_unavailable')
        self.assertFalse(result['timeout_fixed'])

    def test_scripted_http_captures_exact_wire_parameters_and_two_raw_responses(self):
        requests = []
        responses = [json.dumps({'scheduling_probe': 41541750, **observer.SETTINGS}).encode(), b'']
        class Socket:
            def makefile(self, mode):
                body = responses.pop(0)
                return io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
        class Connection:
            def __init__(self, host, port, timeout):
                if (host, port, timeout) != ('127.0.0.1', 8123, 15):
                    raise AssertionError('endpoint or timeout changed')
            def request(self, method, path, body, headers):
                requests.append((method, path, body, headers))
            def getresponse(self):
                result = self.response_class(Socket())
                result.begin()
                return result
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as folder, patch.dict(observer.os.environ,
                {'CLICKHOUSE_USER': 'scripted-readonly', 'CLICKHOUSE_PASSWORD': 'fixture-secret'}), patch.object(
                    observer.http.client, 'HTTPConnection', Connection):
            out = Path(folder)
            observer.worker(out)
            self.assertEqual(len(requests), 2)
            for method, path, body, headers in requests:
                self.assertEqual(method, 'POST')
                parameters = observer.urllib.parse.parse_qs(observer.urllib.parse.urlsplit(path).query)
                self.assertEqual(parameters['compile_expressions'], ['0'])
                self.assertEqual(parameters['max_execution_time'], ['10'])
                self.assertEqual(parameters['max_memory_usage'], ['134217728'])
                self.assertEqual(parameters['max_threads'], ['2'])
                self.assertEqual(parameters['readonly'], ['1'])
                parameters.pop('query_id')
                self.assertEqual(parameters, {
                    'default_format': ['JSONEachRow'], 'readonly': ['1'],
                    'max_execution_time': ['10'], 'max_result_rows': ['1000'],
                    'result_overflow_mode': ['break'], 'max_rows_to_read': ['10000'],
                    'max_bytes_to_read': ['10485760'], 'max_memory_usage': ['134217728'],
                    'max_threads': ['2'], 'compile_expressions': ['0']})
            self.assertTrue((out / '1-headers.bin').read_bytes().startswith(b'HTTP/1.1 200'))
            self.assertTrue((out / '2-headers.bin').read_bytes().endswith(b'\r\n\r\n'))
            self.assertEqual((out / '2-body.bin').read_bytes(), b'')
            self.assertNotIn(b'fixture-secret', b''.join(p.read_bytes() for p in out.iterdir()))

    def test_default_cli_only_prints_protocol_without_creating_capture(self):
        result = observer.subprocess.run([observer.sys.executable, '-B', str(HERE / 'observer.py')],
            capture_output=True, text=True, timeout=3, check=True)
        self.assertEqual(json.loads(result.stdout)['version'], 'phase2-scheduling-control-v1')
        self.assertEqual(result.stderr, '')

    def test_parent_timeout_preserves_terminal_receipt_without_replacement(self):
        class Child:
            killed = False
            def wait(self, timeout):
                if self.killed:
                    return -9
                raise observer.subprocess.TimeoutExpired('scripted observer', timeout)
            def kill(self):
                self.killed = True
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'capture'
            context = Path(folder) / 'context.json'
            context.write_text('{"resource_window":"scripted-window-reference"}')
            digest = observer.hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest()
            arguments = ['observer.py', '--run', '--context', str(context), '--out', str(out),
                '--expected-commit', 'scripted-commit', '--protocol-sha256', digest]
            with patch.object(observer.sys, 'argv', arguments), patch.object(observer.subprocess,
                    'check_output', side_effect=['scripted-commit', '']), patch.object(
                    observer.subprocess, 'Popen', return_value=Child()):
                self.assertEqual(observer.main(), -9)
            receipt = json.loads((out / 'receipt.json').read_text())
            self.assertEqual(receipt['termination'], 'hard_wall_limit')
            self.assertEqual(receipt['remaining_launches'], 0)
            self.assertEqual(receipt['treatment_a_attempts'], 0)
            seal = json.loads((out / 'sha256.json').read_text())
            self.assertEqual(seal['receipt.json'], observer.hashlib.sha256((out / 'receipt.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
