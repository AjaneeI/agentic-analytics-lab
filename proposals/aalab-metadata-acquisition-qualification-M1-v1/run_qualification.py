"""M1 source bootstrap and owned-child supervisor. No implicit live mode."""
import argparse
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import time
import unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PACKAGE='df0b62acd2f3202c9307447a88bff135fa0f51f75d3fed25250847b16a021ef6'
HELPER='3f1e6e5c8ff19ddc85c43785cf5b177ac0bb6769eb207248f36e2f78d0f07639'
INPUTS=None
NAMES={'admission.py':'m1_admission','metadata.py':'m1_metadata','run_qualification.py':'m1_runtime','test_qualification.py':'m1_tests'}
STDLIB={'argparse','copy','hashlib','importlib','json','os','pathlib','platform','signal','socket','subprocess','sys','time','unittest','urllib'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check_imports(raw,path):
    # Builtin AST-only compile avoids adding a project dependency or importing code.
    tree=compile(raw,str(path),'exec',flags=1024);stack=[tree]
    while stack:
        n=stack.pop();kind=type(n).__name__
        if kind=='Import':
            for a in n.names:
                if a.name.split('.')[0] not in STDLIB|set(NAMES.values())|{'m1_helpers'}:raise ValueError('M1 unlisted import: '+a.name)
        if kind=='ImportFrom':
            if n.level or (n.module or '').split('.')[0] not in STDLIB|set(NAMES.values())|{'m1_helpers'}:raise ValueError('M1 unlisted import: '+str(n.module))
        for f in getattr(n,'_fields',()):
            v=getattr(n,f,None)
            if isinstance(v,list):stack.extend(x for x in v if hasattr(x,'_fields'))
            elif hasattr(v,'_fields'):stack.append(v)
class RetainedSource:
    def __init__(self,sources):self.sources=sources
    def find_spec(self,name,path=None,target=None):
        if name in self.sources:return importlib.util.spec_from_loader(name,self)
        if name=='src' or name.startswith('src.') or name.startswith('m1_'):raise ImportError('M1 unlisted project import: '+name)
        spec=importlib.machinery.PathFinder.find_spec(name,path)
        if spec and spec.origin and spec.origin not in ('built-in','frozen'):
            p=Path(spec.origin).resolve()
            if p.is_relative_to(ROOT) or 'site-packages' in p.parts:raise ImportError('M1 ambient project/third-party import: '+name)
    def create_module(self,spec):return None
    def exec_module(self,module):
        p,raw=self.sources[module.__name__];module.__file__=str(p)
        exec(compile(raw,str(p),'exec'),module.__dict__)
def bootstrap(mode='offline'):
    if not getattr(sys,'_m1_guard_installed',False):raise RuntimeError('M1 guarded child required')
    raw=(HERE/'qualification-config.json').read_bytes();config=json.loads(raw)
    if config['package_sha256']!=PACKAGE or config['helper_sha256']!=HELPER or config['version']!='aalab-metadata-acquisition-qualification-M1-v1':raise ValueError('M1 approved configuration required')
    if platform.python_version() not in ('3.11.16','3.12.6'):raise ValueError('M1 approved interpreter required')
    def verify():
        sources={};total=0
        for rel,pin in config['implementation_sha256'].items():
            p=ROOT/rel
            if p.is_symlink():raise ValueError('M1 source symlink refused')
            b=p.read_bytes();total+=len(b)
            if sha(b)!=pin:raise ValueError('M1 source pin mismatch: '+rel)
            if p.suffix=='.py':check_imports(b,p);sources[NAMES[p.name]]=(p,b)
        helper=Path(sys._m1_helper_path);b=helper.read_bytes();total+=len(b)
        if sha(b)!=HELPER or len(b)!=8535:raise ValueError('M1 retained helper mismatch')
        check_imports(b,helper);sources['m1_helpers']=(helper,b)
        if total>524288 or set(sources)!=set(NAMES.values())|{'m1_helpers'}:raise ValueError('M1 exact four-plus-one source closure required')
        if sha((HERE/'contract.json').read_bytes())!=config['contract_sha256']:raise ValueError('M1 contract mismatch')
        if sha((HERE/'qualification-config.json').read_bytes())!=sha(raw):raise ValueError('M1 configuration changed')
        return sources
    sources=verify()
    if any(n in sys.modules for n in set(sources)-{'m1_runtime'}):raise ValueError('M1 cached project module refused')
    sys.meta_path.insert(0,RetainedSource(sources))
    import m1_admission
    global INPUTS
    INPUTS=m1_admission.VerifiedInputs(mode)
    m1_admission.CONFIG=config;m1_admission.CONFIG_SHA=sha(raw);m1_admission.INPUTS=INPUTS;m1_admission.RECHECK=verify
    import m1_metadata
    if mode=='offline':
        import m1_tests
        m1_admission.FACTORY_TYPES=(m1_tests.Factory,);m1_admission.CLOCK_TYPES=(m1_tests.Clock,)
    return m1_admission,m1_metadata,config,raw
def terminal_disposition(handle,*,elapsed,kill):
    done=handle.poll() is not None
    if not done and elapsed>=9:kill()
    return {'cleanup_confirmed':done,'disposition':'reaped' if done else 'STOP_CLEANUP_UNCONFIRMED' if elapsed>=10 else 'pending'}
def validate(report,evidence,*,review=None):
    a,m,config,raw=bootstrap();import m1_tests
    m1_tests.EVIDENCE=evidence
    if review:
        b=review.read_bytes();mod=importlib.util.module_from_spec(importlib.util.spec_from_loader('_m1_review',None));mod.__file__=str(review)
        exec(compile(b,str(review),'exec'),mod.__dict__);mod.EVIDENCE=evidence
        suite=unittest.defaultTestLoader.loadTestsFromModule(mod);count=suite.countTestCases()
        if not 1<=count<=4:raise ValueError('M1 independent slot bound')
        review_sha=sha(b)
    else:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(m1_tests.M1Controls)
        if suite.countTestCases()!=12:raise ValueError('M1 exact12 authored slots required')
        review_sha=None
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sizes={d.name:sum(p.stat().st_size for p in d.rglob('*') if p.is_file()) for d in evidence.iterdir() if d.is_dir()}
    blocked=getattr(sys,'_m1_blocked',[]);passed=result.wasSuccessful() and not blocked and all(n<=262144 for n in sizes.values())
    r={'version':config['version'],'mode':'independent' if review else 'author','python':platform.python_version(),
      'configuration_sha256':sha(raw),'contract_sha256':config['contract_sha256'],'helper_sha256':HELPER,
      'implementation_sha256':config['implementation_sha256'],'review_source_sha256':review_sha,
      'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'blocked_effects':blocked,
      'per_control_bytes':sizes,'passed':passed,'real_requests':0,'scientific_replicates':0,'live_qualified':False}
    with report.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:r[k] for k in ('mode','tests','failures','errors','passed','real_requests')}))
    raise SystemExit(0 if passed else 1)
