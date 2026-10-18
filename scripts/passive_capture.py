#!/usr/bin/env python3
"""Version 2 offline-tested capture library; the CLI is preflight-only.

No model, database or benchmark runtime is imported. A future owner-reviewed
adapter must inject the actual executor/model/tools and explicitly authorize
one run. This module never retries, rewrites SQL or scores an outcome.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from typing import Any, Callable

VERSION = 'passive-capture-v2'
CONTRACT_PATHS = (
    'evals/system_benchmark/development_tasks.json',
    'evals/system_benchmark/development_references.json',
    'src/evals/system_benchmark/contracts.py',
    'src/evals/system_benchmark/loader.py',
    'src/evals/system_benchmark/references.py',
    'src/evals/system_benchmark/routing.py',
    'src/evals/system_benchmark/workers.py',
    'src/evals/system_benchmark/local_worker.py',
    'src/evals/system_benchmark/runner.py',
    'src/evals/system_benchmark/scoring.py',
    'src/agents/ollama_client.py',
    'src/tools/clickhouse_readonly.py',
    'src/tools/policy_retrieval.py',
    'scripts/generate_delivery_data.py',
)
PRIVATE_FIELDS = {'thinking', 'reasoning', 'reasoning_content', 'chain_of_thought', 'analysis'}


class CaptureRefused(RuntimeError):
    """No authorized worker invocation was made by this refusal."""


@dataclass(frozen=True)
class CaptureRequest:
    root: Path
    expected_commit: str
    config_path: Path
    config_sha256: str
    run: bool = False
    approval_reference: str = ''


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _public(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _public(asdict(value))
    if isinstance(value, dict):
        return {str(key): _public(item) for key, item in value.items() if str(key).lower() not in PRIVATE_FIELDS}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    if value is None or isinstance(value, str) or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise TypeError(f'unsupported public capture type: {type(value).__name__}')


def _omit_private_json(value: Any) -> tuple[Any, bool]:
    """Remove named private fields from a decoded JSON copy, not from text."""
    if isinstance(value, dict):
        copied, changed = {}, False
        for key, item in value.items():
            if key.lower() in PRIVATE_FIELDS:
                changed = True
            else:
                copied[key], nested_changed = _omit_private_json(item)
                changed |= nested_changed
        return copied, changed
    if isinstance(value, list):
        copied, changed = [], False
        for item in value:
            public, nested_changed = _omit_private_json(item)
            copied.append(public)
            changed |= nested_changed
        return copied, changed
    return value, False


def _model_content_copy(envelope: dict) -> tuple[dict, dict]:
    """Trace-only handling of a known model-return envelope's content string."""
    content = envelope['content']
    copied = dict(envelope)
    changed = False
    try:
        decoded = json.loads(content)
    except (ValueError, TypeError):
        pass  # Opaque text is preserved; this is not general privacy redaction.
    else:
        cleaned, changed = _omit_private_json(decoded)
        if changed:
            copied['content'] = json.dumps(cleaned, sort_keys=True, allow_nan=False)
    return copied, {'content_sha256': _sha(content.encode()), 'content_redacted': changed}


def _error(error: BaseException) -> dict:
    try:
        message = str(error)
    except BaseException:
        message = '<exception message unavailable>'
    public = {'type': type(error).__name__, 'message': message}
    for field in ('http_status', 'server_code', 'server_error_name'):
        value = getattr(error, field, None)
        if type(value) in (str, int):
            public[field] = value
    return public


def contract_fingerprint(root: Path) -> dict:
    """Same declared file list and byte algorithm as the pinned capture block."""
    paths = set(CONTRACT_PATHS)
    scope_module = 'src/evals/system_benchmark/scope_observation_v1.py'
    if (root / scope_module).is_file():
        paths.add(scope_module)
    paths.update(str(path.relative_to(root)) for path in (root / 'evals/system_benchmark/corpus').rglob('*') if path.is_file())
    files = {name: _sha((root / name).read_bytes()) for name in sorted(paths)}
    aggregate = b''.join(name.encode() + b'\0' + digest.encode() + b'\n' for name, digest in files.items())
    return {'benchmark_contract_sha256': _sha(aggregate), 'contract_files': files}


