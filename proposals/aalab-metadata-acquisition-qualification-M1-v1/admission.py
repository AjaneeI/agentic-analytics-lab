"""M1 host-owned inputs and durable one-use metadata admission. No network."""
import copy
import json
import os
from pathlib import Path
import m1_helpers as helpers
CONFIG={};CONFIG_SHA='';INPUTS=None;RECHECK=None;FACTORY_TYPES=();CLOCK_TYPES=()
ENDPOINT='http://127.0.0.1:11434/api/version'
def authorization_ledger_path():
    return Path(__file__).resolve().parents[4]/'outputs'/CONFIG['evidence_directory_slug']/CONFIG['authorization_ledger_name']
FLAGS={'inactive':True,'live_qualified':False,'phase2_qualified':False,
 'live_authentication':False,'scientific_ready':False,'independence_established':False,'scientific_replicates':0,'new_TreatmentA_attempts':0}
class Receipt:
    def __init__(self,kind,payload):self.kind=kind;self._payload=copy.deepcopy(payload)
class VerifiedInputs:
    """Trusted bootstrap registry; payload declarations alone are not receipts.

    This is owner/host trust, not cryptographic authentication of native messages.
    Offline registrations can never serve as real observations' admission.
    """
    def __init__(self,mode):self.mode=mode;self._registry={};self._sealed=False
    def issue(self,kind,payload):
        if self.mode!='offline' or self._sealed:raise ValueError('real receipts require trusted source bootstrap')
        return self._register(kind,payload)
    def _register(self,kind,payload):
        r=Receipt(kind,payload);self._registry[r]=(kind,copy.deepcopy(payload));return r
    def payload(self,r,kind):
        if type(r) is not Receipt:raise ValueError('host-registered '+kind+' receipt required')
        if r not in self._registry or self._registry[r][0]!=kind:raise ValueError('host-registered '+kind+' receipt required')
        if r.kind!=kind or r._payload!=self._registry[r][1]:raise ValueError('registered receipt changed')
        return copy.deepcopy(self._registry[r][1])
def decode(raw):
    if type(raw) is not bytes or len(raw)>16384:raise ValueError('M1 bounded plan bytes required')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate plan key')
            d[k]=v
        return d
    d=json.loads(raw,object_pairs_hook=unique)
    if type(d) is not dict or set(d)!={'version','operation_id','endpoint','mode','configuration_sha256'}:raise ValueError('M1 closed plan required')
    if d['endpoint']!=ENDPOINT:raise ValueError('M1 fixed endpoint required')
    if d['version']!='M1-plan-v1' or d['configuration_sha256']!=CONFIG_SHA:raise ValueError('M1 exact configuration required')
    if d['mode']!=INPUTS.mode or d['mode'] not in ('offline','real'):raise ValueError('M1 mode not admitted')
    if d['operation_id'] not in ('M1-SYN-01','M1-O-ONE') or (d['mode']=='real')!=(d['operation_id']=='M1-O-ONE'):raise ValueError('M1 exact operation identity required')
    return d