def install_real_guard(evidence,admission_path,ledger,helper):
    """No permission escalation: exact native call permitted only after reservation."""
    stdlib=Path(os.__file__).resolve().parent
    exact={HERE/n for n in (*NAMES,'README.md','contract.json','qualification-config.json')}|{admission_path,helper}
    blocked=[];counts={'socket':0,'connect':0}
    def audit(event,args):
        deny=event in ('subprocess.Popen','os.system','os.posix_spawn','os.fork','os.exec','sqlite3.connect','os.urandom')
        if event.startswith('socket.'):
            c=getattr(sys,'_m1_native_context',None)
            allowed=c is not None and c.mode=='real' and c._started and getattr(c,'_reserved',False) and getattr(c,'_entry_ready',False)
            if event=='socket.__new__':
                allowed=allowed and counts['socket']==0 and args[1:3]==(socket.AF_INET,socket.SOCK_STREAM)
                if allowed:counts['socket']+=1
            elif event=='socket.connect':
                allowed=allowed and counts['connect']==0 and args[1]==('127.0.0.1',11434)
                if allowed:counts['connect']+=1
            else:allowed=False
            deny|=not allowed
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=Path(os.fsdecode(args[0])).resolve();flags=args[2] if len(args)>2 else 0
            writing=(isinstance(args[1],str) and any(x in args[1] for x in 'wax+')) or isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
            if writing:deny|=not(p.is_relative_to(evidence) or p==ledger)
            else:deny|=not(p in exact or p==ledger or p.is_relative_to(evidence) or p.is_relative_to(stdlib) and 'site-packages' not in p.parts)
        if event=='import':deny|=args[0]=='src' or args[0].startswith('src.') or any(args[0]==x or args[0].startswith(x+'.') for x in ('sqlite3','openai','anthropic','ollama','numpy'))
        if deny:blocked.append(event);raise RuntimeError('M1 real boundary denied: '+event)
    sys.addaudithook(audit);sys._m1_guard_installed=True;sys._m1_blocked=blocked;sys._m1_helper_path=helper
    return counts