def preflight(request: CaptureRequest) -> dict:
    """Read-only source/config checks; no service requests or output mutation."""
    root = request.root.resolve()
    if len(request.expected_commit) != 40 or any(c not in '0123456789abcdef' for c in request.expected_commit):
        raise CaptureRefused('expected_commit must be a full immutable commit SHA')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
    if git('rev-parse', 'HEAD') != request.expected_commit:
        raise CaptureRefused('execution commit pin differs')
    if git('status', '--porcelain'):
        raise CaptureRefused('execution worktree is not clean')
    config_path = request.config_path.resolve()
    if not config_path.is_relative_to(root):
        raise CaptureRefused('configuration must be inside the pinned worktree')
    raw = config_path.read_bytes()
    if _sha(raw) != request.config_sha256:
        raise CaptureRefused('configuration SHA-256 differs')
    config = json.loads(raw)
    fingerprint = contract_fingerprint(root)
    if fingerprint['benchmark_contract_sha256'] != config['benchmark_contract_sha256']:
        raise CaptureRefused('benchmark contract fingerprint differs')
    source = ast.parse((root / 'src/evals/system_benchmark/local_worker.py').read_text())
    tool = next(ast.literal_eval(node.value) for node in source.body
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == '_QUERY_TOOL'
                                                       for target in node.targets))
    if _sha(_canonical(tool)) != config['query_tool_sha256']:
        raise CaptureRefused('query tool fingerprint differs')
    fixed_model = {
        'name': 'hermes-local:qwen3.5-9b', 'base_url': 'http://127.0.0.1:11434',
        'temperature': 0, 'num_predict': 512, 'num_ctx': 65536, 'timeout_seconds': 120,
        'digest': '0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c',
    }
    if (not config.get('configuration_id') or config['task_id'] != 'SB-D01'
            or set(config['allowed_tools']) != {'query_clickhouse', 'retrieve_policy'}
            or config['limits'] != {'model_steps': 6, 'evidence_calls': 2, 'retries': 0, 'reprompts': 0}
            or any(type(config['model'].get(key)) is not type(value) or config['model'][key] != value
                   for key, value in fixed_model.items())):
        raise CaptureRefused('configuration is outside the bounded Treatment A contract')
    return {'version': VERSION, 'execution_commit': request.expected_commit,
            'config_sha256': request.config_sha256, 'config': config,
            'benchmark_contract': fingerprint, 'collector_sha256': _sha(Path(__file__).read_bytes()),
            'runtime_validity_gate': config.get('runtime_offline_validity_gate', 'missing')}


def resource_snapshot() -> dict:
    """Sample this worker-host process and Ollama OS processes, without API calls."""
    pid = os.getpid()
    run = subprocess.run(['ps', '-axo', 'pid=,ppid=,%cpu=,rss=,comm='],
                         text=True, capture_output=True, timeout=5, check=True)
    rows = []
    for line in run.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) != 5:
            continue
        if int(fields[0]) == pid or 'ollama' in fields[4].lower():
            rows.append({'pid': int(fields[0]), 'ppid': int(fields[1]),
                         'cpu_percent_os_reported': float(fields[2]),
                         'rss_bytes': int(fields[3]) * 1024, 'command': fields[4]})
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {'worker_host_pid': pid, 'processes': rows,
            'process_cpu_user_seconds': usage.ru_utime,
            'process_cpu_system_seconds': usage.ru_stime,
            'process_lifetime_peak_rss_bytes': usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
            'limits': 'Before/after OS snapshots only; host process includes capture overhead. '
                      'Ollama is shared; these are not per-request CPU/GPU/VRAM or peak model-memory measurements.'}


