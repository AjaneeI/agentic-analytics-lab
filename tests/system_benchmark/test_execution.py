"""The gateway enforces boundaries before observable backend side effects."""
import importlib
import json
from dataclasses import asdict, replace
from pathlib import Path
import unittest

from src.evals.system_benchmark.contracts import (
    BenchmarkSplit, CapabilityProfile, ResponseDisposition, SystemBenchmarkResponse,
)
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references

ROOT = Path(__file__).resolve().parents[2]


def pair(case_id):
    tasks = load_tasks(ROOT / 'evals/system_benchmark/development_tasks.json')
    refs = load_references(ROOT / 'evals/system_benchmark/development_references.json')
    task = next(t for t in tasks if t.case_id == case_id)
    return task, next(r for r in refs if r.reference_solution_id == task.reference_solution_id)


class CountingBackend:
    def __init__(self):
        self.calls = []

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return {
            'backend': 'test_replay',
            'evidence': [{
                'ref': 'structured:delivery_work_items',
                'source_type': 'structured', 'source_id': 'delivery_work_items',
                'values': {'team': 'Data', 'blocked_pct': 20.86, 'scope': 'all_work_items'},
            }],
        }


class TestExecution(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module('src.evals.system_benchmark.execution')
        except ModuleNotFoundError as exc:
            self.fail(f'Execution contract is not implemented: {exc}')
        self.task, self.ref = pair('SB-A01')
        self.backend = CountingBackend()

    def output(self, values=None, refs=('structured:delivery_work_items',)):
        return self.m.WorkerOutput(
            response=SystemBenchmarkResponse(ResponseDisposition.ANSWER, 'Data at 20.86%.', refs),
            answer_values={'team': 'Data', 'blocked_pct': 20.86} if values is None else values,
            route='deterministic',
        )

    def adapter(self, public_task, tools):
        result = tools.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        return self.output(result['evidence'][0]['values'])

    def test_conforming_record_has_observed_tools_and_grounded_values(self):
        record = self.m.execute_task(self.task, self.ref, self.adapter, self.backend)
        self.assertTrue(record.passed, record.reason_codes)
        data = record.to_dict()
        self.assertEqual(data['schema_version'], 'system-benchmark-execution-v1')
        self.assertEqual(data['route_source'], 'scripted_plan')
        self.assertEqual(data['trace'][0]['status'], 'succeeded')
        self.assertEqual(data['trace'][0]['sequence'], 1)
        self.assertEqual(data['score']['reason_codes'], [])
        self.assertEqual(len(self.backend.calls), 1)
        self.assertEqual(json.loads(record.to_json()), data)

    def test_adapter_projection_excludes_reference_and_oracle_metadata(self):
        seen = []
        def adapter(public, tools):
            seen.append(set(asdict(public)))
            return self.adapter(public, tools)
        self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertEqual(seen, [{'case_id', 'request', 'allowed_tools'}])

    def test_forbidden_tool_never_reaches_backend(self):
        gateway = self.m.ToolGateway(self.task, self.backend)
        with self.assertRaisesRegex(self.m.ToolFailure, 'forbidden_tool'):
            gateway.call('retrieve_policy', {'query': 'x'})
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(gateway.events[0].status, 'rejected')

    def test_unknown_tool_never_reaches_backend(self):
        gateway = self.m.ToolGateway(self.task, self.backend)
        with self.assertRaisesRegex(self.m.ToolFailure, 'unexpected_tool'):
            gateway.call('shell', {'command': 'echo x'})
        self.assertEqual(self.backend.calls, [])

    def test_capability_rejects_allowed_but_unavailable_tool(self):
        task = replace(self.task, expected_capability_profile=CapabilityProfile.NONE)
        gateway = self.m.ToolGateway(task, self.backend)
        with self.assertRaisesRegex(self.m.ToolFailure, 'capability_denied'):
            gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        self.assertEqual(self.backend.calls, [])

    def test_write_sql_and_unlisted_read_sql_do_not_dispatch(self):
        for sql, reason in [('DELETE FROM agentic_analytics.delivery_work_items', 'sql_rejected'),
                            ('SELECT 1', 'query_not_in_replay_allowlist')]:
            with self.subTest(sql=sql):
                gateway = self.m.ToolGateway(self.task, self.backend)
                with self.assertRaisesRegex(self.m.ToolFailure, reason):
                    gateway.call('query_clickhouse', {'sql': sql})
        self.assertEqual(self.backend.calls, [])

    def test_invalid_policy_arguments_do_not_dispatch(self):
        task, _ = pair('SB-C01')
        for arguments in [
            {'query': 'blocker', 'top_k': True}, {'query': 'blocker', 'top_k': 6},
            {'query': 'blocker', 'as_of': '20260101'},
            {'query': 'blocker', 'as_of': '2026-02-30'},
            {'query': 'blocker', 'corpus_root': '/tmp'}, {'query': ' '},
        ]:
            with self.subTest(arguments=arguments):
                with self.assertRaises(self.m.ToolFailure):
                    self.m.ToolGateway(task, self.backend).call('retrieve_policy', arguments)
        self.assertEqual(self.backend.calls, [])

    def test_invalid_and_oversized_request_do_not_dispatch(self):
        gateway = self.m.ToolGateway(self.task, self.backend)
        for arguments in [None, [], {'sql': 1}, {'sql': 'x'*10001}, {'sql': self.m.ALL_ITEMS_SQL, 'password': 'SECRET'}]:
            with self.subTest(kind=type(arguments).__name__):
                with self.assertRaises(self.m.ToolFailure):
                    gateway.call('query_clickhouse', arguments)
        self.assertEqual(self.backend.calls, [])
        self.assertNotIn('SECRET', str([e.to_dict() for e in gateway.events]))

    def test_call_budget_precedes_backend_dispatch(self):
        gateway = self.m.ToolGateway(self.task, self.backend, max_calls=2)
        for _ in range(2):
            gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        with self.assertRaisesRegex(self.m.ToolFailure, 'tool_budget_exceeded'):
            gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        self.assertEqual(len(self.backend.calls), 2)
        for value in [True, 0, 9, '2']:
            with self.assertRaises(ValueError):
                self.m.ToolGateway(self.task, self.backend, max_calls=value)

    def test_mutating_return_does_not_mutate_trace(self):
        gateway = self.m.ToolGateway(self.task, self.backend)
        result = gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        before = gateway.events[0].to_dict()
        result['evidence'][0]['values']['team'] = 'FORGED'
        self.assertEqual(gateway.events[0].to_dict(), before)
        self.assertEqual(before['result']['evidence'][0]['values']['team'], 'Data')

    def test_backend_error_is_recorded_without_secret_or_fallback(self):
        class Broken(CountingBackend):
            def execute(self, name, arguments):
                self.calls.append(name)
                raise RuntimeError('password=SECRET')
        backend = Broken()
        record = self.m.execute_task(self.task, self.ref, self.adapter, backend)
        self.assertFalse(record.passed)
        self.assertIn('tool_execution_failed', record.reason_codes)
        self.assertNotIn('SECRET', record.to_json())
        self.assertEqual(len(backend.calls), 1)

    def test_invalid_backend_result_is_failure_not_tool_success(self):
        class Invalid(CountingBackend):
            def execute(self, name, arguments):
                return {'backend': 'test', 'evidence': 'not-a-list'}
        record = self.m.execute_task(self.task, self.ref, self.adapter, Invalid())
        self.assertFalse(record.passed)
        self.assertIn('invalid_tool_result', record.reason_codes)
        self.assertEqual(record.to_dict()['trace'][0]['status'], 'failed')

    def test_fabricated_citation_is_not_grounded_by_just_naming_a_tool(self):
        def adapter(public, tools):
            return self.output()
        result = self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertFalse(result.passed)
        self.assertIn('unobserved_evidence_ref', result.reason_codes)
        self.assertIn('missing_required_tool', result.reason_codes)

    def test_worker_cannot_forge_values_by_mutating_backend_return(self):
        def adapter(public, tools):
            result = tools.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
            result['evidence'][0]['values']['blocked_pct'] = 99.0
            return self.output(result['evidence'][0]['values'])
        result = self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertFalse(result.passed)
        self.assertIn('ungrounded_answer_values', result.reason_codes)

    def test_wrong_value_fails_with_correct_observed_tool_record(self):
        def adapter(public, tools):
            tools.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
            return self.output({'team': 'Data', 'blocked_pct': 99.0})
        result = self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertIn('structured_value_mismatch', result.reason_codes)
        self.assertIn('ungrounded_answer_values', result.reason_codes)

    def test_heldout_task_rejected_before_adapter_or_backend(self):
        task = replace(self.task, split=BenchmarkSplit.HELDOUT)
        invoked = []
        with self.assertRaisesRegex(ValueError, 'development'):
            self.m.execute_task(task, self.ref, lambda *_: invoked.append(True), self.backend)
        self.assertEqual(invoked, [])
        self.assertEqual(self.backend.calls, [])

    def test_bad_reference_fails_before_adapter(self):
        ref = replace(self.ref, reference_solution_id='WRONG')
        invoked = []
        with self.assertRaisesRegex(ValueError, 'reference_solution_id'):
            self.m.execute_task(self.task, ref, lambda *_: invoked.append(True), self.backend)
        self.assertEqual(invoked, [])

    def test_nonfinite_answer_value_does_not_create_valid_json_score(self):
        def adapter(public, tools):
            tools.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
            return self.output({'team': 'Data', 'blocked_pct': float('nan')})
        result = self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertFalse(result.passed)
        self.assertIn('invalid_response', result.reason_codes)
        self.assertNotIn('NaN', result.to_json())

    def test_four_response_envelopes_round_trip(self):
        for kind in ResponseDisposition:
            payload = {'disposition': kind.value, 'answer_text': 'Bounded response', 'evidence_refs': [], 'uncertainty': None, 'clarification': None, 'handoff': None}
            if kind is ResponseDisposition.CLARIFY:
                payload['clarification'] = {'concept': 'reporting period'}
            if kind is ResponseDisposition.HANDOFF:
                payload['handoff'] = {'trigger': 'conflict', 'evidence_refs': ['policy:x@1#s'], 'actions_taken': ['retrieved'], 'unresolved_uncertainty': 'authority', 'requested_authority': 'service owner'}
            with self.subTest(kind=kind):
                response = self.m.response_from_dict(payload)
                self.assertEqual(self.m.response_to_dict(response), payload)

    def test_handoff_shape_and_extra_reasoning_are_rejected(self):
        payload = {'disposition': 'handoff', 'answer_text': 'Escalate', 'evidence_refs': [], 'handoff': {}}
        with self.assertRaises(ValueError):
            self.m.response_from_dict(payload)
        payload = {'disposition': 'answer', 'answer_text': 'ok', 'reasoning': 'hidden'}
        with self.assertRaises(ValueError):
            self.m.response_from_dict(payload)

    def test_reference_changes_do_not_change_observed_execution(self):
        first = self.m.execute_task(self.task, self.ref, self.adapter, self.backend)
        ref = replace(self.ref, required_answer_terms=('absent_literal',))
        second = self.m.execute_task(self.task, ref, self.adapter, self.backend)
        self.assertEqual(first.to_dict()['trace'], second.to_dict()['trace'])
        self.assertEqual(first.to_dict()['response'], second.to_dict()['response'])
        self.assertTrue(first.passed)
        self.assertFalse(second.passed)

    def test_missing_worker_output_after_tool_success_has_explicit_reason(self):
        def adapter(public, tools):
            tools.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
            return None
        record = self.m.execute_task(self.task, self.ref, adapter, self.backend)
        self.assertFalse(record.passed)
        self.assertIn('invalid_response', record.reason_codes)

    def test_backend_hidden_reasoning_field_is_not_captured(self):
        class Invalid(CountingBackend):
            def execute(self, name, arguments):
                result = super().execute(name, arguments)
                result['evidence'][0]['reasoning'] = 'SECRET-HIDDEN-REASONING'
                return result
        record = self.m.execute_task(self.task, self.ref, self.adapter, Invalid())
        self.assertFalse(record.passed)
        self.assertIn('invalid_tool_result', record.reason_codes)
        self.assertNotIn('SECRET-HIDDEN-REASONING', record.to_json())

    def test_wrong_evidence_kind_for_tool_is_rejected(self):
        task, ref = pair('SB-C01')
        def adapter(public, tools):
            tools.call('retrieve_policy', {'query': 'kpi-dictionary'})
            return self.m.WorkerOutput(SystemBenchmarkResponse(ResponseDisposition.ANSWER, 'blocked items / active items'))
        record = self.m.execute_task(task, ref, adapter, self.backend)
        self.assertFalse(record.passed)
        self.assertIn('invalid_tool_result', record.reason_codes)
        self.assertEqual(record.to_dict()['trace'][0]['status'], 'failed')

    def test_oversized_backend_result_is_rejected(self):
        class Oversized(CountingBackend):
            def execute(self, name, arguments):
                result = super().execute(name, arguments)
                item = result['evidence'][0]
                item['values'] = {'large': 'x' * 8500}
                result['evidence'] = [item] * 10
                return result
        record = self.m.execute_task(self.task, self.ref, self.adapter, Oversized())
        self.assertFalse(record.passed)
        self.assertIn('tool_result_too_large', record.reason_codes)

    def test_repeated_budget_denials_do_not_grow_trace_unbounded(self):
        gateway = self.m.ToolGateway(self.task, self.backend, max_calls=1)
        gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        for _ in range(20):
            with self.assertRaisesRegex(self.m.ToolFailure, 'tool_budget_exceeded'):
                gateway.call('query_clickhouse', {'sql': self.m.ALL_ITEMS_SQL})
        self.assertEqual(len(gateway.events), 2)
        self.assertEqual(len(self.backend.calls), 1)
