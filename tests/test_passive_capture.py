"""Offline only: no service, model, database, shell agent or benchmark invocation."""

from dataclasses import replace
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts import passive_capture as capture


class OfflineModel:
    model = 'hermes-local:qwen3.5-9b'
    base_url = 'http://127.0.0.1:11434'
    timeout = 120

    def __init__(self, response):
        self.response = response
        self.calls = []

    def respond(self, messages, tools):
        self.calls.append((messages, tools))
        return self.response


class TestPassiveCapture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        # A synthetic repository, not a copied benchmark or held-out task bank.
        self.tool = {'name': 'query_clickhouse', 'description': 'offline fixture', 'input_schema': {}}
        for relative in capture.CONTRACT_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('offline fixture\n')
        (self.root / 'src/evals/system_benchmark/local_worker.py').write_text('_QUERY_TOOL = ' + repr(self.tool))
        corpus = self.root / 'evals/system_benchmark/corpus'
        corpus.mkdir()
        (corpus / 'fixture.md').write_text('offline public policy')
        self.config = {
            'configuration_id': 'offline-capture-test-v1', 'task_id': 'SB-D01',
            'benchmark_contract_sha256': capture.contract_fingerprint(self.root)['benchmark_contract_sha256'],
            'query_tool_sha256': hashlib.sha256(json.dumps(self.tool, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'runtime_offline_validity_gate': 'passed',
            'model': {'name': OfflineModel.model, 'base_url': OfflineModel.base_url, 'timeout_seconds': 120,
                      'temperature': 0, 'num_predict': 512, 'num_ctx': 65536,
                      'digest': '0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c'},
            'limits': {'model_steps': 6, 'evidence_calls': 2, 'retries': 0, 'reprompts': 0},
            'allowed_tools': ['query_clickhouse', 'retrieve_policy'],
        }
        self.config_path = self.root / 'configuration.json'
        self.config_path.write_text(json.dumps(self.config))
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'offline fixture', '--no-gpg-sign')
        self.request = capture.CaptureRequest(
            root=self.root, expected_commit=self.git('rev-parse', 'HEAD').strip(),
            config_path=self.config_path, config_sha256=hashlib.sha256(self.config_path.read_bytes()).hexdigest(),
            run=True, approval_reference='offline-test-fixture-only',
        )
        self.out = Path(self.temp.name) / 'evidence'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL)

    def events(self):
        return [json.loads(line) for line in (self.out / 'events.jsonl').read_text().splitlines()]

    def run_capture(self, execute, **kwargs):
        return capture.capture_once(self.request, self.out, execute, snapshot=lambda: {'fixture': True}, **kwargs)

    def test_success_preserves_identity_arguments_and_records_before_delegate(self):
        response = {'type': 'final', 'content': 'public answer',
                    '_metrics': {'input_tokens': 7, 'output_tokens': 3, 'total_duration_seconds': 1.5},
                    'thinking': 'PRIVATE_REASONING'}
        model = OfflineModel(response)
        messages, tools = [{'role': 'user', 'content': 'offline question'}], [self.tool, {'name': 'retrieve_policy'}]
        result_object = {'task_success': False, 'fixture': True}
        def execute(session):
            wrapped_model = session.wrap_model(model)
            def worker():
                manifest = json.loads((self.out / 'manifest.json').read_text())
                self.assertEqual(manifest['worker_invocations'], 1)
                self.assertTrue((self.out / 'INVOCATION_STARTED.json').exists())
                returned = wrapped_model.respond(messages, tools)
                self.assertIs(returned, response)
                return result_object
            return session.wrap_executor(worker)()
        result = self.run_capture(execute)
        self.assertIs(result, result_object)
        self.assertIs(model.calls[0][0], messages)
        self.assertIs(model.calls[0][1], tools)
        self.assertEqual(len(model.calls), 1)
        self.assertNotIn('PRIVATE_REASONING', (self.out / 'events.jsonl').read_text())
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual(manifest['attempt_status'], 'completed')
        self.assertEqual(manifest['worker_invocations'], 1)
        self.assertEqual(manifest['partial_metrics']['model_returns'], 1)
        self.assertEqual(manifest['partial_metrics']['input_tokens'], 7)
        self.assertEqual(manifest['partial_metrics'].get('model_duration_seconds_known'), 1.5)

    def test_tools_and_models_cannot_run_outside_recorded_worker_entry(self):
        calls = []
        def execute(session):
            tool = session.wrap_tool('query_clickhouse', lambda sql: calls.append(sql))
            with self.assertRaises(capture.CaptureRefused):
                tool('SELECT 1')
            model = OfflineModel({'type': 'final', 'content': 'offline'})
            with self.assertRaises(capture.CaptureRefused):
                session.wrap_model(model).respond([], [self.tool, {'name': 'retrieve_policy'}])
            self.assertFalse(model.calls)
            return session.wrap_executor(lambda: {'fixture': True})()
        self.run_capture(execute)
        self.assertEqual(calls, [])

    def test_runner_cannot_turn_a_swallowed_worker_failure_into_completion(self):
        failure = RuntimeError('offline worker failure')
        def worker():
            raise failure
        def execute(session):
            try:
                session.wrap_executor(worker)()
            except RuntimeError:
                return {'task_success': True}
        with self.assertRaises(RuntimeError) as caught:
            self.run_capture(execute)
        self.assertIs(caught.exception, failure)
        self.assertEqual(json.loads((self.out / 'manifest.json').read_text())['attempt_status'], 'execution_error')

    def test_dataclass_and_string_enum_results_are_recorded_without_changing_them(self):
        class Disposition(str, Enum):
            ANSWER = 'answer'
        @dataclass
        class Execution:
            disposition: Disposition
        returned = Execution(Disposition.ANSWER)
        self.assertIs(self.run_capture(lambda session: session.wrap_executor(lambda: returned)()), returned)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertFalse(manifest['collector_errors'])
        self.assertEqual(next(e['result'] for e in self.events() if e['event'] == 'worker_return'),
                         {'disposition': 'answer'})

    def test_pin_is_rechecked_after_assembly_before_reserving_worker_entry(self):
        def execute(session):
            self.config_path.write_text('changed after preflight')
            return session.wrap_executor(lambda: self.fail('worker must not run'))()
        with self.assertRaises(capture.CaptureRefused):
            self.run_capture(execute)
        self.assertFalse((self.out / 'INVOCATION_STARTED.json').exists())

    def test_sql_is_durable_before_query_and_original_error_survives_snapshots(self):
        failure = RuntimeError('offline query failed')
        calls = []
        sql = 'SELECT team FROM fixture WHERE status != \'done\''
        def query(actual_sql):
            calls.append(actual_sql)
            self.assertEqual(self.events()[-1]['input']['args'], [sql])
            raise failure
        def execute(session):
            tool = session.wrap_tool('query_clickhouse', query)
            return session.wrap_executor(lambda: tool(sql))()
        def broken_snapshot():
            raise OSError('offline sampler unavailable')
        with self.assertRaises(RuntimeError) as caught:
            capture.capture_once(self.request, self.out, execute, snapshot=broken_snapshot)
        self.assertIs(caught.exception, failure)
        self.assertEqual(calls, [sql])
        events = self.events()
        self.assertEqual(sum(e['event'] == 'query_clickhouse_start' for e in events), 1)
        self.assertEqual(sum(e['event'] == 'query_clickhouse_error' for e in events), 1)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual(manifest['attempt_status'], 'execution_error')
        self.assertEqual(manifest['worker_invocations'], 1)
        self.assertEqual(manifest['partial_metrics']['tool_attempts'], 1)
        self.assertEqual(manifest['partial_metrics']['tool_returns'], 0)
        self.assertEqual(len(manifest['collector_errors']), 2)

    def test_policy_wrapper_forwards_exact_kwargs_and_return_identity(self):
        response = [{'source': 'fixture', 'section_id': 'public', 'text': 'policy'}]
        calls = []
        def policy(*args, **kwargs):
            calls.append((args, kwargs))
            return response
        def execute(session):
            wrapped = session.wrap_tool('retrieve_policy', policy)
            return session.wrap_executor(lambda: wrapped('question', as_of='2026-10-17', top_k=2))()
        self.assertIs(self.run_capture(execute), response)
        self.assertEqual(calls, [(('question',), {'as_of': '2026-10-17', 'top_k': 2})])

    def test_second_executor_entry_is_blocked_without_extra_delegate_call(self):
        calls = []
        def execute(session):
            worker = session.wrap_executor(lambda: calls.append('called'))
            worker()
            worker()
        with self.assertRaises(FileExistsError):
            self.run_capture(execute)
        self.assertEqual(calls, ['called'])
        self.assertEqual(json.loads((self.out / 'manifest.json').read_text())['worker_invocations'], 1)

    def test_reusing_evidence_folder_never_overwrites_or_calls_again(self):
        self.run_capture(lambda session: session.wrap_executor(lambda: {'fixture': True})())
        original = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaises(FileExistsError):
            self.run_capture(lambda session: self.fail('must not enter callback'))
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_missing_authorization_or_bad_pins_have_no_output_or_invocation(self):
        for request in [replace(self.request, run=False), replace(self.request, approval_reference=''),
                        replace(self.request, expected_commit='0' * 40),
                        replace(self.request, config_sha256='0' * 64)]:
            with self.subTest(request=request):
                with self.assertRaises(capture.CaptureRefused):
                    capture.capture_once(request, self.out, lambda session: self.fail('unexpected entry'))
                self.assertFalse(self.out.exists())

    def test_blocked_scope_configuration_cannot_consume_invocation(self):
        self.config['runtime_offline_validity_gate'] = 'blocked_missing_scope_observation'
        self.config_path.write_text(json.dumps(self.config))
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'blocked fixture', '--no-gpg-sign')
        request = replace(self.request, expected_commit=self.git('rev-parse', 'HEAD').strip(),
                          config_sha256=hashlib.sha256(self.config_path.read_bytes()).hexdigest())
        with self.assertRaisesRegex(capture.CaptureRefused, 'validity'):
            capture.capture_once(request, self.out, lambda session: self.fail('unexpected entry'))
        self.assertFalse(self.out.exists())

    def test_contract_drift_is_rejected_even_with_new_commit(self):
        (self.root / capture.CONTRACT_PATHS[0]).write_text('changed offline fixture')
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'changed fixture', '--no-gpg-sign')
        request = replace(self.request, expected_commit=self.git('rev-parse', 'HEAD').strip())
        with self.assertRaisesRegex(capture.CaptureRefused, 'fingerprint'):
            capture.capture_once(request, self.out, lambda session: self.fail('unexpected entry'))

    def test_failure_before_worker_entry_leaves_zero_count_and_no_marker(self):
        failure = ValueError('offline assembly failure')
        def execute(session):
            raise failure
        with self.assertRaises(ValueError) as caught:
            self.run_capture(execute)
        self.assertIs(caught.exception, failure)
        self.assertFalse((self.out / 'INVOCATION_STARTED.json').exists())
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual(manifest['worker_invocations'], 0)
        self.assertEqual(manifest['attempt_status'], 'pre_invocation_error')

    def test_model_failure_preserves_prior_metrics_and_rethrows_same_object(self):
        failure = TimeoutError('offline model timeout')
        model = OfflineModel({'type': 'tool_call', 'name': 'query_clickhouse', 'arguments': {'sql': 'SELECT 1'},
                              '_metrics': {'input_tokens': 4, 'output_tokens': 2}})
        original_respond = model.respond
        def respond(messages, tools):
            if model.calls:
                raise failure
            return original_respond(messages, tools)
        model.respond = respond
        def execute(session):
            wrapped = session.wrap_model(model)
            def worker():
                wrapped.respond([], [self.tool, {'name': 'retrieve_policy'}])
                wrapped.respond([], [self.tool, {'name': 'retrieve_policy'}])
            return session.wrap_executor(worker)()
        with self.assertRaises(TimeoutError) as caught:
            self.run_capture(execute)
        self.assertIs(caught.exception, failure)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual(manifest['partial_metrics']['model_attempts'], 2)
        self.assertEqual(manifest['partial_metrics']['model_returns'], 1)
        self.assertEqual(manifest['partial_metrics']['input_tokens'], 4)

    def test_import_is_offline_and_does_not_load_runtime(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run([sys.executable, '-c',
            "import sys; import scripts.passive_capture; "
            "assert not any(n.startswith(('src', 'requests', 'httpx', 'openai')) for n in sys.modules)"],
            cwd=root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_resource_snapshot_labels_host_and_shared_ollama_with_rss_units(self):
        pid = capture.os.getpid()
        output = f'{pid} 1 2.5 1024 python\n99999 1 3.0 2048 ollama runner\n88888 1 4.0 4096 unrelated\n'
        with patch.object(capture.subprocess, 'run', return_value=SimpleNamespace(stdout=output)), \
             patch.object(capture.resource, 'getrusage', return_value=SimpleNamespace(ru_utime=3.0, ru_stime=1.0, ru_maxrss=2048)):
            observed = capture.resource_snapshot()
        self.assertEqual(observed['worker_host_pid'], pid)
        self.assertEqual([p['pid'] for p in observed['processes']], [pid, 99999])
        self.assertEqual(observed['processes'][0]['rss_bytes'], 1048576)
        self.assertEqual(observed['process_cpu_user_seconds'], 3.0)
        self.assertIn('shared', observed['limits'])

    def test_finalization_write_failure_does_not_replace_original_worker_error(self):
        failure = TimeoutError('offline worker failure')
        original = capture.CaptureSession.write_manifest
        def write(session):
            if 'end_utc' in session.manifest:
                raise OSError('offline disk failure')
            return original(session)
        def worker():
            raise failure
        with patch.object(capture.CaptureSession, 'write_manifest', write):
            with self.assertRaises(TimeoutError) as caught:
                self.run_capture(lambda session: session.wrap_executor(worker)())
        self.assertIs(caught.exception, failure)
        self.assertTrue((self.out / 'INVOCATION_STARTED.json').exists())
        # A missing finalization remains visibly incomplete, never a success.
        self.assertEqual(json.loads((self.out / 'manifest.json').read_text())['attempt_status'], 'started')

    def test_cli_preflight_never_runs_and_run_flag_requires_future_activation_adapter(self):
        script = Path(capture.__file__).resolve()
        command = [sys.executable, str(script), '--root', str(self.root),
                   '--expected-commit', self.request.expected_commit, '--config', str(self.config_path),
                   '--config-sha256', self.request.config_sha256]
        checked = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)['runtime_validity_gate'], 'passed')
        refused = subprocess.run(command + ['--run', '--approval-reference', 'offline-fixture-only'],
                                 capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_existing_bounded_executor_runs_only_injected_offline_delegates(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor, _QUERY_TOOL
        from src.tools.policy_retrieval import PolicyEvidence
        from tests.system_benchmark.test_local_worker import sb_d01, final_payload

        self.tool = _QUERY_TOOL
        (self.root / 'src/evals/system_benchmark/local_worker.py').write_text('_QUERY_TOOL = ' + repr(self.tool))
        self.config['query_tool_sha256'] = hashlib.sha256(json.dumps(self.tool, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.config['benchmark_contract_sha256'] = capture.contract_fingerprint(self.root)['benchmark_contract_sha256']
        self.config_path.write_text(json.dumps(self.config))
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'real tool schema offline fixture', '--no-gpg-sign')
        self.request = replace(self.request, expected_commit=self.git('rev-parse', 'HEAD').strip(),
                               config_sha256=hashlib.sha256(self.config_path.read_bytes()).hexdigest())
        responses = [
            {'type': 'tool_call', 'name': 'query_clickhouse', 'arguments': {
                'sql': "SELECT team, avg(blocked)*100 AS blocked_pct FROM agentic_analytics.delivery_work_items WHERE status != 'done' GROUP BY team"}},
            {'type': 'tool_call', 'name': 'retrieve_policy', 'arguments': {'query': 'KPI blocker rate'}},
            {'type': 'final', 'content': final_payload()},
        ]
        model = OfflineModel(None)
        def respond(messages, tools):
            model.calls.append((messages, tools))
            return responses.pop(0)
        model.respond = respond
        tool_calls = []
        def query(sql):
            tool_calls.append('query')
            return [{'team': 'Data', 'blocked_pct': 20.9}]
        def policy(**kwargs):
            tool_calls.append('policy')
            return [PolicyEvidence('kpi-dictionary', '1.0', 'blocker-rate',
                                   'Blocked items divided by active items.', '2026-01-01', 'active')]
        def execute(session):
            worker = BoundedLocalExecutor(model=session.wrap_model(model),
                query_fn=session.wrap_tool('query_clickhouse', query),
                policy_fn=session.wrap_tool('retrieve_policy', policy))
            return session.wrap_executor(worker)(sb_d01(), 1, None)
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden in offline test')):
            returned = self.run_capture(execute)
        self.assertEqual(returned.model_calls, 3)
        self.assertEqual(tool_calls, ['query', 'policy'])
        self.assertEqual(len(model.calls), 3)
        self.assertFalse(json.loads((self.out / 'manifest.json').read_text())['collector_errors'])

    def test_output_inside_source_is_refused_before_any_mutation(self):
        with self.assertRaises(capture.CaptureRefused):
            capture.capture_once(self.request, self.root / 'evidence', lambda session: self.fail('unexpected entry'))
        self.assertFalse((self.root / 'evidence').exists())

    def test_postflight_source_drift_is_separate_from_unchanged_return(self):
        returned = {'fixture': True}
        def worker():
            self.config_path.write_text('changed during offline invocation')
            return returned
        actual = self.run_capture(lambda session: session.wrap_executor(worker)())
        self.assertIs(actual, returned)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertFalse(manifest.get('postflight', {}).get('valid', True))
        self.assertEqual(manifest['collector_status'], 'incomplete')

    def test_broken_exception_string_cannot_mask_delegate_failure(self):
        class BrokenError(RuntimeError):
            def __str__(self):
                raise ValueError('offline formatting failure')
        failure = BrokenError()
        def worker():
            raise failure
        with self.assertRaises(BrokenError) as caught:
            self.run_capture(lambda session: session.wrap_executor(worker)())
        self.assertIs(caught.exception, failure)

    def test_unsupported_result_capture_marks_incomplete_and_preserves_return(self):
        returned = object()
        self.assertIs(self.run_capture(lambda session: session.wrap_executor(lambda: returned)()), returned)
        manifest = json.loads((self.out / 'manifest.json').read_text())
        self.assertEqual(manifest['collector_status'], 'incomplete')
        self.assertEqual(manifest['attempt_status'], 'completed')
        self.assertTrue(any(item['stage'] == 'worker_return' for item in manifest['collector_errors']))

    def test_configuration_cannot_relabel_fixed_runtime_model_options(self):
        approved = dict(self.config['model'])
        for field, wrong in [('temperature', 0.5), ('num_predict', 513), ('num_ctx', 65535),
                             ('timeout_seconds', 121), ('digest', '0' * 64)]:
            with self.subTest(field=field):
                self.config['model'] = dict(approved, **{field: wrong})
                self.config_path.write_text(json.dumps(self.config))
                self.git('add', '.')
                self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                         'commit', '-qm', 'wrong model option fixture', '--no-gpg-sign')
                request = replace(self.request, expected_commit=self.git('rev-parse', 'HEAD').strip(),
                                  config_sha256=hashlib.sha256(self.config_path.read_bytes()).hexdigest())
                out = Path(self.temp.name) / f'evidence-{field}'
                with self.assertRaises(capture.CaptureRefused):
                    capture.capture_once(request, out, lambda session: self.fail('unexpected entry'))
                self.assertFalse(out.exists())

    def test_versioned_scope_module_is_fingerprinted_and_missing_or_changed_is_blocked(self):
        module = self.root / 'src/evals/system_benchmark/scope_observation_v1.py'
        module.write_text('versioned offline scope fixture')
        fingerprint = capture.contract_fingerprint(self.root)
        self.assertIn(str(module.relative_to(self.root)), fingerprint['contract_files'])
        self.config['benchmark_contract_sha256'] = fingerprint['benchmark_contract_sha256']
        self.config_path.write_text(json.dumps(self.config))
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'scope module fixture', '--no-gpg-sign')
        pinned_config_hash = hashlib.sha256(self.config_path.read_bytes()).hexdigest()
        for remove in (False, True):
            with self.subTest(remove=remove):
                if remove:
                    module.unlink()
                else:
                    module.write_text('changed offline scope fixture')
                self.git('add', '-A')
                self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                         'commit', '-qm', 'scope drift fixture', '--no-gpg-sign')
                request = replace(self.request, expected_commit=self.git('rev-parse', 'HEAD').strip(),
                                  config_sha256=pinned_config_hash)
                with self.assertRaisesRegex(capture.CaptureRefused, 'fingerprint'):
                    capture.capture_once(request, self.out, lambda session: self.fail('unexpected entry'))

    def test_json_model_content_private_canary_is_removed_only_from_trace_copy(self):
        content = json.dumps({'disposition': 'answer', 'answer_text': 'public answer',
                              'analysis': 'INDEPENDENT_PRIVATE_JSON_ANALYSIS_CANARY'})
        response = {'type': 'final', 'content': content}
        model = OfflineModel(response)
        def execute(session):
            observed = session.wrap_model(model)
            return session.wrap_executor(lambda: observed.respond([], [self.tool, {'name': 'retrieve_policy'}]))()
        self.assertIs(self.run_capture(execute), response)
        self.assertIs(response['content'], content)
        self.assertIn('INDEPENDENT_PRIVATE_JSON_ANALYSIS_CANARY', response['content'])
        self.assertNotIn('INDEPENDENT_PRIVATE_JSON_ANALYSIS_CANARY', (self.out / 'events.jsonl').read_text())
        for event in self.events():
            if event['event'] in ('model_return', 'worker_return', 'runner_return'):
                self.assertEqual(json.loads(event['result']['content']),
                                 {'disposition': 'answer', 'answer_text': 'public answer'})
                self.assertTrue(event['content_redacted'])
                self.assertEqual(event['content_sha256'], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(json.loads((self.out / 'manifest.json').read_text())['collector_status'], 'complete')

    def test_nested_private_json_keys_are_omitted_without_touching_public_answer_text(self):
        public_text = 'A public answer may discuss analysis or reasoning.'
        content = json.dumps({'answer_text': public_text, 'nested': [
            {'Thinking': 'NESTED_THINKING_CANARY', 'public': 1},
            {'child': {'reasoning_content': 'NESTED_REASONING_CANARY', 'public': 2}}]})
        response = {'type': 'final', 'content': content}
        def execute(session):
            observed = session.wrap_model(OfflineModel(response))
            return session.wrap_executor(lambda: observed.respond([], [self.tool, {'name': 'retrieve_policy'}]))()
        self.assertIs(self.run_capture(execute), response)
        event = next(item for item in self.events() if item['event'] == 'model_return')
        self.assertEqual(json.loads(event['result']['content']),
                         {'answer_text': public_text, 'nested': [{'public': 1}, {'child': {'public': 2}}]})
        self.assertTrue(event['content_redacted'])
        self.assertNotIn('NESTED_THINKING_CANARY', (self.out / 'events.jsonl').read_text())
        self.assertNotIn('NESTED_REASONING_CANARY', (self.out / 'events.jsonl').read_text())

    def test_public_json_string_without_private_keys_keeps_exact_spacing(self):
        content = '  { "answer_text" : "public analysis", "value" : 1.00 }\n'
        response = {'type': 'final', 'content': content}
        def execute(session):
            observed = session.wrap_model(OfflineModel(response))
            return session.wrap_executor(lambda: observed.respond([], [self.tool, {'name': 'retrieve_policy'}]))()
        self.assertIs(self.run_capture(execute), response)
        event = next(item for item in self.events() if item['event'] == 'model_return')
        self.assertEqual(event['result']['content'], content)
        self.assertFalse(event['content_redacted'])
        self.assertEqual(event['content_sha256'], hashlib.sha256(content.encode()).hexdigest())

    def test_json_output_filter_does_not_parse_inputs_sql_policy_or_opaque_text(self):
        content = 'ordinary non-JSON public answer: analysis is useful'
        response = {'type': 'final', 'content': content}
        model = OfflineModel(response)
        messages = [{'role': 'user', 'content': '{"analysis":"INPUT_TRACE_CANARY"}'}]
        sql = 'SELECT \'{"analysis":"SQL_TRACE_CANARY"}\' AS public_text'
        policy_text = '{"analysis":"POLICY_TRACE_CANARY"}'
        def execute(session):
            observed = session.wrap_model(model)
            query = session.wrap_tool('query_clickhouse', lambda statement: [{'text': statement}])
            policy = session.wrap_tool('retrieve_policy', lambda: [policy_text])
            def worker():
                self.assertIs(observed.respond(messages, [self.tool, {'name': 'retrieve_policy'}]), response)
                query(sql)
                policy()
                return {'fixture': True}
            return session.wrap_executor(worker)()
        self.run_capture(execute)
        events = self.events()
        self.assertEqual(next(e for e in events if e['event'] == 'model_start')['input']['messages'], messages)
        self.assertEqual(next(e for e in events if e['event'] == 'query_clickhouse_start')['input']['args'], [sql])
        self.assertEqual(next(e for e in events if e['event'] == 'retrieve_policy_return')['result'], [policy_text])
        returned = next(e for e in events if e['event'] == 'model_return')
        self.assertEqual(returned['result']['content'], content)
        self.assertFalse(returned['content_redacted'])
        self.assertIs(model.calls[0][0], messages)


if __name__ == '__main__':
    unittest.main()