class CaptureSession:
    def __init__(self, request: CaptureRequest, out: Path, checks: dict):
        self.request, self.out, self.checks = request, out, checks
        self.events = (out / 'events.jsonl').open('x')
        self.sequence = 0
        self.worker_entries = 0
        self.worker_active = False
        self.worker_error = None
        self.collector_errors = []
        self.metrics = {name: 0 for name in ('model_attempts', 'model_returns', 'model_returns_with_metrics',
                                            'input_tokens', 'output_tokens', 'tool_attempts', 'tool_returns')}
        self.metrics['model_duration_seconds_known'] = 0.0
        self.metrics['model_returns_with_duration'] = 0
        self.manifest = {'capture_version': VERSION, 'attempt_status': 'prepared',
                         'worker_invocations': 0, 'start_utc': self.utc(),
                         'approval_reference': request.approval_reference, 'preflight': checks,
                         'partial_metrics': self.metrics, 'collector_errors': self.collector_errors,
                         'metrics_boundary': 'Observed completed model returns only; missing/error-call usage is unknown.',
                         'invocation_boundary': 'Count durable wrapper-entry events; crash after reservation remains unresolved, never retried.'}
        self.write_manifest()

    @staticmethod
    def utc():
        return datetime.now(timezone.utc).isoformat()

    def event(self, name: str, **payload):
        result = payload.get('result')
        if (name in ('model_return', 'worker_return', 'runner_return')
                and isinstance(result, dict) and result.get('type') in ('final', 'tool_call')
                and isinstance(result.get('content'), str)):
            # A model envelope may also be forwarded as an executor/runner
            # return in adapters. Sanitize those trace copies consistently.
            public_result, metadata = _model_content_copy(result)
            payload = {**payload, 'result': public_result, **metadata}
        record = {'sequence': self.sequence, 'utc': self.utc(), 'monotonic_seconds': time.monotonic(),
                  'event': name, **_public(payload)}
        self.events.write(json.dumps(record, sort_keys=True, allow_nan=False) + '\n')
        self.events.flush()
        os.fsync(self.events.fileno())
        self.sequence += 1

    def safe_event(self, name: str, **payload):
        try:
            self.event(name, **payload)
        except BaseException as error:
            self.collector_errors.append({'stage': name, **_error(error)})

    def write_manifest(self):
        self.manifest['worker_invocations'] = self.worker_entries
        temporary = self.out / 'manifest.json.tmp'
        with temporary.open('w') as file:
            file.write(json.dumps(self.manifest, indent=2, sort_keys=True, allow_nan=False) + '\n')
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(self.out / 'manifest.json')

    def snapshot(self, stage: str, sampler: Callable):
        try:
            self.event('resource_snapshot', stage=stage, observation=sampler())
        except BaseException as error:
            self.collector_errors.append({'stage': f'resource_{stage}', **_error(error)})

    def wrap_executor(self, delegate: Callable) -> Callable:
        def invoke(*args, **kwargs):
            # Reservation is one-shot and is never cleared, even after errors.
            if self.worker_entries:
                raise FileExistsError('worker already entered; no retry is permitted')
            preflight(self.request)  # Recheck after adapter assembly, before reservation.
            self.manifest['attempt_status'] = 'started'
            self.write_manifest()  # Durable before any worker entry or model/tool call.
            with (self.out / 'INVOCATION_STARTED.json').open('x') as marker:
                json.dump({'capture_version': VERSION, 'utc': self.utc(),
                           'execution_commit': self.request.expected_commit,
                           'configuration_sha256': self.request.config_sha256,
                           'approval_reference': self.request.approval_reference}, marker, sort_keys=True)
                marker.flush()
                os.fsync(marker.fileno())
            self.event('worker_enter')
            self.worker_entries += 1
            self.write_manifest()
            started = time.monotonic()
            self.worker_active = True
            try:
                returned = delegate(*args, **kwargs)
            except BaseException as error:
                self.worker_error = error
                self.safe_event('worker_error', error=_error(error), wall_seconds=time.monotonic() - started)
                raise
            finally:
                self.worker_active = False
            self.safe_event('worker_return', result=returned, wall_seconds=time.monotonic() - started)
            return returned
        return invoke

    def wrap_tool(self, name: str, delegate: Callable) -> Callable:
        if name not in self.checks['config']['allowed_tools']:
            raise CaptureRefused('tool is not in the approved configuration')
        def invoke(*args, **kwargs):
            if not self.worker_active:
                raise CaptureRefused('tool call outside the recorded worker entry')
            self.event(f'{name}_start', input={'args': args, 'kwargs': kwargs})
            self.metrics['tool_attempts'] += 1
            try:
                returned = delegate(*args, **kwargs)
            except BaseException as error:
                self.safe_event(f'{name}_error', error=_error(error))
                raise
            self.metrics['tool_returns'] += 1
            self.safe_event(f'{name}_return', result=returned)
            return returned
        return invoke

    def wrap_model(self, delegate):
        expected = self.checks['config']['model']
        for attribute, value in [('model', expected['name']), ('base_url', expected['base_url']),
                                 ('timeout', expected['timeout_seconds'])]:
            if getattr(delegate, attribute, None) != value:
                raise CaptureRefused(f'model delegate {attribute} differs from configuration')
        session = self
        class ObservedModel:
            def respond(self, messages, tools):
                if not session.worker_active:
                    raise CaptureRefused('model call outside the recorded worker entry')
                if set(tool['name'] for tool in tools) != set(session.checks['config']['allowed_tools']):
                    raise CaptureRefused('model-facing tool names differ')
                query = next(tool for tool in tools if tool['name'] == 'query_clickhouse')
                if _sha(_canonical(query)) != session.checks['config']['query_tool_sha256']:
                    raise CaptureRefused('model-facing query tool fingerprint differs')
                session.event('model_start', input={'messages': messages, 'tools': tools})
                session.metrics['model_attempts'] += 1
                try:
                    returned = delegate.respond(messages, tools)
                except BaseException as error:
                    session.safe_event('model_error', error=_error(error))
                    raise
                session.metrics['model_returns'] += 1
                try:
                    public = {key: returned[key] for key in ('type', 'name', 'arguments', 'content', '_metrics') if key in returned}
                    metrics = public.get('_metrics') or {}
                    session.metrics['model_returns_with_metrics'] += bool(metrics)
                    for field in ('input_tokens', 'output_tokens'):
                        if type(metrics.get(field)) is int:
                            session.metrics[field] += metrics[field]
                    duration = metrics.get('total_duration_seconds')
                    if type(duration) in (int, float) and math.isfinite(duration):
                        session.metrics['model_duration_seconds_known'] += duration
                        session.metrics['model_returns_with_duration'] += 1
                    session.safe_event('model_return', result=public)
                except BaseException as error:
                    session.collector_errors.append({'stage': 'model_return', **_error(error)})
                return returned
        return ObservedModel()