class Context:
    def __init__(self,plan_bytes,root,approval,owner):
        self.plan=decode(plan_bytes);RECHECK()
        self.approval=INPUTS.payload(approval,'approval')
        self.owner=INPUTS.payload(owner,'owner') if owner is not None else None
        self.root=Path(root).absolute();self.mode=self.plan['mode'];self._started=False;self._reserved=False;self._entry_ready=False;self._record=None
        self._files={};self._bytes=0;self._factory=None;self._clock=None;self._limits={}
        if self.root.is_symlink():raise ValueError('M1 private root required')
        self.root.mkdir(parents=True,exist_ok=False,mode=0o700)
        self.binding={'version':CONFIG['version'],'operation_id':self.plan['operation_id'],
          'configuration_sha256':CONFIG_SHA,'contract_sha256':CONFIG['contract_sha256'],
          'implementation_sha256':copy.deepcopy(CONFIG['implementation_sha256']),
          'helper_sha256':CONFIG['helper_sha256'],'package_sha256':CONFIG['package_sha256'],
          'plan_sha256':helpers.sha(plan_bytes),'approval_sha256':helpers.sha(helpers.encoded(self.approval)),
          'owner_sha256':helpers.sha(helpers.encoded(self.owner)),'synthetic':self.mode=='offline',**FLAGS}
        self.write('plan.json',plan_bytes);self.write('binding.json',helpers.encoded(self.binding))
    def write(self,name,raw):
        ceiling=45056 if self.mode=='real' else 65536
        if type(raw) is not bytes or Path(name).name!=name or self._bytes+len(raw)>ceiling:raise ValueError('M1 private evidence ceiling/path')
        p=self.root/name
        if p.is_symlink() or not p.resolve().is_relative_to(self.root.resolve()):raise ValueError('M1 private file required')
        with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        self._bytes+=len(raw);self._files[name]=helpers.sha(raw)
    def intact(self):
        return all(not(self.root/n).is_symlink() and (self.root/n).is_file() and helpers.sha((self.root/n).read_bytes())==h for n,h in self._files.items())
    def admitted(self,utc):
        RECHECK()
        if not self.intact():return False,'retained inputs changed'
        if self.approval.get('package_sha256')!=CONFIG['package_sha256']:return False,'approval package mismatch'
        if self.owner is None:return False,'no current owner receipt'
        o=self.owner
        if o.get('route')!=ENDPOINT or o.get('incompatible_hold') is not False:return False,'owner route/hold mismatch'
        if not all(type(o.get(k)) in (int,float) for k in ('window_start','window_end')):return False,'unknown owner window'
        if not 0<o['window_end']-o['window_start']<=600 or not o['window_start']<=utc<=o['window_end']:return False,'owner window not current'
        if not all(type(o.get(k)) is str and o[k] for k in ('source','message_id','text','permission_source')):return False,'unverified owner provenance'
        if self.mode=='real':
            if not INPUTS._sealed or CONFIG.get('approved_real_operation')!='conditional-one-version-GET':return False,'real bootstrap unsealed'
            if not self.approval.get('M1_O_actual_human_approval') or not o.get('actual_source_verified') or not o.get('enforced_permission_verified'):return False,'real authority/permission not verified'
            if not all(o.get(k) for k in ('actor_identity','actor_authority_source','source_text_sha256','reviewed_commit','reviewed_tree','no_newer_hold_source','authorization_ledger')):return False,'real evidence binding incomplete'
            if o.get('configuration_sha256')!=CONFIG_SHA or o.get('reviewed_tree')!=self.approval.get('reviewed_tree'):return False,'reviewed pins differ'
        return True,None
    def reserve(self,utc):
        entry=helpers.encoded({'binding':self.binding,'admission_utc_epoch':utc,
          'request':'GET /api/version HTTP/1.0','consumption':'one socket admission, consumed on failure',**FLAGS})
        # Real allowance also has one fixed, cross-invocation authorization ledger.
        if self.mode=='real':
            path=Path(self.owner['authorization_ledger'])
            expected=authorization_ledger_path()
            if path.resolve()!=expected:raise ValueError('M1 fixed authorization ledger required')
            try:
                with path.open('xb') as f:f.write(entry);f.flush();os.fsync(f.fileno())
            except FileExistsError:
                self._reserved=True  # A prior/partial reservation is never reusable.
                raise
            self._reserved=True  # Irreversible consumption precedes local entry.
        self.write('RESERVED.json',entry)
        self._reserved=True;self._entry_ready=True
def prepare_metadata_qualification(plan_bytes,evidence_root,*,approval_receipt,owner_receipt):
    if INPUTS is None:raise RuntimeError('M1 trusted bootstrap required')
    return Context(plan_bytes,evidence_root,approval_receipt,owner_receipt)
