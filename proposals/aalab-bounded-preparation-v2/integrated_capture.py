"""Inactive new synthetic capture integration of pinned PR122 + PR123 lineage.

Loaded only by the verified-source offline entrypoint. Registry/context and call
selection remain host-owned; this does not authenticate a live capture.
Original adapter/scorer/evidence stay unchanged. Capture core reused from PR122
836e4060dc72afc837640e74f6fc4dc138b2178f06ca08f7b703d84c5c129f26.
"""
from dataclasses import dataclass
import json
import re
import sqlite3
import time
import uuid
from _aal_v2_lineage import verifier, integration_contract_sha256
from semantic_guards import assess

class CaptureLimitError(RuntimeError):
    """An offline adapter bound stopped execution or collection."""

def validate_host_config(config):
    if (not isinstance(config,dict) or not isinstance(config.get('source_commit'),str)
        or not re.fullmatch('[0-9a-f]{40}',config['source_commit'])
        or not isinstance(config.get('version'),str) or not config['version']
        or config.get('task_id')!='SB-D01' or config.get('metric')!=verifier.VERSION
        or '_capture_contract_sha256' in config):
        raise ValueError('invalid host configuration')

@dataclass(frozen=True)
class CallToken:
    execution_id:str
    call_id:str

@dataclass(frozen=True)
class CaptureEvent:
    execution_id:str|None
    call_id:str|None
    query_sha256:str|None
    execute_attempts:int
    success:bool
    complete:bool
    returned_rows:int
    error_type:str|None
    error_message:str|None
    elapsed_seconds:float
    rejected_query_json:str|None=None

