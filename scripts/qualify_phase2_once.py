#!/usr/bin/env python3
"""Inactive one-entry Treatment A wiring. Default CLI is source preflight only.

Execution requires independently approved pinned configuration and explicit run
authorization. No retry, fallback, SQL rewrite or score on an exception exists.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import passive_capture as capture

VERSION = 'phase2-qualification-runner-v1'
CONFIGURATION_ID = 'phase2-runtime-schema-v1-scope-observation-v1'
SCOPE_VERSION = 'runtime-sql-scope-v1'
TABLE = 'agentic_analytics.delivery_work_items'
SCHEMA_SQL = f'DESCRIBE TABLE {TABLE}'
COUNT_SQL = f'SELECT count() AS row_count FROM {TABLE}'
EXPECTED_SCHEMA_ROWS = [
    {'name': name, 'type': kind} for name, kind in (
        ('work_item_id', 'String'), ('team', 'LowCardinality(String)'),
        ('priority', 'LowCardinality(String)'), ('status', 'LowCardinality(String)'),
        ('created_at', 'DateTime'), ('due_at', 'DateTime'), ('completed_at', 'Nullable(DateTime)'),
        ('planned_hours', 'UInt16'), ('actual_hours', 'Float32'), ('blocked', 'UInt8'),
        ('blocker_type', 'LowCardinality(String)'), ('rework_count', 'UInt8'), ('customer_impact', 'UInt8'),
    )
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_preflight(request: capture.CaptureRequest) -> dict:
    """No services, runtime imports, constructors, output folders or execution."""
    checks = capture.preflight(request)
    # Imported adapter/capture/runtime source must be the pinned bytes, even if
    # a caller supplies another checkout with a superficially matching config.
    paths = list(checks['benchmark_contract']['contract_files'])
    paths += ['scripts/qualify_phase2_once.py', 'scripts/passive_capture.py']
    for name in paths:
        if _sha(ROOT / name) != _sha(request.root / name):
            raise capture.CaptureRefused('loaded adapter/runtime source differs from pinned source')
    config = checks['config']
    blockers = []
    if (config.get('configuration_id') != CONFIGURATION_ID
            or config.get('schema_version') != 'delivery-work-items-schema-v1'
            or config.get('scope_observation_version') != SCOPE_VERSION
            or config.get('standalone_qualification') is not True
            or config.get('architecture_comparison_allowed') is not False):
        blockers.append('configuration_scope_version_or_standalone_boundary_differs')
    if config.get('owner_observation_approval') != 'approved':
        blockers.append('owner_observation_approval_not_approved')
    if config.get('runtime_offline_validity_gate') != 'passed':
        blockers.append('runtime_offline_validity_gate_not_passed')
    return {'runner_version': VERSION, 'checks': checks, 'execution_blockers': blockers,
            'adapter_sha256': _sha(Path(__file__)), 'capture_sha256': _sha(Path(capture.__file__)),
            'source_preflight_only': not request.run, 'services_contacted': False,
            'qualification_or_phase_accepted': False}


def _get_json(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read(1024 * 1024))


def service_preflight(config, *, json_get, query_fn):
    """Fresh read-only setup calls, separate from the two evidence tool calls."""
    started = utc()
    catalog = json_get(config['model']['base_url'] + '/api/tags')
    matches = [item for item in catalog.get('models', []) if item.get('name') == config['model']['name']]
    if len(matches) != 1 or matches[0].get('digest') != config['model']['digest']:
        raise capture.CaptureRefused('fresh Ollama model name/digest differs')
    model = {key: matches[0][key] for key in ('name', 'digest', 'size', 'details') if key in matches[0]}
    schema = query_fn(SCHEMA_SQL)
    projected = [{'name': item.get('name'), 'type': item.get('type')} for item in schema]
    if len(projected) != 13 or sorted(projected, key=lambda row: row['name'] or '') != sorted(EXPECTED_SCHEMA_ROWS, key=lambda row: row['name']):
        raise capture.CaptureRefused('fresh delivery schema differs from approved 13 columns')
    count = query_fn(COUNT_SQL)
    value = count[0].get('row_count') if len(count) == 1 else None
    if type(value) not in (int, str) or str(value) != '500':
        raise capture.CaptureRefused('fresh delivery row count is not 500')
    return {'start_utc': started, 'end_utc': utc(), 'approved_model': model,
            'schema': projected, 'row_count': 500, 'setup_sql_calls': 2,
            'setup_model_catalog_requests': 1, 'setup_sql': [SCHEMA_SQL, COUNT_SQL],
            'boundary': 'Read-only setup observations; excluded from benchmark evidence-call counts.'}


def _task_boundary(root):
    from src.evals.system_benchmark.loader import load_tasks
    from src.evals.system_benchmark.references import load_references, validate_task_reference
    from src.evals.system_benchmark.routing import oracle_route
    tasks = [task for task in load_tasks(root / 'evals/system_benchmark/development_tasks.json') if task.case_id == 'SB-D01']
    if len(tasks) != 1:
        raise capture.CaptureRefused('exact D01 task is missing')
    task = tasks[0]
    decision = oracle_route(task)
    if (decision.reason_code != 'oracle_metadata' or decision.route.value != 'deterministic'
            or decision.capability_profile.value != 'multi_source'
            or task.trajectory.max_tool_calls != 2
            or set(task.allowed_tools) != {'query_clickhouse', 'retrieve_policy'}
            or task.reference_solution_id != 'REF-D01'):
        raise capture.CaptureRefused('D01 oracle/capability/tool-budget boundary differs')
    references = [ref for ref in load_references(root / 'evals/system_benchmark/development_references.json')
                  if ref.reference_solution_id == task.reference_solution_id]
    if len(references) != 1:
        raise capture.CaptureRefused('exact D01 reference is missing')
    validate_task_reference(task, references[0])
    return task, references[0]


def _model_factory(config):
    from src.agents.ollama_client import OllamaModelClient
    return OllamaModelClient(model=config['model']['name'], base_url=config['model']['base_url'],
                             timeout=config['model']['timeout_seconds'])


def _save(session, name, value):
    """Preserve an unedited public JSON copy without masking delegate outcomes."""
    try:
        with (session.out / name).open('x') as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as error:
        session.collector_errors.append({'stage': name, **capture._error(error)})


def qualify_once(request, out, *, model_factory=None, query_fn=None, policy_fn=None,
                 service_json_get=None, service_query_fn=None, os_snapshot=None):
    """Enter the existing worker once after every guard; delegates are injectable."""
    if request.run is not True or not request.approval_reference.strip():
        raise capture.CaptureRefused('explicit run flag and approval reference are required')
    inspected = source_preflight(request)
    if inspected['execution_blockers']:
        raise capture.CaptureRefused(', '.join(inspected['execution_blockers']))
    task, reference = _task_boundary(request.root)
    out = Path(out)
    if out.exists():
        raise FileExistsError('evidence folder already exists; no retry or overwrite')
    if out.resolve().is_relative_to(request.root.resolve()):
        raise capture.CaptureRefused('evidence folder must be outside pinned source')
    from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
    from src.evals.system_benchmark.runner import run_trial
    from src.tools.clickhouse_readonly import query_clickhouse
    from src.tools.policy_retrieval import retrieve_policy
    config = inspected['checks']['config']
    query = query_fn if query_fn is not None else query_clickhouse
    policy = policy_fn if policy_fn is not None else retrieve_policy
    get = service_json_get if service_json_get is not None else _get_json
    services = service_preflight(config, json_get=get,
        query_fn=service_query_fn if service_query_fn is not None else query)

    def snapshot():
        rows = get(config['model']['base_url'] + '/api/ps').get('models', [])
        approved_rows = [{key: row[key] for key in ('name', 'digest', 'size', 'size_vram', 'context_length', 'expires_at', 'details') if key in row}
                         for row in rows if row.get('name') == config['model']['name']]
        sampler = os_snapshot if os_snapshot is not None else capture.resource_snapshot
        return {'utc': utc(), 'os': sampler(),
                'approved_model_api_ps': approved_rows,
                'limits': 'Before/after shared-service and host snapshots, not per-request CPU/GPU/VRAM or peak model memory.'}

    def execute(session):
        session.event('qualification_adapter', version=VERSION, adapter_sha256=inspected['adapter_sha256'],
                      capture_sha256=inspected['capture_sha256'], python_version=sys.version,
                      python_executable=sys.executable, platform=platform.platform())
        session.event('qualification_service_preflight', report=services)
        factory = model_factory if model_factory is not None else _model_factory
        model = factory(config)
        worker = BoundedLocalExecutor(model=session.wrap_model(model),
            query_fn=session.wrap_tool('query_clickhouse', query),
            policy_fn=session.wrap_tool('retrieve_policy', policy),
            max_model_steps=config['limits']['model_steps'])

        def preserve_execution(*args, **kwargs):
            execution = worker(*args, **kwargs)
            _save(session, 'execution.json', asdict(execution))
            return execution

        try:
            result = run_trial(task, reference, trial_number=1, executor=session.wrap_executor(preserve_execution))
        except BaseException as error:
            _save(session, 'error.json', capture._error(error))
            raise
        _save(session, 'raw-result.json', result)
        return result

    return capture.capture_once(request, out, execute, snapshot=snapshot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--approval-reference', default='')
    args = parser.parse_args()
    request = capture.CaptureRequest(args.root, args.expected_commit, args.config, args.config_sha256,
                                     args.run, args.approval_reference)
    if not args.run:
        inspected = source_preflight(request)
        print(json.dumps(inspected, indent=2, sort_keys=True))
        return 2 if inspected['execution_blockers'] else 0
    if args.out is None:
        parser.error('--out is required for an explicitly authorized run')
    result = qualify_once(request, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    try:
        manifest = json.loads((args.out / 'manifest.json').read_text())
        complete = (manifest.get('collector_status') == 'complete'
                    and isinstance(manifest.get('postflight'), dict)
                    and manifest['postflight'].get('valid') is True
                    and type(manifest.get('worker_invocations')) is int
                    and manifest['worker_invocations'] == 1)
    except (OSError, ValueError, TypeError, AttributeError):
        complete = False
    if not complete:
        print('qualification blocked: final collector/postflight/worker-entry evidence is incomplete', file=sys.stderr)
        return 2
    return 0 if result['task_success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
