"""Qualification wiring tests use temporary pins and injected offline delegates."""

from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import passive_capture as capture
from scripts import qualify_phase2_once as runner


ROOT = Path(__file__).resolve().parents[1]


class ScriptedModel:
    model = 'hermes-local:qwen3.5-9b'
    base_url = 'http://127.0.0.1:11434'
    timeout = 120

    def __init__(self, steps):
        self.steps = iter(steps)
        self.inputs = []

    def respond(self, messages, tools):
        self.inputs.append((messages[:], tools))
        step = next(self.steps)
        if isinstance(step, BaseException):
            raise step
        return step


class TestQualificationRunner(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        paths = set(capture.CONTRACT_PATHS) | {
            'src/evals/system_benchmark/scope_observation_v1.py',
            'scripts/qualify_phase2_once.py',
            'scripts/passive_capture.py',
        }
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'evals/system_benchmark/corpus').glob('*') if p.is_file())
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.config = json.loads((ROOT / 'configurations/phase2-runtime-schema-v1-scope-observation-v1.proposal.json').read_text())
        self.config.update(owner_observation_approval='approved', runtime_offline_validity_gate='passed')
        self.config_path = self.root / 'configurations/approved-offline-fixture.json'
        self.config_path.parent.mkdir()
        self.git('init', '-q')
        self.pin()
        self.out = Path(self.temp.name) / 'evidence'
        self.get = Mock(side_effect=self.service_get)
        self.setup_query = Mock(side_effect=lambda sql: runner.EXPECTED_SCHEMA_ROWS if sql.startswith('DESCRIBE') else [{'row_count': 500}])

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()

    def pin(self):
        self.config['benchmark_contract_sha256'] = capture.contract_fingerprint(self.root)['benchmark_contract_sha256']
        self.config_path.write_text(json.dumps(self.config))
        self.git('add', '.')
        self.git('-c', 'user.name=Offline Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'offline fixture', '--allow-empty', '--no-gpg-sign')
        self.request = capture.CaptureRequest(self.root, self.git('rev-parse', 'HEAD'), self.config_path,
            hashlib.sha256(self.config_path.read_bytes()).hexdigest(), True, 'offline-authorization-fixture')

    def service_get(self, url):
        if url.endswith('/api/tags'):
            return {'models': [dict(self.config['model'], size=123, details={'family': 'offline'}),
                               {'name': 'unrelated-private-model', 'digest': 'not-for-evidence'}]}
        if url.endswith('/api/ps'):
            return {'models': [{'name': self.config['model']['name'], 'digest': self.config['model']['digest'],
                                'size': 123, 'size_vram': 456, 'context_length': 65536}]}
        self.fail('unexpected service endpoint')

    @staticmethod
    def model_steps():
        return [
            {'type': 'tool_call', 'name': 'query_clickhouse', 'arguments': {
                'sql': "SELECT team,100.0 * SUM(blocked) / COUNT(*) AS blocked_pct FROM agentic_analytics.delivery_work_items WHERE status != 'done' GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"}},
            {'type': 'tool_call', 'name': 'retrieve_policy', 'arguments': {'query': 'Blocker rate percentage KPI dictionary', 'top_k': 1}},
            {'type': 'final', 'content': json.dumps({'disposition': 'answer',
                'answer_text': 'Data has the highest active-work blocker rate at 17.8%. The KPI divides blocked active items by active items. This does not establish causality.'})},
        ]

    def run_offline(self, *, model=None, evidence_query=None, **kwargs):
        from src.tools.policy_retrieval import retrieve_policy
        model = model or ScriptedModel(self.model_steps())
        return runner.qualify_once(self.request, self.out,
            model_factory=Mock(return_value=model), query_fn=evidence_query or Mock(return_value=[{'team': 'Data', 'blocked_pct': 17.77777777777778}]),
            policy_fn=retrieve_policy, service_json_get=self.get, service_query_fn=self.setup_query,
            os_snapshot=lambda: {'offline_host': True}, **kwargs)

    def events(self):
        return [json.loads(line) for line in (self.out / 'events.jsonl').read_text().splitlines()]

    def test_pending_configuration_refuses_before_constructor_network_or_folder(self):
        self.config.update(owner_observation_approval='pending', runtime_offline_validity_gate='scope_controls_passed_overall_evaluator_unaccepted')
        self.pin()
        factory = Mock(side_effect=AssertionError('model constructor must not run'))
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(capture.CaptureRefused):
                runner.qualify_once(self.request, self.out, model_factory=factory,
                    service_json_get=self.get, service_query_fn=self.setup_query)
        factory.assert_not_called()
        self.get.assert_not_called()
        self.setup_query.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_run_and_approval_reference_are_mandatory(self):
        for request in (replace(self.request, run=False), replace(self.request, approval_reference='')):
            with self.subTest(request=request), self.assertRaises(capture.CaptureRefused):
                runner.qualify_once(request, self.out, service_json_get=self.get)
        self.get.assert_not_called()

    def test_loaded_corpus_must_match_every_pinned_contract_file_before_services(self):
        path = self.root / 'evals/system_benchmark/corpus/kpi_dictionary_v1.md'
        path.write_text(path.read_text() + '\nOffline candidate corpus differs.\n')
        self.pin()  # Legitimate temporary candidate pin; loaded corpus is still different.
        factory = Mock(side_effect=AssertionError('model constructor must not run'))
        with self.assertRaises(capture.CaptureRefused):
            runner.qualify_once(self.request, self.out, model_factory=factory,
                service_json_get=self.get, service_query_fn=self.setup_query)
        factory.assert_not_called()
        self.get.assert_not_called()
        self.setup_query.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_success_uses_exact_runner_and_two_evidence_calls_separate_from_setup(self):
        query = Mock(return_value=[{'team': 'Data', 'blocked_pct': 17.77777777777778}])
        model = ScriptedModel(self.model_steps())
        result = self.run_offline(model=model, evidence_query=query)
        self.assertTrue(result['task_success'])
        self.assertEqual(result['model_calls'], 3)
        self.assertEqual(result['tool_call_count'], 2)
        self.assertEqual(query.call_count, 1)
        self.assertEqual(self.setup_query.call_count, 2)
        self.assertEqual(len(model.inputs), 3)
        for messages, _tools in model.inputs:
            self.assertEqual(messages[1]['content'], json.loads((self.root / 'evals/system_benchmark/development_tasks.json').read_text())[2]['request'])
        raw = json.loads((self.out / 'raw-result.json').read_text())
        self.assertEqual(raw, result)
        self.assertTrue((self.out / 'execution.json').is_file())
        self.assertTrue((self.out / 'INVOCATION_STARTED.json').is_file())
        events = self.events()
        setup = next(event for event in events if event['event'] == 'qualification_service_preflight')
        self.assertEqual(setup['report']['setup_sql_calls'], 2)
        self.assertNotIn('unrelated-private-model', json.dumps(events))
        self.assertEqual(sum(event['event'] == 'worker_enter' for event in events), 1)
        self.assertEqual(sum(event['event'] == 'resource_snapshot' for event in events), 2)

    def test_service_identity_schema_and_count_fail_before_model_constructor(self):
        for defect in ('digest', 'schema', 'count'):
            with self.subTest(defect=defect):
                get = Mock(side_effect=self.service_get)
                query = Mock(side_effect=self.setup_query.side_effect)
                if defect == 'digest':
                    get.return_value = {'models': [{'name': self.config['model']['name'], 'digest': 'wrong'}]}
                    get.side_effect = None
                if defect == 'schema':
                    query.side_effect = lambda _sql: [{'name': 'invented', 'type': 'String'}]
                if defect == 'count':
                    query.side_effect = lambda sql: runner.EXPECTED_SCHEMA_ROWS if sql.startswith('DESCRIBE') else [{'row_count': 499}]
                factory = Mock()
                with self.assertRaises(capture.CaptureRefused):
                    runner.qualify_once(self.request, self.out, model_factory=factory,
                        service_json_get=get, service_query_fn=query)
                factory.assert_not_called()
                self.assertFalse(self.out.exists())

    def test_exception_is_original_no_score_no_retry_and_pre_query_sql_is_preserved(self):
        failure = RuntimeError('offline query failure')
        query = Mock(side_effect=failure)
        model = ScriptedModel(self.model_steps())
        with patch('src.evals.system_benchmark.runner.score_response', side_effect=AssertionError('must not score an exception')) as score:
            with self.assertRaises(RuntimeError) as caught:
                self.run_offline(model=model, evidence_query=query)
        self.assertIs(caught.exception, failure)
        score.assert_not_called()
        self.assertEqual(query.call_count, 1)
        self.assertEqual(len(model.inputs), 1)
        self.assertFalse((self.out / 'raw-result.json').exists())
        self.assertFalse((self.out / 'execution.json').exists())
        self.assertTrue((self.out / 'INVOCATION_STARTED.json').exists())
        event = next(event for event in self.events() if event['event'] == 'query_clickhouse_start')
        self.assertEqual(event['input']['args'][0], self.model_steps()[0]['arguments']['sql'])
        self.assertEqual(json.loads((self.out / 'error.json').read_text())['type'], 'RuntimeError')

    def test_existing_evidence_folder_refuses_before_service_calls(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            self.run_offline()
        self.get.assert_not_called()

    def test_d01_budget_and_route_boundaries_refuse_before_model(self):
        task_path = self.root / 'evals/system_benchmark/development_tasks.json'
        original = task_path.read_text()
        for field, value in (('budget', 3), ('expected_route', 'local'),
                             ('expected_capability_profile', 'documents'), ('allowed_tools', ['query_clickhouse'])):
            payload = json.loads(original)
            if field == 'budget':
                payload[2]['trajectory']['max_tool_calls'] = value
            else:
                payload[2][field] = value
            task_path.write_text(json.dumps(payload))
            self.pin()
            factory = Mock()
            with self.subTest(field=field), patch.object(runner, 'ROOT', self.root), self.assertRaises(capture.CaptureRefused):
                runner.qualify_once(self.request, self.out, model_factory=factory,
                    service_json_get=self.get, service_query_fn=self.setup_query)
            factory.assert_not_called()
        self.get.assert_not_called()

    def test_default_cli_is_source_preflight_only_and_current_pending_config_is_unreachable(self):
        self.config.update(owner_observation_approval='pending')
        self.pin()
        arguments = ['qualify_phase2_once.py', '--root', str(self.root), '--expected-commit', self.request.expected_commit,
                     '--config', str(self.config_path), '--config-sha256', self.request.config_sha256]
        with patch.object(sys, 'argv', arguments), patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 2)
        self.assertFalse(self.out.exists())

    def test_cli_keeps_task_success_but_blocks_incomplete_capture_qualification(self):
        result = {'task_success': True, 'unaltered_result': 'offline'}
        arguments = ['qualify_phase2_once.py', '--root', str(self.root), '--expected-commit', self.request.expected_commit,
                     '--config', str(self.config_path), '--config-sha256', self.request.config_sha256,
                     '--out', str(self.out), '--run', '--approval-reference', 'offline-cli-fixture']
        for bad_field in ('collector_status', 'postflight', 'worker_invocations'):
            manifest = {'collector_status': 'complete', 'postflight': {'valid': True}, 'worker_invocations': 1}
            manifest[bad_field] = {'collector_status': 'incomplete', 'postflight': {'valid': False}, 'worker_invocations': 0}[bad_field]
            self.out.mkdir(exist_ok=True)
            (self.out / 'manifest.json').write_text(json.dumps(manifest))
            (self.out / 'raw-result.json').write_text(json.dumps(result))
            raw_before = (self.out / 'raw-result.json').read_bytes()
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(field=bad_field), patch.object(sys, 'argv', arguments), \
                 patch.object(runner, 'qualify_once', return_value=result) as delegate, \
                 redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(runner.main(), 2)
            self.assertIn('qualification blocked', stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue()), result)
            self.assertEqual((self.out / 'raw-result.json').read_bytes(), raw_before)
            self.assertTrue(result['task_success'])
            delegate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
