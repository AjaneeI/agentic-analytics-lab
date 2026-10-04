"""Model-free execution records and an enforced, bounded evidence gateway.

The adapter/backend are trusted Python components, not an OS security sandbox.
Worker declarations and captured backend evidence are deliberately separate.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import date
import hashlib
import json
import math
import re
from typing import Any, Protocol

from .contracts import (
    BenchmarkSplit, REQUIRED_HANDOFF_FIELDS, ResponseDisposition,
    SystemBenchmarkResponse, SystemBenchmarkTask,
)
from .references import parse_reference_expectation, ReferenceExpectation, validate_task_reference
from .scoring import ScoringObservation, score_response

_AGGREGATE = (
    'SELECT team, SUM(blocked) AS blocked_count, COUNT(*) AS item_count, '
    '100.0 * SUM(blocked) / COUNT(*) AS blocked_pct '
    'FROM agentic_analytics.delivery_work_items'
)
_ORDER = ' GROUP BY team ORDER BY blocked_pct DESC, team ASC LIMIT 1'
ALL_ITEMS_SQL = _AGGREGATE + _ORDER
ACTIVE_ITEMS_SQL = _AGGREGATE + " WHERE status != 'done'" + _ORDER
REPLAY_QUERIES = {ALL_ITEMS_SQL: 'all_work_items', ACTIVE_ITEMS_SQL: 'active_work_items'}
MAX_CALLS = 8
MAX_ARGUMENT_BYTES = 10000
MAX_RESULT_BYTES = 32000
_CAPABILITIES = {
    'none': frozenset(), 'structured': frozenset({'query_clickhouse'}),
    'documents': frozenset({'retrieve_policy'}),
    'multi_source': frozenset({'query_clickhouse', 'retrieve_policy'}),
}


def canonical_json(value: Any) -> str:
    """Stable UTF-8 JSON text with no non-finite numbers or volatile metadata."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n'


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _strings(value: Any, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)) or len(value) > 40:
        raise ValueError('expected a bounded string list')
    if any(not isinstance(x, str) or not x.strip() or len(x) > 2000 for x in value):
        raise ValueError('expected non-empty bounded strings')
    if len(set(value)) != len(value) or (nonempty and not value):
        raise ValueError('expected unique non-empty list')
    return list(value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 8000


def _values(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > 40:
        raise ValueError('answer values must be a bounded object')
    if any(not _text(k) or not isinstance(v, (str, int, float, bool, type(None))) for k, v in value.items()):
        raise ValueError('answer values must contain named JSON scalars')
    text = canonical_json(dict(value))
    if len(text.encode('utf-8')) > MAX_ARGUMENT_BYTES:
        raise ValueError('answer values exceed size bound')
    return json.loads(text)


def _response_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {'disposition', 'answer_text', 'evidence_refs', 'uncertainty', 'clarification', 'handoff'}
    if not isinstance(payload, Mapping) or set(payload) - fields:
        raise ValueError('unknown response fields')
    if not _text(payload.get('answer_text')):
        raise ValueError('answer_text must be non-empty bounded text')
    try:
        kind = ResponseDisposition(payload.get('disposition'))
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid disposition') from exc
    result = {key: payload.get(key) for key in fields}
    result['disposition'] = kind.value
    result['evidence_refs'] = _strings(payload.get('evidence_refs', ()))
    if result['uncertainty'] is not None and not _text(result['uncertainty']):
        raise ValueError('uncertainty must be text or null')
    clarification = result['clarification']
    if kind is ResponseDisposition.CLARIFY:
        if not isinstance(clarification, Mapping) or set(clarification) - {'concept', 'question'}:
            raise ValueError('invalid clarification object')
        if not _text(clarification.get('concept')):
            raise ValueError('missing clarification concept')
        if 'question' in clarification and not _text(clarification['question']):
            raise ValueError('invalid clarification question')
    elif clarification is not None:
        raise ValueError('clarification payload on a different disposition')
    handoff = result['handoff']
    if kind is ResponseDisposition.HANDOFF:
        if not isinstance(handoff, Mapping) or set(handoff) != set(REQUIRED_HANDOFF_FIELDS):
            raise ValueError('invalid handoff fields')
        handoff = dict(handoff)
        for key in ('trigger', 'unresolved_uncertainty', 'requested_authority'):
            if not _text(handoff[key]):
                raise ValueError('empty handoff field')
        for key in ('evidence_refs', 'actions_taken'):
            handoff[key] = _strings(handoff[key], nonempty=True)
        result['handoff'] = handoff
    elif handoff is not None:
        raise ValueError('handoff payload on a different disposition')
    return json.loads(canonical_json(result))


def response_from_dict(payload: Mapping[str, Any]) -> SystemBenchmarkResponse:
    """Validate the public envelope; reject hidden reasoning and unknown fields."""
    normalized = _response_payload(payload)
    normalized['disposition'] = ResponseDisposition(normalized['disposition'])
    normalized['evidence_refs'] = tuple(normalized['evidence_refs'])
    return SystemBenchmarkResponse(**normalized)


def response_to_dict(response: SystemBenchmarkResponse) -> dict[str, Any]:
    if not isinstance(response, SystemBenchmarkResponse) or not isinstance(response.disposition, ResponseDisposition):
        raise ValueError('response must use the typed envelope')
    return _response_payload(asdict(response))


@dataclass(frozen=True)
class PublicTask:
    case_id: str
    request: str
    allowed_tools: tuple[str, ...]


@dataclass(frozen=True)
class WorkerOutput:
    response: SystemBenchmarkResponse
    answer_values: Mapping[str, Any] = field(default_factory=dict)
    route: str = 'deterministic'


class Backend(Protocol):
    def execute(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]: ...


class ToolFailure(ValueError):
    """Stable reason code only; exception messages must not leak backend secrets."""


@dataclass(frozen=True)
class ToolEvent:
    sequence: int
    name: str
    arguments_json: str
    status: str
    reason_code: str | None
    result_json: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            'sequence': self.sequence, 'name': self.name,
            'arguments': json.loads(self.arguments_json), 'status': self.status,
            'reason_code': self.reason_code,
            'result': None if self.result_json is None else json.loads(self.result_json),
            'result_sha256': None if self.result_json is None else _digest(self.result_json),
        }


def _validate_arguments(name: str, arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, Mapping):
        raise ToolFailure('invalid_tool_arguments')
    try:
        encoded = canonical_json(dict(arguments))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ToolFailure('invalid_tool_arguments') from exc
    if len(encoded.encode('utf-8')) > MAX_ARGUMENT_BYTES:
        raise ToolFailure('tool_arguments_too_large')
    args = json.loads(encoded)
    if name == 'query_clickhouse':
        if set(args) != {'sql'} or not _text(args['sql']):
            raise ToolFailure('invalid_tool_arguments')
        from src.tools.clickhouse_readonly import QueryRejected, validate_read_only
        try:
            sql = validate_read_only(args['sql'])
        except QueryRejected as exc:
            raise ToolFailure('sql_rejected') from exc
        if sql not in REPLAY_QUERIES:
            raise ToolFailure('query_not_in_replay_allowlist')
        return {'sql': sql}
    if set(args) - {'query', 'top_k', 'as_of'} or not _text(args.get('query')):
        raise ToolFailure('invalid_tool_arguments')
    top_k = args.get('top_k', 3)
    if type(top_k) is not int or not 1 <= top_k <= 5:
        raise ToolFailure('invalid_tool_arguments')
    cutoff = args.get('as_of')
    if cutoff is not None:
        if not isinstance(cutoff, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', cutoff) is None:
            raise ToolFailure('invalid_tool_arguments')
        try:
            date.fromisoformat(cutoff)
        except ValueError as exc:
            raise ToolFailure('invalid_tool_arguments') from exc
    return {'query': args['query'], 'top_k': top_k, 'as_of': cutoff}


def _validate_result(result: Any, tool_name: str) -> str:
    if not isinstance(result, Mapping) or set(result) != {'backend', 'evidence'} or not _text(result['backend']):
        raise ToolFailure('invalid_tool_result')
    evidence = result['evidence']
    if not isinstance(evidence, list) or len(evidence) > 10:
        raise ToolFailure('invalid_tool_result')
    for item in evidence:
        common_fields = {'ref', 'source_type', 'source_id', 'values'}
        policy_fields = {'document_version', 'section_id', 'excerpt', 'effective_date', 'status'}
        expected_type = 'structured' if tool_name == 'query_clickhouse' else 'policy'
        required_fields = common_fields | (policy_fields if expected_type == 'policy' else set())
        if (not isinstance(item, Mapping) or set(item) != required_fields
                or item.get('source_type') != expected_type):
            raise ToolFailure('invalid_tool_result')
        if not _text(item['ref']) or not _text(item['source_id']):
            raise ToolFailure('invalid_tool_result')
        _values(item['values'])
        if item['source_type'] == 'structured':
            if item['ref'] != 'structured:' + item['source_id']:
                raise ToolFailure('invalid_tool_result')
        elif item['source_type'] == 'policy':
            expected = f"policy:{item['source_id']}@{item.get('document_version')}#{item.get('section_id')}"
            if item['ref'] != expected or not _text(item.get('excerpt')):
                raise ToolFailure('invalid_tool_result')
        else:
            raise ToolFailure('invalid_tool_result')
    encoded = canonical_json(result)
    if len(encoded.encode('utf-8')) > MAX_RESULT_BYTES:
        raise ToolFailure('tool_result_too_large')
    return encoded


class ToolGateway:
    """Deny before dispatch and keep immutable snapshots of successful returns."""
    def __init__(self, task: SystemBenchmarkTask, backend: Backend, *, max_calls: int = MAX_CALLS):
        if type(max_calls) is not int or not 1 <= max_calls <= MAX_CALLS:
            raise ValueError('max_calls must be an integer from 1 to 8')
        self._task = task
        self._backend = backend
        self._max_calls = max_calls
        self._events: list[ToolEvent] = []

    @property
    def events(self) -> tuple[ToolEvent, ...]:
        return tuple(self._events)

    def call(self, name: str, arguments: Any) -> dict[str, Any]:
        args_json = canonical_json({'rejected_arguments': True})
        safe_name = name if isinstance(name, str) and len(name) <= 100 else '<invalid>'
        try:
            if len(self._events) >= self._max_calls:
                raise ToolFailure('tool_budget_exceeded')
            if safe_name in self._task.forbidden_tools:
                raise ToolFailure('forbidden_tool')
            if safe_name not in self._task.allowed_tools or safe_name not in {'query_clickhouse', 'retrieve_policy'}:
                raise ToolFailure('unexpected_tool')
            if safe_name not in _CAPABILITIES[self._task.expected_capability_profile.value]:
                raise ToolFailure('capability_denied')
            args = _validate_arguments(safe_name, arguments)
            args_json = canonical_json(args)
        except ToolFailure as exc:
            if len(self._events) <= self._max_calls:
                self._events.append(ToolEvent(len(self._events)+1, safe_name, args_json, 'rejected', str(exc), None))
            raise
        try:
            returned = self._backend.execute(safe_name, json.loads(args_json))
        except Exception:
            self._events.append(ToolEvent(len(self._events)+1, safe_name, args_json, 'failed', 'tool_execution_failed', None))
            raise ToolFailure('tool_execution_failed') from None
        try:
            result_json = _validate_result(returned, safe_name)
        except (TypeError, ValueError, OverflowError) as exc:
            reason = str(exc) if isinstance(exc, ToolFailure) else 'invalid_tool_result'
            self._events.append(ToolEvent(len(self._events)+1, safe_name, args_json, 'failed', reason, None))
            raise ToolFailure(reason) from None
        self._events.append(ToolEvent(len(self._events)+1, safe_name, args_json, 'succeeded', None, result_json))
        return json.loads(result_json)


@dataclass(frozen=True)
class ExecutionRecord:
    passed: bool
    reason_codes: tuple[str, ...]
    _payload_json: str

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._payload_json)

    def to_json(self) -> str:
        return self._payload_json


def _same_value(observed: Any, claimed: Any, tolerance: float = 0.0) -> bool:
    if isinstance(observed, bool) or isinstance(claimed, bool):
        return type(observed) is type(claimed) and observed == claimed
    if isinstance(observed, (int, float)) and isinstance(claimed, (int, float)):
        try:
            return math.isclose(float(observed), float(claimed), rel_tol=0.0, abs_tol=tolerance)
        except OverflowError:
            return False
    if isinstance(observed, str) and isinstance(claimed, str):
        return observed.casefold() == claimed.casefold()
    return type(observed) is type(claimed) and observed == claimed


def _grounding(task: SystemBenchmarkTask, response: dict[str, Any], values: dict[str, Any], events: tuple[ToolEvent, ...]) -> tuple[str, ...]:
    evidence = [item for event in events if event.status == 'succeeded'
                for item in json.loads(event.result_json)['evidence']]
    produced = {item['ref'] for item in evidence}
    cited = set(response['evidence_refs'])
    handoff_cited = set(response['handoff']['evidence_refs']) if response['handoff'] else set()
    reasons = []
    if (cited | handoff_cited) - produced:
        reasons.append('unobserved_evidence_ref')
    if handoff_cited - cited:
        reasons.append('handoff_evidence_not_in_response')
    rows = [item['values'] for item in evidence if item['source_type'] == 'structured' and item['ref'] in cited]
    tolerances = {v.name: v.tolerance or 0.0 for v in task.expected_values}
    if values and not any(all(k in row and _same_value(row[k], v, tolerances.get(k, 0.0))
                              for k, v in values.items()) for row in rows):
        reasons.append('ungrounded_answer_values')
    scope = next((v.value for v in task.expected_values if v.name == 'scope'), None)
    if scope is not None and (values.get('scope') != scope or not any(row.get('scope') == scope for row in rows)):
        reasons.append('scope_mismatch')
    return tuple(reasons)


def validate_execution_pair(task: SystemBenchmarkTask, reference: ReferenceExpectation) -> ReferenceExpectation:
    """Fail preflight before any backend is constructed or called."""
    if task.split is not BenchmarkSplit.DEVELOPMENT:
        raise ValueError('dry-run execution accepts development tasks only')
    reference = parse_reference_expectation(json.loads(canonical_json(asdict(reference))))
    validate_task_reference(task, reference)
    canonical_json(asdict(task))
    names = [expected.name for expected in task.expected_values]
    if len(set(names)) != len(names):
        raise ValueError('duplicate expected value name')
    for expected in task.expected_values:
        _values({expected.name: expected.value})
    return reference


def execute_task(task: SystemBenchmarkTask, reference: ReferenceExpectation,
                 adapter: Callable[[PublicTask, ToolGateway], WorkerOutput], backend: Backend) -> ExecutionRecord:
    """Execute one development script; the scorer never supplies worker evidence."""
    reference = validate_execution_pair(task, reference)
    gateway = ToolGateway(task, backend)
    public = PublicTask(task.case_id, task.request, task.allowed_tools)
    response = None
    answer_values: dict[str, Any] = {}
    route = None
    runtime_reasons: list[str] = []
    try:
        output = adapter(public, gateway)
    except ToolFailure:
        output = None  # The gateway already preserved the exact stable reason.
    except Exception:
        output = None
        runtime_reasons.append('adapter_failed')
    if output is not None:
        try:
            if not isinstance(output, WorkerOutput) or output.route not in {'deterministic', 'local', 'escalate'}:
                raise ValueError('invalid worker output')
            response = response_to_dict(output.response)
            answer_values = _values(output.answer_values)
            route = output.route
        except (TypeError, ValueError, OverflowError):
            response = None
            answer_values = {}
            runtime_reasons.append('invalid_response')
    elif not runtime_reasons and not any(event.reason_code for event in gateway.events):
        runtime_reasons.append('invalid_response')
    event_reasons = [event.reason_code for event in gateway.events if event.reason_code]
    runtime_reasons = event_reasons + runtime_reasons
    grounded = ()
    score = None
    if response is not None:
        grounded = _grounding(task, response, answer_values, gateway.events)
        observation = ScoringObservation(
            tuple(event.name for event in gateway.events if event.status == 'succeeded'), answer_values,
        )
        score = score_response(task, reference, response_from_dict(response), observation).to_dict()
    reasons = tuple(dict.fromkeys(runtime_reasons + list(grounded) + ([] if score is None else score['reason_codes'])))
    passed = not reasons and score is not None and score['passed']
    if any(event.status == 'rejected' for event in gateway.events):
        stage = 'tool_validation'
    elif any(event.status == 'failed' for event in gateway.events):
        stage = 'tool_execution'
    elif runtime_reasons:
        stage = 'response_validation'
    elif grounded:
        stage = 'evidence_grounding'
    else:
        stage = 'none' if passed else 'scoring'
    payload = {
        'schema_version': 'system-benchmark-execution-v1', 'mode': 'scripted_development_dry_run',
        'case_id': task.case_id, 'split': 'development',
        'route': route, 'route_source': 'scripted_plan',
        'response': response, 'answer_values': answer_values,
        'trace': [event.to_dict() for event in gateway.events], 'score': score,
        'execution_checks': {'passed': not runtime_reasons, 'reason_codes': runtime_reasons},
        'grounding_checks': {'passed': not grounded and response is not None, 'reason_codes': list(grounded)},
        'passed': passed, 'reason_codes': list(reasons), 'primary_failure_stage': stage,
    }
    return ExecutionRecord(passed, reasons, canonical_json(payload))
