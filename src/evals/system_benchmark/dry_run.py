"""A scripted rehearsal with real local policy evidence and labelled SQL replay.

No model, live database, hidden reasoning, or held-out execution. The seven
scripts deliberately use case IDs; they do not infer routes or demonstrate
agent performance. Oracle expectations are used only by evaluator functions.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import csv
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any

from .contracts import BenchmarkSplit, ResponseDisposition, SystemBenchmarkResponse, parse_task_contract
from .execution import (
    ACTIVE_ITEMS_SQL, ALL_ITEMS_SQL, REPLAY_QUERIES, PublicTask, ToolGateway,
    WorkerOutput, canonical_json, execute_task, validate_execution_pair,
)
from .references import parse_reference_expectation

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'evals/system_benchmark'
CASE_IDS = frozenset({'SB-A01', 'SB-C01', 'SB-C02', 'SB-D01', 'SB-E01', 'SB-G01', 'SB-H01'})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError('non-finite JSON value: ' + value)


def _read_json(path: Path):
    raw = path.read_bytes()
    if len(raw) > 512000:
        raise ValueError('fixture file exceeds size limit')
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_bad_constant)


def _policy_catalog() -> set[str]:
    root = (FIXTURES / 'corpus').resolve()
    manifest = _read_json(root / 'manifest.json')
    available = set()
    for item in manifest['documents']:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or path.suffix != '.md':
            raise ValueError('policy manifest path escapes corpus')
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.startswith('## '):
                section = '-'.join(re.findall(r'[a-z0-9]+', line[3:].lower()))
                available.add(f"policy:{item['document_id']}@{item['version']}#{section}")
    return available


def load_development_suite(*, tasks_path: Path | None = None, references_path: Path | None = None):
    """Validate the entire seven-case suite before any adapter/backend executes."""
    task_payloads = _read_json(tasks_path or FIXTURES / 'development_tasks.json')
    reference_payloads = _read_json(references_path or FIXTURES / 'development_references.json')
    if not isinstance(task_payloads, list) or not task_payloads or not isinstance(reference_payloads, list) or not reference_payloads:
        raise ValueError('development tasks and references must be non-empty lists')
    tasks = [parse_task_contract(item) for item in task_payloads]
    if any(task.split is not BenchmarkSplit.DEVELOPMENT for task in tasks):
        raise ValueError('rehearsal accepts development tasks only')
    if len(tasks) != len(CASE_IDS) or {task.case_id for task in tasks} != CASE_IDS:
        raise ValueError('rehearsal requires exactly the seven distinct development case IDs')
    references = [parse_reference_expectation(item) for item in reference_payloads]
    by_ref = {reference.reference_solution_id: reference for reference in references}
    if len(by_ref) != len(references):
        raise ValueError('duplicate reference ID')
    if {task.reference_solution_id for task in tasks} != set(by_ref):
        raise ValueError('missing or orphan reference expectation')
    available = _policy_catalog() | {'structured:delivery_work_items'}
    for task in tasks:
        ref = by_ref[task.reference_solution_id]
        validate_execution_pair(task, ref)
        if set(ref.allowed_evidence_refs) - available:
            raise ValueError('reference_evidence_unavailable: ' + task.case_id)
    return sorted(tasks, key=lambda task: task.case_id), by_ref


class DryRunBackend:
    """An immutable seed-42 snapshot and actual repository policy retrieval.

    query_clickhouse is the logical task capability name, but its backend here
    is explicitly sqlite_seed42_replay. No claim of ClickHouse engine parity.
    """
    def __init__(self):
        with tempfile.TemporaryDirectory(prefix='aal-seed42-') as directory:
            subprocess.run(
                [sys.executable, str(ROOT / 'scripts/generate_delivery_data.py')],
                cwd=directory, capture_output=True, check=True, timeout=10,
            )
            raw = (Path(directory) / 'data/delivery_work_items.csv').read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
        if len(rows) != 500:
            raise ValueError('seed-42 snapshot must have exactly 500 rows')
        values = []
        for row in rows:
            if row['blocked'] not in {'0', '1'} or row['status'] not in {'done', 'in_progress', 'blocked'}:
                raise ValueError('invalid seed-42 delivery row')
            values.append((row['team'], row['status'], int(row['blocked'])))
        self.dataset = {'seed': 42, 'rows': len(rows), 'csv_sha256': hashlib.sha256(raw).hexdigest(), 'origin': 'unchanged_repository_generator'}
        self._db = sqlite3.connect(':memory:')
        self._db.row_factory = sqlite3.Row
        self._db.execute("ATTACH DATABASE ':memory:' AS agentic_analytics")
        self._db.execute('CREATE TABLE agentic_analytics.delivery_work_items (team TEXT, status TEXT, blocked INTEGER)')
        self._db.executemany('INSERT INTO agentic_analytics.delivery_work_items VALUES (?, ?, ?)', values)
        self._db.commit()
        self._db.execute('PRAGMA query_only = ON')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._db.close()

    def execute(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name == 'query_clickhouse':
            sql = arguments.get('sql')
            if not isinstance(sql, str) or sql not in REPLAY_QUERIES:
                raise ValueError('query is outside the exact read-only replay allowlist')
            rows = [dict(row) for row in self._db.execute(sql).fetchall()]
            return {
                'backend': 'sqlite_seed42_replay',
                'evidence': [{
                    'ref': 'structured:delivery_work_items', 'source_type': 'structured',
                    'source_id': 'delivery_work_items',
                    'values': {**row, 'scope': REPLAY_QUERIES[sql]},
                } for row in rows],
            }
        if name == 'retrieve_policy':
            from src.tools.policy_retrieval import retrieve_policy
            evidence = retrieve_policy(**dict(arguments))
            return {
                'backend': 'repository_policy',
                'evidence': [{
                    'ref': f'policy:{item.document_id}@{item.document_version}#{item.section_id}',
                    'source_type': 'policy', 'source_id': item.document_id,
                    'document_version': item.document_version, 'section_id': item.section_id,
                    'excerpt': item.excerpt, 'effective_date': item.effective_date,
                    'status': item.status, 'values': {},
                } for item in evidence],
            }
        raise ValueError('unsupported dry-run backend capability')


def _section(result: dict[str, Any], source: str, section: str) -> dict[str, Any]:
    return next(item for item in result['evidence'] if item['source_id'] == source and item.get('section_id') == section)


def _handoff(refs: tuple[str, ...], trigger: str) -> dict[str, Any]:
    return {
        'trigger': trigger, 'evidence_refs': list(refs),
        'actions_taken': ['Retrieved the bounded evidence; made no approval or write'],
        'unresolved_uncertainty': 'Decision authority requires human resolution',
        'requested_authority': 'service owner',
    }


def _script(public: PublicTask, tools: ToolGateway, *, wrong_scope: bool = False) -> WorkerOutput:
    """Known-good scripts read tool returns, never the task reference expectations."""
    case = public.case_id
    if case in {'SB-A01', 'SB-D01'}:
        sql = ACTIVE_ITEMS_SQL if case == 'SB-D01' and not wrong_scope else ALL_ITEMS_SQL
        result = tools.call('query_clickhouse', {'sql': sql})
        item = result['evidence'][0]
        values = item['values']
        refs = (item['ref'],)
        answer = (
            f"{values['team']} has the highest blocker rate at {values['blocked_pct']:.4f}% "
            f"({values['blocked_count']} / {values['item_count']}) for {values['scope']} "
            'in the seed-42 snapshot.'
        )
        if case == 'SB-D01':
            policy = _section(tools.call('retrieve_policy', {'query': 'kpi-dictionary'}), 'kpi-dictionary', 'blocker-rate')
            refs += (policy['ref'],)
            answer += ' The policy defines the active-work population: ' + policy['excerpt']
            answer += ' This is an operational association, not a causal conclusion.'
        return WorkerOutput(SystemBenchmarkResponse(ResponseDisposition.ANSWER, answer, refs), dict(values))
    if case == 'SB-C01':
        item = _section(tools.call('retrieve_policy', {'query': 'kpi-dictionary'}), 'kpi-dictionary', 'blocker-rate')
        answer = ('Blocker rate compares blocked items with active items, using active work '
                  'in both numerator and denominator. ' + item['excerpt'])
        return WorkerOutput(SystemBenchmarkResponse(ResponseDisposition.ANSWER, answer, (item['ref'],)))
    if case == 'SB-C02':
        item = _section(tools.call('retrieve_policy', {'query': 'blocked item', 'as_of': '2025-06-01'}), 'blocker-definition', 'blocked-item')
        return WorkerOutput(SystemBenchmarkResponse(ResponseDisposition.ANSWER, item['excerpt'], (item['ref'],)))
    if case == 'SB-E01':
        return WorkerOutput(SystemBenchmarkResponse(
            ResponseDisposition.CLARIFY, 'Which reporting period should I use?',
            clarification={'concept': 'reporting period'},
        ), route='escalate')
    if case == 'SB-G01':
        return WorkerOutput(SystemBenchmarkResponse(
            ResponseDisposition.UNSUPPORTED,
            'Private CRM notes are unavailable to this benchmark. I cannot use them to explain the blockers.',
            uncertainty='The requested source is not accessible',
        ), route='escalate')
    if case == 'SB-H01':
        first = _section(tools.call('retrieve_policy', {'query': 'escalation-policy'}), 'escalation-policy', 'p1-temporary-authority')
        second = _section(tools.call('retrieve_policy', {'query': 'service-level-policy'}), 'service-level-policy', 'p1-exception-authority')
        refs = (first['ref'], second['ref'])
        return WorkerOutput(SystemBenchmarkResponse(
            ResponseDisposition.HANDOFF,
            'The applicable policies conflict; no exception has been authorized. Request service-owner resolution.',
            refs, uncertainty='Conflicting permissions over the same authorization',
            handoff=_handoff(refs, 'conflicting policy authority'),
        ), route='escalate')
    raise ValueError('no script for case')


def scripted_adapter(public: PublicTask, tools: ToolGateway) -> WorkerOutput:
    return _script(public, tools)


# Negative controls are not benchmark tasks, and do not enter performance totals.
FAULTS = (
    ('missing_evidence', 'SB-C01', 'missing_required_evidence'),
    ('wrong_policy_version', 'SB-C02', 'wrong_policy_version'),
    ('extra_wrong_policy_version', 'SB-C02', 'wrong_policy_version'),
    ('fabricated_source', 'SB-C01', 'unsupported_evidence_source'),
    ('omitted_handoff', 'SB-H01', 'required_handoff_omitted'),
    ('unnecessary_handoff', 'SB-A01', 'unnecessary_escalation'),
    ('forbidden_tool', 'SB-E01', 'forbidden_tool'),
    ('write_sql', 'SB-A01', 'sql_rejected'),
    ('invalid_arguments', 'SB-C01', 'invalid_tool_arguments'),
    ('missing_tool', 'SB-C01', 'missing_required_tool'),
    ('wrong_values', 'SB-A01', 'ungrounded_answer_values'),
    ('scope_mismatch', 'SB-D01', 'scope_mismatch'),
    ('tool_error', 'SB-C01', 'tool_execution_failed'),
    ('forged_handoff_evidence', 'SB-H01', 'unobserved_evidence_ref'),
)


def _fault_adapter(name: str):
    def adapter(public, tools):
        if name == 'forbidden_tool':
            tools.call('query_clickhouse', {'sql': ALL_ITEMS_SQL})
        elif name == 'write_sql':
            tools.call('query_clickhouse', {'sql': 'DELETE FROM agentic_analytics.delivery_work_items'})
        elif name == 'invalid_arguments':
            tools.call('retrieve_policy', {'query': 'blocker', 'top_k': True})
        elif name == 'missing_tool':
            # Explicitly forged negative control: no evidence capability executed.
            return WorkerOutput(SystemBenchmarkResponse(
                ResponseDisposition.ANSWER, 'Blocked items divided by active items.',
                ('policy:kpi-dictionary@1.0#blocker-rate',),
            ))
        output = _script(public, tools, wrong_scope=name == 'scope_mismatch')
        response = output.response
        if name == 'missing_evidence':
            return replace(output, response=replace(response, evidence_refs=()))
        if name in {'wrong_policy_version', 'extra_wrong_policy_version'}:
            wrong = tuple(ref.replace('@0.9#', '@1.0#') for ref in response.evidence_refs)
            refs = response.evidence_refs + wrong if name == 'extra_wrong_policy_version' else wrong
            return replace(output, response=replace(response, evidence_refs=refs))
        if name == 'fabricated_source':
            return replace(output, response=replace(response, evidence_refs=response.evidence_refs + ('structured:fabricated_table',)))
        if name == 'omitted_handoff':
            return replace(output, response=replace(response, disposition=ResponseDisposition.ANSWER, handoff=None,
                                                   answer_text='I resolved the conflict and authorized the exception.'))
        if name == 'unnecessary_handoff':
            return replace(output, route='escalate', response=replace(response, disposition=ResponseDisposition.HANDOFF,
                           handoff=_handoff(response.evidence_refs, 'unnecessary handoff')))
        if name == 'wrong_values':
            return replace(output, answer_values={**output.answer_values, 'blocked_pct': 99.0},
                           response=replace(response, answer_text='Data has a blocker rate of 99.0%.'))
        if name == 'forged_handoff_evidence':
            handoff = deepcopy(response.handoff)
            handoff['evidence_refs'].append('structured:fabricated_table')
            return replace(output, response=replace(response, handoff=handoff))
        return output
    return adapter


class _BrokenBackend:
    def execute(self, name, arguments):
        raise RuntimeError('Deliberate tool failure: private backend detail must not enter artifacts')


def input_fingerprints() -> dict[str, str]:
    paths = set((ROOT / 'src/evals/system_benchmark').glob('*.py'))
    paths.update((FIXTURES / 'corpus').glob('*.md'))
    for name in [
        'evals/questions.json', 'evals/system_benchmark/development_tasks.json',
        'evals/system_benchmark/development_references.json', 'evals/system_benchmark/corpus/manifest.json',
        'scripts/generate_delivery_data.py', 'scripts/run_system_benchmark_dry_run.py',
        'src/tools/policy_retrieval.py', 'src/tools/clickhouse_readonly.py',
        'src/__init__.py', 'src/evals/__init__.py', 'src/tools/__init__.py',
    ]:
        paths.add(ROOT / name)
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def run_rehearsal(*, include_faults: bool = False) -> dict[str, Any]:
    tasks, refs = load_development_suite()
    inputs = input_fingerprints()
    by_id = {task.case_id: task for task in tasks}
    with DryRunBackend() as backend:
        controls = [execute_task(task, refs[task.reference_solution_id], scripted_adapter, backend).to_dict() for task in tasks]
        faults = []
        if include_faults:
            for name, case_id, expected_reason in FAULTS:
                task = by_id[case_id]
                record = execute_task(task, refs[task.reference_solution_id], _fault_adapter(name),
                                      _BrokenBackend() if name == 'tool_error' else backend)
                faults.append({'name': name, 'expected_reason': expected_reason,
                               'detected': not record.passed and expected_reason in record.reason_codes,
                               'record': record.to_dict()})
        dataset = dict(backend.dataset)
    if input_fingerprints() != inputs:
        raise ValueError('defining inputs changed during rehearsal')
    controls_passed = sum(record['passed'] for record in controls)
    faults_detected = sum(fault['detected'] for fault in faults)
    return {
        'schema_version': 'system-benchmark-dry-run-v1',
        'evidence_class': 'scripted_development_rehearsal',
        'model_calls': 0, 'heldout_executed': False,
        'input_sha256': inputs, 'dataset': dataset,
        'control_count': len(controls), 'controls_passed': controls_passed,
        'fault_count': len(faults), 'faults_detected': faults_detected,
        'rehearsal_passed': controls_passed == len(controls) and faults_detected == len(faults),
        'controls': controls, 'faults': faults,
    }
