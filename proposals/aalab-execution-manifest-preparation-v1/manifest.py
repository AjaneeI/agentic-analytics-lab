"""Pure bounded declaration consistency only. No I/O or execution authentication."""
import hashlib
import json
import re
from datetime import datetime

VERSION='aalab-execution-manifest-preparation-v1'
ROOT_FIELDS={'version','synthetic','independence','cells'}
CELL_FIELDS={'task_id','task_version','family','arm','repeat_id','block_id','execution_order',
 'start_utc','end_utc','run_id','session_id','shared_block_id','seed_control',
 'treatment_sha256','configuration_sha256'}
CONTRACT={'version':VERSION,'state':'inactive_proposal','max_cells':32,'max_tasks':8,
 'arms':['baseline','candidate'],'repeat_labels':[1,2],'max_input_bytes':65536,
 'max_receipt_bytes':65536,'root_fields':sorted(ROOT_FIELDS),'cell_fields':sorted(CELL_FIELDS),
 'declared_dependence':['unknown','dependent'],'utc_format':'YYYY-MM-DDTHH:MM:SS[.ffffff]Z',
 'seed_control_fields':['reason','seed','state'],'sequential_only':True,
 'live_qualified':False,'independence_established':False,'scientific_ready':False,'new_attempts':0}
_ID=re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
_TASK=re.compile(r'P1-SYN-[A-Z0-9-]{1,48}\Z')
_HASH=re.compile(r'[0-9a-f]{64}\Z')
_UTC=re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6})?Z\Z',re.ASCII)

def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result

def _constant(value):raise ValueError('nonfinite JSON constant')

def _decode(raw):
    if type(raw) is not bytes or not 0<len(raw)<=65536:return None,'input_limit'
    try:return json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_constant),'ok'
    except (ValueError,TypeError,UnicodeError,RecursionError):return None,'invalid_json'

def _text(value,pattern):return type(value) is str and pattern.fullmatch(value) is not None

def _shape(doc):
    if type(doc) is not dict or set(doc)!=ROOT_FIELDS:return 'root_fields',{}
    if doc['version']!=VERSION or doc['synthetic'] is not True:return 'synthetic_version',{}
    if type(doc['independence']) is not str or doc['independence'] not in ('unknown','dependent'):
        return 'unsupported_independence',{}
    rows=doc['cells']
    if type(rows) is not list or not 0<len(rows)<=32:return 'cell_limit',{}
    tasks={};identities={};pairs={};blocks={};shared={};hashes={}
    for row in rows:
        if type(row) is not dict or set(row)!=CELL_FIELDS:return 'cell_fields',{}
        if not _text(row['task_id'],_TASK):return 'task_id',{}
        if any(not _text(row[k],_ID) for k in ('task_version','block_id','run_id','session_id','shared_block_id')):
            return 'identity_fields',{}
        if type(row['family']) is not str or row['family'] not in tuple('ABCDEFGH'):return 'family',{}
        if type(row['arm']) is not str or row['arm'] not in ('baseline','candidate'):return 'arm',{}
        if type(row['repeat_id']) is not int or row['repeat_id'] not in (1,2):return 'repeat_label',{}
        if type(row['execution_order']) is not str or row['execution_order'] not in ('AB','BA'):return 'order',{}
        if any(not _text(row[k],_HASH) for k in ('treatment_sha256','configuration_sha256')):return 'fingerprint',{}
        seed=row['seed_control']
        if type(seed) is not dict or set(seed)!={'state','seed','reason'}:return 'seed_state',{}
        if seed['state']=='controlled':
            if type(seed['seed']) is not int or not 0<=seed['seed']<2**63 or seed['reason'] is not None:
                return 'seed_state',{}
        elif seed['state']=='unavailable':
            if seed['seed'] is not None or type(seed['reason']) is not str or not seed['reason'].strip() or len(seed['reason'])>256:
                return 'seed_state',{}
        else:return 'seed_state',{}
        try:
            if any(not _text(row[k],_UTC) for k in ('start_utc','end_utc')):return 'chronology',{}
            start=datetime.fromisoformat(row['start_utc'].replace('Z','+00:00'))
            end=datetime.fromisoformat(row['end_utc'].replace('Z','+00:00'))
            if start>=end:return 'chronology',{}
        except (ValueError,TypeError,OverflowError):return 'chronology',{}
        membership=(row['task_version'],row['family'])
        if tasks.setdefault(row['task_id'],membership)!=membership:return 'task_membership',{}
        if len(tasks)>8:return 'task_limit',{}
        # A changed block must not create a second slot for the same task/arm/repeat.
        slot=tuple(row[k] for k in ('task_id','task_version','arm','repeat_id'))
        if slot in identities:return 'duplicate_identity',{}
        identities[slot]=row
        pair=tuple(row[k] for k in ('task_id','task_version','repeat_id','block_id'))
        pairs.setdefault(pair,{})[row['arm']]=(row,start,end)
        provenance=tuple(row[k] for k in ('run_id','session_id','shared_block_id'))
        if blocks.setdefault(row['block_id'],provenance)!=provenance:return 'pair_provenance',{}
        if shared.setdefault(row['shared_block_id'],provenance[:2])!=provenance[:2]:return 'shared_provenance',{}
        binding=tuple(row[k] for k in ('treatment_sha256','configuration_sha256'))
        if hashes.setdefault(row['arm'],binding)!=binding:return 'treatment_drift',{}
    for pair in pairs.values():
        if set(pair)!={'baseline','candidate'}:return 'missing_pair',{}
        a,b=pair['baseline'],pair['candidate']
        if a[0]['execution_order']!=b[0]['execution_order']:return 'order_conflict',{}
        first,second=(a,b) if a[0]['execution_order']=='AB' else (b,a)
        if first[2]>second[1]:return 'overlap',{}
    # Key includes block identity for exact host comparison; rows are never altered.
    index={tuple(row[k] for k in ('task_id','task_version','arm','repeat_id','block_id')):row for row in rows}
    return 'ok',index

def validate(manifest,*,expected):
    """Compare untrusted UTF-8 JSON bytes with independently supplied host bytes.

    Expected declarations are a trusted input, not authenticated by this function.
    Consistency cannot establish actual chronology, ownership or independence.
    """
    receipt={'version':VERSION,'active':False,'live_qualified':False,
      'independence_established':False,'scientific_ready':False,'new_attempts':0,
      'valid':False,'reason':'invalid_input','declared_dependence':'unknown','cell_count':0,
      'manifest_sha256':hashlib.sha256(manifest).hexdigest() if type(manifest) is bytes and len(manifest)<=65536 else None,
      'expected_sha256':hashlib.sha256(expected).hexdigest() if type(expected) is bytes and len(expected)<=65536 else None}
    host,reason=_decode(expected)
    if reason!='ok':receipt['reason']='expected_'+reason;return receipt
    reason,host_index=_shape(host)
    if reason!='ok':receipt['reason']='expected_'+reason;return receipt
    submitted,reason=_decode(manifest)
    if reason!='ok':receipt['reason']=reason;return receipt
    reason,index=_shape(submitted)
    if reason!='ok':receipt['reason']=reason;return receipt
    if index.keys()!=host_index.keys():receipt['reason']='identity_mismatch';return receipt
    if submitted['independence']!=host['independence'] or any(index[k]!=host_index[k] for k in index):
        receipt['reason']='binding_mismatch';return receipt
    receipt.update(valid=True,reason='consistent',declared_dependence=submitted['independence'],cell_count=len(index))
    return receipt
