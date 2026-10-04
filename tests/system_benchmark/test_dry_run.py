"""Model-free controls and deliberate corruptions, not performance trials."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TestDryRun(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module('src.evals.system_benchmark.dry_run')
        except ModuleNotFoundError as exc:
            self.fail(f'Dry-run harness is not implemented: {exc}')

    def test_seven_real_evidence_controls_pass(self):
        report = self.m.run_rehearsal(include_faults=False)
        self.assertTrue(report['rehearsal_passed'])
        self.assertEqual(report['control_count'], 7)
        self.assertEqual(report['controls_passed'], 7)
        self.assertEqual(report['model_calls'], 0)
        self.assertEqual(report['evidence_class'], 'scripted_development_rehearsal')
        self.assertEqual(report['dataset']['rows'], 500)
        self.assertEqual(report['dataset']['seed'], 42)
        self.assertEqual({c['case_id'] for c in report['controls']}, {'SB-A01', 'SB-C01', 'SB-C02', 'SB-D01', 'SB-E01', 'SB-G01', 'SB-H01'})

    def test_structured_replay_computes_all_and_active_populations(self):
        from src.evals.system_benchmark.execution import ALL_ITEMS_SQL, ACTIVE_ITEMS_SQL
        with self.m.DryRunBackend() as backend:
            all_row = backend.execute('query_clickhouse', {'sql': ALL_ITEMS_SQL})['evidence'][0]['values']
            active_row = backend.execute('query_clickhouse', {'sql': ACTIVE_ITEMS_SQL})['evidence'][0]['values']
            self.assertEqual((all_row['team'], all_row['blocked_count'], all_row['item_count']), ('Data', 29, 139))
            self.assertAlmostEqual(all_row['blocked_pct'], 100 * 29 / 139)
            self.assertEqual((active_row['team'], active_row['blocked_count'], active_row['item_count']), ('Data', 8, 45))
            self.assertAlmostEqual(active_row['blocked_pct'], 100 * 8 / 45)
            self.assertEqual(active_row['scope'], 'active_work_items')
            self.assertNotAlmostEqual(all_row['blocked_pct'], active_row['blocked_pct'])

    def test_multisource_reference_matches_actual_active_population(self):
        # This fails on the original PR C oracle of 20.9; not copied from the scorer.
        tasks, _ = self.m.load_development_suite()
        task = next(t for t in tasks if t.case_id == 'SB-D01')
        expected = {v.name: v.value for v in task.expected_values}
        self.assertAlmostEqual(expected['blocked_pct'], round(100 * 8 / 45, 1))
        self.assertEqual(expected['scope'], 'active_work_items')
        self.assertIn('active', task.request.lower())

    def test_policy_evidence_is_actual_retriever_output(self):
        from src.tools.policy_retrieval import retrieve_policy
        with self.m.DryRunBackend() as backend:
            result = backend.execute('retrieve_policy', {'query': 'blocked item', 'as_of': '2025-06-01', 'top_k': 3})
        actual = retrieve_policy('blocked item', as_of='2025-06-01', top_k=3)
        self.assertEqual([e['excerpt'] for e in result['evidence']], [e.excerpt for e in actual])
        self.assertTrue(all(e['document_version'] == '0.9' for e in result['evidence']))
        self.assertTrue(all('material progress' not in e['excerpt'].lower() for e in result['evidence']))

    def test_handoff_gathers_both_policies_and_preserves_authority_boundary(self):
        report = self.m.run_rehearsal()
        record = next(c for c in report['controls'] if c['case_id'] == 'SB-H01')
        self.assertEqual(record['response']['disposition'], 'handoff')
        self.assertEqual(len(record['response']['evidence_refs']), 2)
        self.assertTrue(all(t['status'] == 'succeeded' for t in record['trace']))
        self.assertEqual(record['response']['handoff']['requested_authority'], 'service owner')
        self.assertIn('no exception has been authorized', record['response']['answer_text'].lower())

    def test_clarification_and_unsupported_controls_execute_no_tools(self):
        report = self.m.run_rehearsal()
        records = {c['case_id']: c for c in report['controls']}
        for case in ['SB-E01', 'SB-G01']:
            self.assertEqual(records[case]['trace'], [])
        self.assertEqual(records['SB-E01']['response']['disposition'], 'clarify')
        self.assertEqual(records['SB-G01']['response']['disposition'], 'unsupported')

    def test_every_injected_fault_fails_for_its_predeclared_reason(self):
        report = self.m.run_rehearsal(include_faults=True)
        self.assertTrue(report['rehearsal_passed'], [(f['name'], f['record']['reason_codes']) for f in report['faults']])
        required = {'missing_evidence', 'wrong_policy_version', 'extra_wrong_policy_version', 'fabricated_source',
                    'omitted_handoff', 'unnecessary_handoff', 'forbidden_tool', 'write_sql', 'invalid_arguments',
                    'missing_tool', 'wrong_values', 'scope_mismatch', 'tool_error', 'forged_handoff_evidence'}
        self.assertEqual({f['name'] for f in report['faults']}, required)
        self.assertEqual(report['faults_detected'], len(required))
        for fault in report['faults']:
            with self.subTest(fault=fault['name']):
                self.assertFalse(fault['record']['passed'])
                self.assertTrue(fault['detected'])
                self.assertIn(fault['expected_reason'], fault['record']['reason_codes'])

    def test_blocked_fault_records_do_not_claim_backend_success(self):
        report = self.m.run_rehearsal(include_faults=True)
        for fault in report['faults']:
            if fault['name'] in {'forbidden_tool', 'write_sql', 'invalid_arguments'}:
                self.assertTrue(all(event['status'] == 'rejected' for event in fault['record']['trace']))
                self.assertTrue(all(event['result'] is None for event in fault['record']['trace']))

    def test_replay_backend_rejects_unlisted_sql_even_if_called_directly(self):
        with self.m.DryRunBackend() as backend:
            with self.assertRaises(ValueError):
                backend.execute('query_clickhouse', {'sql': 'DROP TABLE agentic_analytics.delivery_work_items'})
            with self.assertRaises(ValueError):
                backend.execute('shell', {})

    def test_fixture_validation_rejects_heldout_before_script_invocation(self):
        tasks = json.loads((ROOT / 'evals/system_benchmark/development_tasks.json').read_text())
        tasks[0]['split'] = 'heldout'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tasks.json'
            path.write_text(json.dumps(tasks), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'development'):
                self.m.load_development_suite(tasks_path=path)

    def test_unknown_policy_reference_is_rejected_before_execution(self):
        refs = json.loads((ROOT / 'evals/system_benchmark/development_references.json').read_text())
        entry = next(r for r in refs if r['reference_solution_id'] == 'REF-C01')
        entry['required_evidence_refs'] = ['policy:kpi-dictionary@999#blocker-rate']
        entry['allowed_evidence_refs'] = list(entry['required_evidence_refs'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'references.json'
            path.write_text(json.dumps(refs), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'reference_evidence_unavailable'):
                self.m.load_development_suite(references_path=path)

    def test_duplicate_json_keys_and_missing_reference_fail_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'refs.json'
            path.write_text('[{"reference_solution_id":"A","reference_solution_id":"B"}]')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                self.m.load_development_suite(references_path=path)
            refs = json.loads((ROOT / 'evals/system_benchmark/development_references.json').read_text())
            path.write_text(json.dumps(refs[:-1]))
            with self.assertRaisesRegex(ValueError, 'reference'):
                self.m.load_development_suite(references_path=path)

    def test_provenance_pins_inputs_and_backend_results(self):
        report = self.m.run_rehearsal()
        hashes = report['input_sha256']
        for name in ['evals/system_benchmark/development_tasks.json', 'evals/system_benchmark/development_references.json',
                     'src/evals/system_benchmark/scoring.py', 'src/evals/system_benchmark/execution.py',
                     'src/tools/policy_retrieval.py', 'scripts/generate_delivery_data.py']:
            self.assertEqual(hashes[name], hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        from src.evals.system_benchmark.execution import canonical_json
        for record in report['controls']:
            for event in record['trace']:
                if event['result'] is not None:
                    self.assertEqual(event['result_sha256'], hashlib.sha256(canonical_json(event['result']).encode()).hexdigest())

    def test_identical_bytes_across_processes_and_hash_seeds(self):
        command = [sys.executable, str(ROOT/'scripts/run_system_benchmark_dry_run.py'), '--include-faults']
        outputs = [subprocess.check_output(command, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': seed}, timeout=20)
                   for seed in ['1', '7', '42']]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])
        self.assertNotIn(str(ROOT).encode(), outputs[0])
        self.assertNotIn(b'created_at', outputs[0])

    def test_cli_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'evidence.json'
            output.write_text('PRESERVE')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/run_system_benchmark_dry_run.py'), '--output', str(output)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), 'PRESERVE')

    def test_real_rehearsal_has_no_network_or_model_imports(self):
        probe = '''
import sys

def deny_network(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo'}:
        raise RuntimeError('network prohibited during dry-run')
sys.addaudithook(deny_network)
from src.evals.system_benchmark.dry_run import run_rehearsal
report = run_rehearsal(include_faults=True)
assert report['rehearsal_passed']
for name in sys.modules:
    assert not any(name == p or name.startswith(p + '.') for p in ('src.agents', 'ollama', 'openai', 'anthropic'))
print('offline model-free rehearsal passed')
'''
        result = subprocess.run([sys.executable, '-c', probe], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_scalar_expectation_fails_whole_suite_preflight(self):
        tasks = json.loads((ROOT / 'evals/system_benchmark/development_tasks.json').read_text())
        tasks[0]['expected_values'][0]['value'] = {'nested': 'unsupported'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tasks.json'
            path.write_text(json.dumps(tasks))
            with self.assertRaisesRegex(ValueError, 'scalar'):
                self.m.load_development_suite(tasks_path=path)

    def test_duplicate_expected_names_fail_whole_suite_preflight(self):
        tasks = json.loads((ROOT / 'evals/system_benchmark/development_tasks.json').read_text())
        tasks[0]['expected_values'].append(dict(tasks[0]['expected_values'][0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'tasks.json'
            path.write_text(json.dumps(tasks))
            with self.assertRaisesRegex(ValueError, 'duplicate expected value'):
                self.m.load_development_suite(tasks_path=path)

    def test_unrelated_failures_do_not_count_as_detected_faults(self):
        from unittest.mock import patch
        from src.evals.system_benchmark.execution import ExecutionRecord, canonical_json
        unrelated = ExecutionRecord(False, ('adapter_failed',), canonical_json({'passed': False, 'reason_codes': ['adapter_failed']}))
        with patch.object(self.m, 'execute_task', return_value=unrelated):
            report = self.m.run_rehearsal(include_faults=True)
        self.assertFalse(report['rehearsal_passed'])
        self.assertEqual(report['faults_detected'], 0)