class SyntheticCaptureSession:
    """Own one closed synthetic snapshot and up to two one-shot SELECT calls.

    query(sql) returns only ordinary result rows. calls/context/resolve/verify
    are host-only side channels and must never be passed to an agent.
    """
    def __init__(self,rows,config):
        if not verifier.snapshot_valid(rows):raise ValueError('invalid synthetic snapshot')
        validate_host_config(config)
        try:
            snapshot_json=verifier.canonical(rows)
            frozen_config=dict(config,_capture_contract_sha256=integration_contract_sha256)
            config_json=verifier.canonical(frozen_config)
        except (ValueError,TypeError,RecursionError) as e:raise ValueError('invalid serializable host inputs') from e
        if len(snapshot_json)+len(config_json)>1024*1024:
            raise ValueError('snapshot/config exceeds offline bound')
        self._snapshot_json=snapshot_json
        self._config_json=config_json
        self._session=uuid.uuid4().hex
        self._entries=[]
        self._records={}
        self._expected={}
        self._events=[]
        self._closed=False
        self._connection=sqlite3.connect(':memory:')
        try:
            self._connection.row_factory=sqlite3.Row
            # One fixture table in a privately attached memory-only namespace;
            # both approved qualified and unqualified names resolve to it.
            self._connection.execute("ATTACH DATABASE ':memory:' AS agentic_analytics")
            self._connection.execute('CREATE TABLE agentic_analytics.delivery_work_items (id INTEGER PRIMARY KEY, team TEXT NOT NULL, status TEXT NOT NULL, blocked INTEGER NOT NULL)')
            self._connection.executemany('INSERT INTO agentic_analytics.delivery_work_items VALUES (:id,:team,:status,:blocked)',json.loads(snapshot_json))
            self._connection.commit()
            self._connection.execute('PRAGMA query_only=ON')
            self._connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2*1024*1024)
            self._connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH,8192)
            self._connection.set_authorizer(self._authorize)
            self._connection.set_progress_handler(lambda:1,100000)
        except BaseException:
            self._connection.close();self._closed=True;raise

    @staticmethod
    def _authorize(action,arg1,arg2,database,trigger):
        if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
        if (action==sqlite3.SQLITE_READ and arg1=='delivery_work_items'
            and (database=='agentic_analytics' or (arg2=='' and database is None))):
            # SQLite emits an empty-column/table-only read for some scans.
            # Attachments remain forbidden; this is the sole owned table.
            return sqlite3.SQLITE_OK
        if action==sqlite3.SQLITE_FUNCTION and arg2.lower() in ('sum','count','avg'):return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    @property
    def calls(self):return tuple(self._entries)

    @property
    def events(self):return tuple(self._events)

    @property
    def config_json(self):return self._config_json

    def query(self,sql):
        if self._closed:self._reject(RuntimeError('synthetic session is closed'),sql)
        if len(self._entries)>=2:self._reject(CaptureLimitError('two-call offline session bound'),sql)
        if not isinstance(sql,str) or not sql or len(sql)>8192:
            self._reject(ValueError('query must be a nonempty string within offline bound'),sql)
        try:sql.encode('utf-8')
        except UnicodeEncodeError as error:self._reject(error,sql)
        token=CallToken(self._session+'/'+str(len(self._entries)+1),str(len(self._entries)+1))
        self._entries.append(token)
        started=time.monotonic();rows=[];success=complete=False;error=None
        try:
            cursor=self._connection.execute(sql)
            names=[description[0] for description in cursor.description or ()]
            if (not names or any(not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*',name) for name in names)
                or len({name.lower() for name in names})!=len(names)):
                raise CaptureLimitError('ambiguous or unsupported result labels')
            size=len(sql)+len(self._snapshot_json)+len(self._config_json)+2
            while True:
                raw=cursor.fetchone()
                if raw is None:break
                if len(rows)>=1000:raise CaptureLimitError('incomplete result: row bound exceeded')
                row=dict(raw);addition=len(verifier.canonical(row))+(1 if rows else 0)
                if size+addition>2*1024*1024:
                    raise CaptureLimitError('incomplete result: serialized bound exceeded')
                rows.append(row);size+=addition
            success=complete=True
            # Rows returned to the callback caller cannot mutate frozen capture.
            return json.loads(verifier.canonical(rows))
        except BaseException as e:
            error=e
            raise
        finally:
            record=verifier.capture(execution_id=token.execution_id,call_id=token.call_id,
                query=sql,rows=rows,snapshot=json.loads(self._snapshot_json),config=json.loads(self._config_json),
                origin='synthetic_sqlite',success=success,complete=complete)
            self._records[token.execution_id]=record
            self._expected[token.execution_id]=verifier.binding(record)
            self._events.append(CaptureEvent(token.execution_id,token.call_id,verifier.digest(sql),1,
                success,complete,len(rows),type(error).__name__ if error else None,
                str(error)[:1024] if error else None,time.monotonic()-started))

    def resolve(self,execution_id):
        return self._records.get(execution_id) if isinstance(execution_id,str) else None

    def _reject(self,error,sql):
        try:query_hash=verifier.digest(sql) if isinstance(sql,str) else None
        except UnicodeEncodeError:query_hash=None
        rejected_json=verifier.canonical(sql) if isinstance(sql,str) and len(sql)<=8192 else None
        self._events.append(CaptureEvent(None,None,query_hash,
            0,False,False,0,type(error).__name__,str(error),0.0,rejected_json))
        raise error

    def verification_context(self,call):
        if not any(call is token for token in self._entries):
            raise ValueError('untrusted_call_token')
        return {'resolver':self,'expected':dict(self._expected[call.execution_id])}

    def verify(self,claim,*,call=None):
        if call is None:return verifier.outcome('insufficient','explicit_call_required')
        try:context=self.verification_context(call)
        except ValueError:return verifier.outcome('insufficient','untrusted_call_token')
        return verifier.verify(claim,**context)

    def close(self):
        if not self._closed:self._connection.close();self._closed=True

    def __enter__(self):return self

    def __exit__(self,*args):self.close()

def assess_answer(host,claim,answer,*,call,policy_context):
    """Compose selected-capture proof and declared-form answer checks offline.

    Host constructs policy context independently. Final metric context is always
    derived from the mathematically proven selected capture, not a supplied
    context value or the claimant's tolerated percentage. No SQL is repeated.
    """
    proof=host.verify(claim,call=call)
    if proof['status']!='proven':return proof
    if type(policy_context) is not dict or type(answer) is not str or len(answer)>4096:
        return verifier.outcome('insufficient','unsupported_answer_context')
    text=answer[:-1] if answer.endswith('.') else answer
    clauses=text.split('. ')
    final_form=r'[A-Za-z][A-Za-z -]{0,63} has the highest blocker rate at [0-9]{1,3}(?:\.[0-9]{1,8})?% among (?:all|active) work items'
    if not any(re.fullmatch(final_form,clause) for clause in clauses):
        return verifier.outcome('insufficient','final_metric_clause_required')
    context=dict(policy_context,task_id='SB-D01',metric_population='active',
        final_metric={'team':claim['team'],'percentage':proof['percentage_exact'],
                      'population':'active','tolerance_pp':'0.2'})
    result=assess(answer,context=context)
    return dict(result,capture_contract_sha256=proof['contract_sha256'],
                query_sha256=proof['query_sha256'],integration_contract_sha256=integration_contract_sha256)
