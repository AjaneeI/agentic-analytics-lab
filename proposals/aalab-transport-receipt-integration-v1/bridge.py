"""Inactive outer linkage; unchanged H1 and pinned clients own actual outcomes."""
import copy
import json
import os
from pathlib import Path
import sys
import h1_bridge as H1
import h2_transport as transport
from src.agents.ollama_client import OllamaModelClient
from src.tools.clickhouse_readonly import query_clickhouse

CONFIG={};CONFIG_SHA='';TRANSPORT=None
FLAGS={**H1.FLAGS,'fake_transport':True}

class TransportHost:
    def __init__(self,plan_bytes,fixture_bytes,evidence_root):
        if type(plan_bytes) is not bytes or len(plan_bytes)>16384:raise ValueError('bounded H2 plan bytes required')
        plan=H1.plan_decode(plan_bytes)
        if len(plan['invocations'])>2:raise ValueError('H2 two invocation bound')
        identities=[e['invocation_id'] for e in plan['invocations']]
        fixture=transport.decode_fixture(fixture_bytes,CONFIG_SHA,identities)
        self.root=Path(evidence_root).absolute()
        self._fixture=fixture;self._plan=plan;self._records={};self._proof={};self._reserved=[];self._used={}
        binding={'version':CONFIG['version'],'configuration_sha256':CONFIG_SHA,'source_commit':CONFIG['source_commit'],
          'contract_sha256':CONFIG['source_sha256'][CONFIG['proposal_path']+'/contract.json'],
          'plan_sha256':transport.sha(plan_bytes),'fixture_sha256':transport.sha(fixture_bytes),
          'h1_configuration_sha256':H1.CONFIG_SHA,'h1_source_commit':H1.CONFIG['source_commit'],**FLAGS}
        if len(transport.encoded(binding))>4096:raise ValueError('outer binding byte cap')
        self._binding=binding
        self._owner=transport.sha(transport.encoded({'binding':binding,'private_root':str(self.root)}))
        self.root.mkdir(parents=True,exist_ok=False)
        self._write(self.root/'h2-plan.json',plan_bytes);self._write(self.root/'h2-fixture.json',fixture_bytes)
        self._write(self.root/'h2-binding.json',transport.encoded(binding))
        self._sealed={name:transport.sha((self.root/name).read_bytes()) for name in ('h2-plan.json','h2-fixture.json','h2-binding.json')}
        self.h1=H1.prepare_host(plan_bytes,self.root/'h1')
    def _write(self,path,raw):
        path=Path(path)
        if type(raw) is not bytes or path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):raise ValueError('private H2 artifact required')
        used=self._used.get(path.parent,0)
        if used+len(raw)>65536:raise ValueError('H2 outer invocation artifact cap')
        self._used[path.parent]=used+len(raw)
        with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    def _intact(self):
        return all(not(self.root/name).is_symlink() and (self.root/name).is_file() and transport.sha((self.root/name).read_bytes())==value for name,value in self._sealed.items())
    def transport_receipt(self,invocation_id):return copy.deepcopy(self._records[invocation_id])
    def verify_transport(self,invocation_id,receipt):
        try:
            if not self._intact() or not receipt['complete'] or transport.encoded(receipt)!=self._proof[invocation_id]['receipt']:return False
            h1=self.h1.receipt(invocation_id)
            if not self.h1.verify(invocation_id,h1) or transport.sha(transport.encoded(h1))!=receipt['h1_receipt_sha256']:return False
            return all(not(self.root/name).is_symlink() and (self.root/name).is_file() and transport.sha((self.root/name).read_bytes())==value for name,value in self._proof[invocation_id]['files'].items())
        except (KeyError,ValueError,TypeError,OSError):return False

def prepare_transport_host(h1_plan_bytes,fixture_bytes,evidence_root):
    if TRANSPORT is None or not TRANSPORT.installed():raise RuntimeError('H2 sealed transport required')
    return TransportHost(h1_plan_bytes,fixture_bytes,evidence_root)

def run_transport_trial(host,invocation_id,*,task,reference):
    if type(host) is not TransportHost:raise ValueError('host-owned H2 context required')
    if not TRANSPORT.installed() or TRANSPORT.active is not None:raise RuntimeError('H2 sealed interceptor unavailable')
    index=len(host._reserved)
    if index>=len(host._plan['invocations']) or host._plan['invocations'][index]['invocation_id']!=invocation_id or invocation_id in host._reserved:raise ValueError('explicit unused H2 invocation required')
    if not host._intact():raise ValueError('retained H2 inputs changed')
    if getattr(sys,'_h2_trial_entries',0)>=2:raise ValueError('H2 per-control trial cap')
    specs=host._fixture['invocations'][index]['calls']
    out=host.root/'transport'/invocation_id;out.mkdir(parents=True,exist_ok=False)
    host._write(out/'entry.json',transport.encoded({'invocation_id':invocation_id,'owner':host._owner,**host._binding}))
    host._reserved.append(invocation_id);sys._h2_trial_entries=getattr(sys,'_h2_trial_entries',0)+1
    TRANSPORT.begin(host._owner,invocation_id,specs,lambda name,raw:host._write(out/name,raw))
    result=None;failure=None;calls=[];sequence_complete=False;capture_errors=[]
    try:
        result=H1.run_captured_trial(host.h1,invocation_id,task=task,reference=reference,
          scripted_model_factory=lambda:OllamaModelClient(model='H2-OFFLINE',base_url='https://ollama.h2.invalid',timeout=120),
          rows_callback_factory=lambda:(lambda sql:query_clickhouse(sql)))
    except BaseException as exc:failure=exc
    finally:
        try:calls,sequence_complete=TRANSPORT.finish(host._owner)
        except BaseException as exc:capture_errors.append({'stage':'transport_finish',**transport.error(exc)})
    try:
        h1=host.h1.receipt(invocation_id)
        h1_eligible=host.h1.verify(invocation_id,h1)
    except (KeyError,TypeError,ValueError,OSError):h1=None;h1_eligible=False
    receipt={**host._binding,'invocation_id':invocation_id,'owner':host._owner,'calls':calls,
      'h1_receipt_sha256':transport.sha(transport.encoded(h1)) if h1 is not None else None,
      'result_sha256':transport.sha(transport.encoded(result)) if result is not None else None,
      'success':result['task_success'] if result is not None else None,
      'score_status':h1['score_status'] if h1 is not None else 'not_reached',
      'surfaced_error':transport.error(failure) if failure is not None else None,
      'complete':h1_eligible and sequence_complete and not capture_errors,
      'capture_errors':capture_errors,'live_effective_settings':None,'live_model_digest':None,
      'setting_evidence':'synthetic observed request fields only; server application unavailable'}
    try:
        host._write(out/'transport-receipt.json',transport.encoded(receipt))
        files={str(p.relative_to(host.root)):transport.sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
        host._proof[invocation_id]={'receipt':transport.encoded(receipt),'files':files}
    except BaseException as exc:
        receipt['complete']=False;receipt['capture_errors'].append({'stage':'outer_finalization',**transport.error(exc)})
    host._records[invocation_id]=copy.deepcopy(receipt)
    if failure is not None:raise failure
    return result
