#!/usr/bin/env python3
"""Read-only offline independent checks; never authorize or enter a live worker."""
import argparse
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repository', type=Path, required=True)
p.add_argument('--expected-head', required=True)
a = p.parse_args()
root = a.repository.resolve()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
assert git('rev-parse', 'HEAD') == a.expected_head
assert not git('status', '--porcelain')
sys.path.insert(0, str(root))
from scripts import qualify_phase2_once as runner
from scripts import passive_capture as capture
assert not any(name.startswith('src.') for name in sys.modules)
config = root / 'configurations/phase2-runtime-schema-v1-scope-observation-v1.proposal.json'
request = capture.CaptureRequest(root, a.expected_head, config, sha(config.read_bytes()), True,
    'independent offline refusal probe only; no live authorization')
def denied(*_args, **_kwargs):
    raise AssertionError('Independent review forbids constructors/services/network/worker entry')
probes = {name: Mock(side_effect=denied) for name in ('model_factory','query_fn','policy_fn','service_json_get','service_query_fn','os_snapshot')}
with tempfile.TemporaryDirectory() as temp:
    out = Path(temp) / 'must-not-exist'
    with patch.object(socket.socket, 'connect', denied), patch.object(socket.socket, 'connect_ex', denied), \
         patch('socket.create_connection', denied), patch('urllib.request.urlopen', denied), \
         patch.object(runner, '_task_boundary', side_effect=denied):
        inspected = runner.source_preflight(request)
        try:
            runner.qualify_once(request, out, **probes)
        except capture.CaptureRefused as error:
            refusal = str(error)
        else:
            raise AssertionError('actual pending configuration unexpectedly permitted entry')
        assert inspected['execution_blockers'] == ['owner_observation_approval_not_approved', 'runtime_offline_validity_gate_not_passed']
        assert not out.exists()
        for probe in probes.values():
            probe.assert_not_called()
        arguments = ['qualify_phase2_once.py','--root',str(root),'--expected-commit',a.expected_head,
                     '--config',str(config),'--config-sha256',request.config_sha256]
        stdout = io.StringIO()
        with patch.object(sys, 'argv', arguments), redirect_stdout(stdout):
            assert runner.main() == 2
        assert json.loads(stdout.getvalue())['services_contacted'] is False
        assert not out.exists()
assert not any(name.startswith('src.') for name in sys.modules)
frozen = [
 'evals/questions.json','evals/system_benchmark/development_tasks.json','evals/system_benchmark/development_references.json',
 'scripts/generate_delivery_data.py','src/evals/system_benchmark/contracts.py','src/evals/system_benchmark/freeze_audit.py',
 'src/evals/system_benchmark/loader.py','src/evals/system_benchmark/references.py','src/evals/system_benchmark/scoring.py',
 'src/evals/trajectory_quality.py',
]
frozen += sorted(str(path.relative_to(root)) for path in (root/'evals/system_benchmark/corpus').iterdir() if path.is_file())
assert len(frozen) == 18
frozen_hashes = {}
for name in frozen:
    original = subprocess.check_output(['git','show','58add5e:'+name],cwd=root)
    current = (root/name).read_bytes()
    assert original == current, name
    frozen_hashes[name] = sha(current)
runner_original = subprocess.check_output(['git','show','58add5e:src/evals/system_benchmark/runner.py'],cwd=root)
assert runner_original == (root/'src/evals/system_benchmark/runner.py').read_bytes()
security_names = ['validate_read_only','_validate_table_scope','_validate_metric_semantics','_validate_clickhouse_url','_strip_comments','_normalize_identifier','_expression_before_alias']
original_tool = ast.parse(subprocess.check_output(['git','show','58add5e:src/tools/clickhouse_readonly.py'],cwd=root).decode())
current_tool = ast.parse((root/'src/tools/clickhouse_readonly.py').read_text())
def functions(tree):
    return {node.name:ast.dump(node,include_attributes=False) for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
old, new = functions(original_tool), functions(current_tool)
for name in security_names:
    assert old[name] == new[name], name
wire = []
class FakeResponse(io.StringIO):
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
def fake_urlopen(request, timeout):
    wire.append({'url':request.full_url,'method':request.method,'timeout':timeout,'payload':json.loads(request.data)})
    return FakeResponse(json.dumps({'message':{'content':'offline client wire capture'}}))
config_value = json.loads(config.read_text())
with patch.object(socket.socket,'connect',denied), patch('socket.create_connection',denied), patch('urllib.request.urlopen',fake_urlopen):
    client = runner._model_factory(config_value)
    assert type(client).__name__ == 'OllamaModelClient'
    client.respond([{'role':'user','content':'offline wire capture'}],[])
assert len(wire) == 1
assert wire[0] == {'url':'http://127.0.0.1:11434/api/chat','method':'POST','timeout':120,
 'payload':{'model':'hermes-local:qwen3.5-9b','stream':False,'keep_alive':'30m',
 'options':{'temperature':0,'num_predict':512,'num_ctx':65536},
 'messages':[{'role':'user','content':'offline wire capture'}],'tools':[]}}
assert not git('status','--porcelain')
print(json.dumps({'reviewed_commit':a.expected_head,'actual_pending_configuration_refused':True,
 'refusal':refusal,'execution_blockers':inspected['execution_blockers'],'runtime_modules_imported':False,
 'pending_config_constructors_services_delegates_called':0,'actual_client_offline_wire_capture':wire[0],'output_folder_created':False,'network_denied':True,
 'default_cli_exit':2,'frozen_baseline_commit':git('rev-parse','58add5e'),
 'frozen_files_byte_identical_count':len(frozen),'frozen_files_sha256':frozen_hashes,
 'unchanged_runner_sha256':sha(runner_original),'read_only_security_function_ast_unchanged':security_names,
 'source_sha256':{name:sha((root/name).read_bytes()) for name in ['scripts/qualify_phase2_once.py','scripts/passive_capture.py','src/evals/system_benchmark/local_worker.py','src/evals/system_benchmark/scope_observation_v1.py','src/agents/ollama_client.py']},
 'config_sha256':request.config_sha256},sort_keys=True))
