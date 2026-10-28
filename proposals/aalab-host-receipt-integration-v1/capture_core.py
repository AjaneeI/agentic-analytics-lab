"""H1 inactive synthetic-only derivative; origin SHA28859a2b. See README diff map.
No historical preflight/CLI/run flag, capture_once or resource sampler exists.
"""
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Callable
VERSION = 'H1-synthetic-capture-core-v1'
FLAGS = {'synthetic': True, 'inactive': True, 'live_qualified': False, 'live_authentication': False, 'independence_established': False, 'scientific_ready': False, 'new_attempts': 0}
PRIVATE_FIELDS = {'thinking', 'reasoning', 'reasoning_content', 'chain_of_thought', 'analysis'}
@dataclass(frozen=True)
class SyntheticRequest:
    expected_commit: str
    config_sha256: str
    approval_reference: str = 'H1-inactive-scripted-authorization'

class CaptureRefused(RuntimeError):
    """No authorized worker invocation was made by this refusal."""

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

class CaptureSession:
    def __init__(self, request: SyntheticRequest, out: Path, checks: dict, *, synthetic_preflight, write_bounded):
        self.request, self.out, self.checks = request, out, checks
        self._preflight = synthetic_preflight
        self._write_bounded = write_bounded
        self.collector_errors = []
        self.event_path = out / 'events.jsonl'
        self._write_required(self.event_path, b'')
        self.manifest_files = []
        self.manifest_sequence = 0
        self.sequence = 0
        self.worker_entries = 0
        self.worker_active = False
        self.worker_error = None
        self.worker_returned = False
        self.worker_delegate_entered = False
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
        self.manifest.update(FLAGS)
        self.write_manifest()

    def _write_required(self, path, data, *, append=False):
        try:
            return self._write_bounded(path, data, append=append)
        except BaseException as error:
            self.collector_errors.append({'stage': 'required_record:' + path.name, **_error(error)})
            raise

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
                  'event': name, **_public(payload), **FLAGS}
        self._write_required(self.event_path, (json.dumps(record, sort_keys=True, allow_nan=False) + '\n').encode(), append=True)
        self.sequence += 1

    def safe_event(self, name: str, **payload):
        try:
            self.event(name, **payload)
        except BaseException as error:
            self.collector_errors.append({'stage': name, **_error(error)})

    def write_manifest(self):
        self.manifest['worker_invocations'] = self.worker_entries
        target = self.out / ('manifest-%03d.json' % self.manifest_sequence)
        self.manifest_sequence += 1  # A failed record identity is never reused.
        self._write_required(target, _canonical(self.manifest))
        self.manifest_files.append(target)

    def wrap_executor(self, delegate: Callable) -> Callable:
        def invoke(*args, **kwargs):
            # Reservation is one-shot and is never cleared, even after errors.
            if self.worker_entries:
                raise FileExistsError('worker already entered; no retry is permitted')
            try:
                self._preflight()  # Trusted synthetic check, never historical preflight.
            except BaseException as error:
                self.collector_errors.append({'stage': 'synthetic_preflight', **_error(error)})
                raise
            self.manifest['attempt_status'] = 'started'
            self.write_manifest()  # Durable before any worker entry or model/tool call.
            self._write_required(self.out / 'INVOCATION_STARTED.json', _canonical({
                'capture_version': VERSION, 'utc': self.utc(),
                'execution_commit': self.request.expected_commit,
                'configuration_sha256': self.request.config_sha256,
                'approval_reference': self.request.approval_reference, **FLAGS}))
            self.event('worker_enter')
            self.worker_entries += 1
            self.write_manifest()
            started = time.monotonic()
            self.worker_active = True
            try:
                self.worker_delegate_entered = True
                returned = delegate(*args, **kwargs)
            except BaseException as error:
                self.worker_error = error
                self.safe_event('worker_error', error=_error(error), wall_seconds=time.monotonic() - started)
                raise
            finally:
                self.worker_active = False
            self.worker_returned = True
            self.safe_event('worker_return', result=returned, wall_seconds=time.monotonic() - started)
            return returned
        return invoke

    def wrap_tool(self, name: str, delegate: Callable) -> Callable:
        if name not in self.checks['config']['allowed_tools']:
            raise CaptureRefused('tool is not in the approved configuration')
        def invoke(*args, **kwargs):
            if not self.worker_active:
                raise CaptureRefused('tool call outside the recorded worker entry')
            if self.metrics['tool_attempts'] >= 1:
                raise CaptureRefused('H1 one-callback bound')
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
                if session.metrics['model_attempts'] >= 2:
                    raise CaptureRefused('H1 two-scripted-return bound')
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