def capture_once(request: CaptureRequest, out: Path, execute: Callable, *,
                 snapshot: Callable | None = None):
    """Run an injected orchestration callback; it must use wrap_executor once.

    Delegate objects/results/exceptions are forwarded unchanged. This boundary
    never supplies a live adapter, retries, infers missing scores or promotes a
    phase. Inspect the final manifest and collector_errors before qualification.
    """
    if request.run is not True or not request.approval_reference.strip():
        raise CaptureRefused('explicit run flag and approval reference are required')
    checks = preflight(request)
    if checks['runtime_validity_gate'] != 'passed':
        raise CaptureRefused('runtime offline validity gate is not passed')
    out = Path(out)
    if out.resolve().is_relative_to(request.root.resolve()):
        raise CaptureRefused('evidence folder must be outside the pinned source worktree')
    out.mkdir(parents=True, exist_ok=False)
    session = CaptureSession(request, out, checks)
    sampler = snapshot if snapshot is not None else resource_snapshot
    started = time.monotonic()
    try:
        session.snapshot('before', sampler)
        returned = execute(session)
        if session.worker_error is not None:
            raise session.worker_error
        if session.worker_entries != 1:
            raise CaptureRefused('callback did not enter exactly one worker')
        session.safe_event('runner_return', result=returned)
        session.manifest['attempt_status'] = 'completed'
        return returned
    except BaseException as error:
        session.manifest['attempt_status'] = 'execution_error' if session.worker_entries else 'pre_invocation_error'
        session.safe_event('capture_error', error=_error(error))
        raise
    finally:
        # Secondary observation/finalization failures must not replace a return
        # value or the original exception from the actual delegate.
        try:
            session.snapshot('after', sampler)
            try:
                postflight = preflight(request)
                session.manifest['postflight'] = {'valid': True, 'execution_commit': postflight['execution_commit'],
                                                  'config_sha256': postflight['config_sha256'],
                                                  'benchmark_contract_sha256': postflight['benchmark_contract']['benchmark_contract_sha256']}
            except BaseException as error:
                session.manifest['postflight'] = {'valid': False, 'error': _error(error)}
                session.collector_errors.append({'stage': 'postflight', **_error(error)})
            session.manifest.update(end_utc=session.utc(), capture_wall_seconds=time.monotonic() - started,
                                    collector_status='incomplete' if session.collector_errors else 'complete')
            session.write_manifest()
        except BaseException as error:
            session.collector_errors.append({'stage': 'finalization', **_error(error)})
        try:
            session.events.close()
        except BaseException:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--approval-reference', default='')
    args = parser.parse_args()
    if args.run:
        parser.error('live activation adapter is unavailable; owner scope approval and a reviewed adapter are required')
    request = CaptureRequest(args.root, args.expected_commit, args.config, args.config_sha256)
    print(json.dumps(preflight(request), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