def real_child(record_path,record_sha,evidence,config_sha):
    # Only explicitly pinned operator-supplied evidence is read, no discovery.
    record_raw=record_path.read_bytes()
    if sha(record_raw)!=record_sha:raise ValueError('M1 admission record hash mismatch')
    record=json.loads(record_raw)
    helper=Path(record['retained_helper']).resolve();ledger=Path(record['authorization_ledger']).resolve()
    counts=install_real_guard(evidence,record_path,ledger,helper)
    a,m,config,raw=bootstrap('real')
    if sha(raw)!=config_sha or record['configuration_sha256']!=config_sha or record['package_sha256']!=PACKAGE:raise ValueError('M1 real reviewed pins mismatch')
    if record.get('version')!='M1-trusted-admission-v1' or record.get('executor_identity')!='01a14c56-cbf9-7071-a790-61f7eaa72f87':raise ValueError('M1 trusted executor source binding required')
    approval=record['approval'];owner=record['owner']
    if approval.get('source')!='https://github.com/AjaneeI/agentic-analytics-lab/issues/95#issuecomment-6529454607' or sha(approval['source_text'].encode())!=approval['source_text_sha256']:raise ValueError('M1 actual approval provenance required')
    if sha(owner['text'].encode())!=owner['source_text_sha256'] or owner['authorization_ledger']!=str(ledger):raise ValueError('M1 owner receipt integrity required')
    if not owner['source'].startswith(('https://github.com/AjaneeI/agentic-analytics-lab/','codex-thread:')):raise ValueError('M1 supported owner source required')
    ap=INPUTS._register('approval',approval);op=INPUTS._register('owner',owner);INPUTS._sealed=True
    plan={'version':'M1-plan-v1','operation_id':'M1-O-ONE','endpoint':a.ENDPOINT,'mode':'real','configuration_sha256':config_sha}
    c=a.prepare_metadata_qualification(json.dumps(plan).encode(),evidence/'transaction',approval_receipt=ap,owner_receipt=op)
    r=m.qualify_version_once(c)
    if sys._m1_blocked:r['capture_complete']=False;r['metadata_qualified']=False
    print(json.dumps({k:r[k] for k in ('disposition','received_bytes','wire_sha256','capture_complete','metadata_qualified','allowance_consumed','live_qualified')}))
def observe_parent(record_path,record_sha,evidence,config_sha):
    # This function is invoked only after external record/permission/window checks.
    # It makes no network call and has exactly one owned child, no retry loop.
    if evidence.exists():raise FileExistsError('M1 new observation output required')
    evidence.mkdir(parents=True,mode=0o700)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x0'}
    command=[sys.executable,'-I','-B',str(HERE/'run_qualification.py'),'--child-observe','--admission',str(record_path),'--admission-sha256',record_sha,'--evidence',str(evidence),'--configuration-sha256',config_sha]
    started=time.monotonic();p=None;raw=bytearray();stop=None;supervisor_error=None;gone=False;killed=False
    try:
        p=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        os.set_blocking(p.stdout.fileno(),False);eof=False
        while True:
            elapsed=time.monotonic()-started
            if p.poll() is not None and eof:break
            if elapsed>=9:stop='child_deadline';break
            if not eof:
                try:chunk=os.read(p.stdout.fileno(),min(4096,16385-len(raw)))
                except BlockingIOError:chunk=None
                if chunk==b'':eof=True
                elif chunk:
                    room=16384-len(raw);raw.extend(chunk[:room])
                    if len(chunk)>room:stop='output_cap';break
            # EOF is independent of owned-child liveness and never resets deadline.
            time.sleep(min(.005,max(0,9-(time.monotonic()-started))))
    except BaseException as exc:
        stop='supervisor_error';supervisor_error={'type':type(exc).__name__}
    finally:
        if p is not None:
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGKILL);killed=True
                except ProcessLookupError:pass
            remaining=max(0,10-(time.monotonic()-started))
            if remaining>0:
                try:p.wait(timeout=remaining)
                except subprocess.TimeoutExpired:stop=stop or 'cleanup_unconfirmed'
            if p.stdout is not None:p.stdout.close()
            try:os.killpg(p.pid,0);gone=False
            except ProcessLookupError:gone=True
    elapsed=time.monotonic()-started;code=p.returncode if p is not None else None
    final={'version':'M1-owned-observation-terminal-v1','exit_code':code,'stop':stop,'supervisor_error':supervisor_error,
      'elapsed_seconds':elapsed,'owned_group_gone':gone,'child_reaped':p is not None and code is not None,'kill_sent':killed,
      'cleanup_confirmed':gone and code is not None and elapsed<=10,'command':command,
      'configuration_sha256':config_sha,'admission_sha256':record_sha,'stdout_stderr_bytes':len(raw),'scientific_replicates':0}
    if not final['cleanup_confirmed']:final['stop']='STOP_CLEANUP_UNCONFIRMED'
    if sum(f.stat().st_size for f in evidence.rglob('*') if f.is_file())+len(raw)>61440:final['stop']='STOP_EVIDENCE_CAP'
    with (evidence/'child-output.log').open('xb') as f:f.write(raw)
    final_raw=json.dumps(final,sort_keys=True).encode()
    if len(final_raw)>4096:raise ValueError('M1 parent terminal ceiling')
    with (evidence/'parent-terminal.json').open('xb') as f:f.write(final_raw)
    print(json.dumps({'disposition':final['stop'] or 'terminal','cleanup_confirmed':final['cleanup_confirmed'],'exit_code':code}))
    return 0 if final['cleanup_confirmed'] and not final['stop'] and code==0 else 1
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--observe',action='store_true');g.add_argument('--child-observe',action='store_true')
    p.add_argument('--admission',type=Path,required=True);p.add_argument('--admission-sha256',required=True);p.add_argument('--configuration-sha256',required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();record=a.admission.resolve();evidence=a.evidence.resolve()
    if evidence.is_relative_to(ROOT):p.error('M1 private evidence outside source checkout required')
    if a.child_observe:real_child(record,a.admission_sha256,evidence,a.configuration_sha256)
    else:raise SystemExit(observe_parent(record,a.admission_sha256,evidence,a.configuration_sha256))
if __name__=='__main__':main()
