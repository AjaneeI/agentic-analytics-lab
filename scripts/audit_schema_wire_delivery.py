#!/usr/bin/env python3
"""Inspect real Ollama request serialization using a fake HTTP response only.

The audit never permits inference, evidence callbacks, DNS/network access or
private/held-out file reads during captures. Exit 2 means wire delivery passed
while runtime equivalence and architecture-comparison approval remain absent.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager, ExitStack
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
APPROVED_COMMIT = '644a68d75cf6743d3daaace51f42a0571747417c'
APPROVED_WORKER_SHA256 = 'b0e9c39dbcc868fd6a346778a2a9c6b3418aa828d7b57e8852026623a3b8f289'
APPROVED_CLIENT_SHA256 = 'ddffe7ffb31c9586077b1c2160d06da88e9ef2903aa84c8c32864413ee83ecd4'
DESTINATION = 'http://127.0.0.1:11434/api/chat'


class WireDeliveryMismatch(AssertionError):
    """A wire assertion or offline guard failed; no live fallback is permitted."""


def require(condition, message):
    if not condition:
        raise WireDeliveryMismatch(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest(value) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def _git_source(root: Path, relative: str) -> bytes:
    return subprocess.run(['git', 'show', f'{APPROVED_COMMIT}:{relative}'], cwd=root,
                          check=True, capture_output=True).stdout


def _request_constants(source: bytes) -> dict:
    """Read literal options directly from source AST, without client helpers."""
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                and any(isinstance(target, ast.Name) and target.id == 'payload' for target in node.targets)):
            values = {key.value: value for key, value in zip(node.value.keys, node.value.values)
                      if isinstance(key, ast.Constant)}
            if {'options', 'stream', 'keep_alive'} <= values.keys():
                return {key: ast.literal_eval(values[key]) for key in ('options', 'stream', 'keep_alive')}
    raise WireDeliveryMismatch('client source has no inspectable literal request constants')


def approved_contract(root: Path) -> dict:
    worker = _git_source(root, 'src/evals/system_benchmark/local_worker.py')
    client = _git_source(root, 'src/agents/ollama_client.py')
    require(sha(worker) == APPROVED_WORKER_SHA256, 'approved worker source digest differs')
    require(sha(client) == APPROVED_CLIENT_SHA256, 'approved client source digest differs')
    constants = {}
    for node in ast.parse(worker).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('_QUERY_TOOL', '_POLICY_TOOL', '_SYSTEM_PROMPT'):
                    value = node.value
                    if isinstance(value, ast.Call):
                        require(isinstance(value.func, ast.Attribute) and value.func.attr == 'strip'
                                and not value.args and not value.keywords, 'unexpected approved prompt AST')
                        constants[target.id] = ast.literal_eval(value.func.value).strip()
                    else:
                        constants[target.id] = ast.literal_eval(value)
    require(set(constants) == {'_QUERY_TOOL', '_POLICY_TOOL', '_SYSTEM_PROMPT'}, 'approved constants missing')
    return {'prompt': constants['_SYSTEM_PROMPT'],
            'tools': {constants[key]['name']: constants[key] for key in ('_QUERY_TOOL', '_POLICY_TOOL')},
            'qualification_request': _request_constants(client)}


@contextmanager
def offline_guards(root: Path, rejected: list):
    """Scoped socket/DNS denial plus Python-open guards for private/held-out files."""
    root = root.resolve()
    state = {'active': True}
    def deny(*_args, **_kwargs):
        rejected.append('forbidden_network_or_evidence_attempt')
        raise WireDeliveryMismatch('offline wire audit forbids network/evidence calls')
    def audit_open(event, arguments):
        if not state['active'] or event != 'open' or not arguments:
            return
        value = arguments[0]
        if not isinstance(value, (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(value)).resolve()
        if not path.is_relative_to(root):
            return
        parts = tuple(part.casefold() for part in path.relative_to(root).parts)
        if (any('heldout' in part or 'held-out' in part for part in parts)
                or any(part in ('private', 'secrets') or part == '.env' or part.startswith('.env.') for part in parts)):
            rejected.append('forbidden_private_or_heldout_file_open')
            raise WireDeliveryMismatch('offline wire audit forbids private/held-out source access')
    # Python audit hooks cannot be removed; this hook becomes inert on exit.
    sys.addaudithook(audit_open)
    try:
        with ExitStack() as stack:
            for name in ('connect', 'connect_ex', 'sendto', 'sendmsg'):
                if hasattr(socket.socket, name):
                    stack.enter_context(patch.object(socket.socket, name, deny))
            for name in ('create_connection', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr'):
                stack.enter_context(patch.object(socket, name, deny))
            stack.enter_context(patch('urllib.request.urlopen', deny))
            yield deny
    finally:
        state['active'] = False


def audit(root: Path = ROOT, *, model_id: str = 'offline-wire-delivery-probe') -> dict:
    root = Path(root).resolve()
    require(isinstance(model_id, str) and bool(model_id.strip()), 'supplied model ID must be nonempty')
    # A different checkout must run in a fresh interpreter; do not reuse cached
    # classes from the development checkout when auditing activation source.
    for name, module in tuple(sys.modules.items()):
        if name == 'src' or name.startswith('src.'):
            filename = getattr(module, '__file__', None)
            require(not filename or Path(filename).resolve().is_relative_to(root),
                    'use a separate process for a different repository root')
    approved = approved_contract(root)
    client_path = root / 'src/agents/ollama_client.py'
    expected_request = _request_constants(client_path.read_bytes())
    source_paths = [
        'src/agents/ollama_client.py', 'src/evals/system_benchmark/local_worker.py',
        'src/evals/system_benchmark/contracts.py', 'src/evals/system_benchmark/loader.py',
        'src/evals/system_benchmark/routing.py', 'src/evals/system_benchmark/workers.py',
        'evals/system_benchmark/development_tasks.json',
    ]
    has_strong = (root / 'src/evals/system_benchmark/baselines.py').is_file()
    if has_strong:
        source_paths.append('src/evals/system_benchmark/baselines.py')
    before = {relative: sha((root / relative).read_bytes()) for relative in source_paths}
    records, rejected = [], []
    canaries = ('WIRE_HIDDEN_CASE_CANARY', 'WIRE_HIDDEN_REFERENCE_CANARY', 'WIRE_HIDDEN_TRUTH_CANARY')
    private_response_canary = 'WIRE_PRIVATE_RESPONSE_THINKING_CANARY'
    sys.path.insert(0, str(root))
    with offline_guards(root, rejected) as deny:
        from src.agents.ollama_client import OllamaModelClient
        from src.evals.system_benchmark.contracts import StructuredExpectation
        from src.evals.system_benchmark.loader import load_tasks
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
        from src.evals.system_benchmark.routing import natural_language_route, oracle_route, simple_heuristic_route
        if has_strong:
            from src.evals.system_benchmark.baselines import StrongSingleExecutor

        tasks = {task.case_id: task for task in load_tasks(root / 'evals/system_benchmark/development_tasks.json')}
        probes = (
            ('structured', tasks['SB-A01']), ('documents', tasks['SB-C01']),
            ('multi_source', replace(tasks['SB-D01'], request='Compare team blocker rates in the dataset and interpret them using the policy dictionary.')),
            ('none', replace(tasks['SB-E01'], request='Use private Slack messages to explain a delivery delay.')),
        )
        lanes = {'strong_single': None} if has_strong else {}
        lanes.update(oracle_routed=oracle_route,
                     natural_language_routed=lambda task: natural_language_route(task.request),
                     simple_heuristic_routed=lambda task: simple_heuristic_route(task.request))
        profile_tools = {'structured': ['query_clickhouse'], 'documents': ['retrieve_policy'],
                         'multi_source': ['query_clickhouse', 'retrieve_policy'], 'none': []}
        for lane, route in lanes.items():
            for profile, original in probes:
                task = replace(original, case_id=canaries[0], reference_solution_id=canaries[1],
                               expected_values=(StructuredExpectation('wire_canary', canaries[2]),))
                names = ['query_clickhouse', 'retrieve_policy'] if lane == 'strong_single' else profile_tools[profile]
                # Construct the expected wire schema from approved AST constants,
                # never OllamaModelClient._convert_tools or a proposal snapshot.
                expected_tools = [{'type': 'function', 'function': {
                    'name': approved['tools'][name]['name'],
                    'description': approved['tools'][name]['description'],
                    'parameters': approved['tools'][name]['input_schema'],
                }} for name in names]
                expected_messages = [{'role': 'system', 'content': approved['prompt']},
                                     {'role': 'user', 'content': task.request}]
                captured = []
                def fake_http(request, *, timeout):
                    require(request.full_url == DESTINATION, f'{lane}/{profile}: wire destination differs')
                    require(request.get_method() == 'POST', f'{lane}/{profile}: wire method differs')
                    require(request.get_header('Content-type') == 'application/json', 'wire content type differs')
                    require(timeout == 120, 'wire timeout differs')
                    require(isinstance(request.data, bytes), 'real request data must be bytes')
                    raw = request.data
                    payload = json.loads(raw)
                    require(payload.get('model') == model_id, f'{lane}/{profile}: supplied model ID differs')
                    require(payload.get('tools') == expected_tools, f'{lane}/{profile}: wire tools differ')
                    require(payload.get('messages') == expected_messages, f'{lane}/{profile}: wire messages differ')
                    require(all(payload.get(key) == value for key, value in expected_request.items()),
                            f'{lane}/{profile}: wire request constants differ from client source')
                    require(all(canary.encode() not in raw for canary in canaries), 'hidden metadata leaked into wire bytes')
                    captured.append({'url': request.full_url, 'method': request.get_method(), 'timeout_seconds': timeout,
                                     'request_data_utf8': raw.decode(), 'request_data_sha256': sha(raw)})
                    response = {'message': {'content': json.dumps({'disposition': 'answer',
                                'answer_text': 'Offline wire delivery fixture only.'}),
                                'thinking': private_response_canary},
                                'prompt_eval_count': 0, 'eval_count': 0, 'total_duration': 0}
                    return io.BytesIO(json.dumps(response).encode())
                model = OllamaModelClient(model=model_id, base_url='http://127.0.0.1:11434', timeout=120)
                kwargs = {'model': model, 'query_fn': deny, 'policy_fn': deny}
                executor = (StrongSingleExecutor(model_id=model_id, **kwargs) if lane == 'strong_single'
                            else BoundedLocalExecutor(route_fn=route, **kwargs))
                with patch('urllib.request.urlopen', fake_http):
                    execution = executor(task, 1, None)
                require(len(captured) == 1 and execution.model_calls == 1, 'expected one fake-transport client request')
                require(execution.observation.tool_calls == (), 'unexpected evidence tool call')
                records.append({'lane': lane, 'probe_capability': profile, 'expected_tool_names': names,
                                **captured[0], 'wire_tool_schema_and_descriptions_match': True,
                                'wire_messages_match': True, 'hidden_metadata_canaries_absent': True,
                                'evidence_tool_calls': 0, 'fake_http_responses': 1})
    require(not rejected, 'an offline guard rejected an unexpected attempt')
    require(private_response_canary not in json.dumps(records), 'private response field was recorded')
    after = {relative: sha((root / relative).read_bytes()) for relative in source_paths}
    require(before == after, 'runtime source/task bytes changed during audit')
    return {
        'status': 'offline_wire_delivery_verified_not_runtime_equivalence',
        'wire_schema_delivery_verified': True, 'capture_count': len(records), 'captures': records,
        'supplied_probe_model_id': model_id, 'actual_client_source_request': expected_request,
        'phase2_qualification_source_request': approved['qualification_request'],
        'wire_options_equal_phase2_qualification_source': expected_request['options'] == approved['qualification_request']['options'],
        'runtime_equivalence_verified': False, 'same_model_runtime_configuration_as_phase2_qualification': False,
        'comparative_evaluation_approved': False, 'phase2_qualified': False, 'phase5_entry_accepted': False,
        'live_model_calls': 0, 'external_database_calls': 0, 'heldout_access': False,
        'approved_source': {'commit': APPROVED_COMMIT, 'extraction': 'independent AST from git show, no proposal JSON fallback',
                            'worker_sha256': APPROVED_WORKER_SHA256, 'client_sha256': APPROVED_CLIENT_SHA256},
        'runtime_source_sha256': before, 'auditor_sha256': sha(Path(__file__).read_bytes()),
        'guards': {'real_client_respond_and_request_serialization': True, 'HTTP_transport': 'fake response only',
                   'socket_and_DNS_denied': True, 'evidence_callbacks_denied': True,
                   'private_and_heldout_Python_file_opens_denied_during_captures': True,
                   'private_response_thinking_field_not_recorded': True},
        'rejected_attempts': rejected,
        'unverified_lanes': ['Hermes delegated Treatment B', 'architectures not explicitly captured'],
        'limitations': [
            'Wire schema delivery only; no inference, live model digest, model quality, runtime or architecture equivalence evidence.',
            'The explicit probe model ID tests forwarding and does not qualify any model or provider.',
            f'Audited client options are {expected_request["options"]}; Phase 2 qualification source options are {approved["qualification_request"]["options"]}. Matching wire options alone would not establish runtime equivalence.',
            'A different repository root must be audited in a separate interpreter; strong-single is omitted when its adapter is absent.',
            'Private-field guards and synthetic canaries are bounded checks, not complete semantic privacy redaction.',
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--model-id', default='offline-wire-delivery-probe')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        print('Refusing to overwrite an existing wire artifact', file=sys.stderr)
        return 1
    report = audit(args.repository, model_id=args.model_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'], 'capture_count': report['capture_count'],
                      'wire_options_equal_phase2_qualification_source': report['wire_options_equal_phase2_qualification_source']}))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
