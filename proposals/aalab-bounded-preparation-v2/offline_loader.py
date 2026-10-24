"""Explicit verified-source loader for the inactive preparation only."""
import hashlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MODULES=("semantic_guards","endpoint_contract","integrated_capture",
         "test_capture_integration","test_semantic_guards","test_endpoint_contract","test_preflight")
SOURCE={"offline_loader.py","run_validation.py","contract.json","compatibility-roster.json",
        *(name+".py" for name in MODULES)}
DEPENDENCIES={
    "evals/system_benchmark/development_tasks.json",
    "evals/system_benchmark/development_references.json",
    "proposals/phase3-d01-provenance-v1/sql_proof.py",
    "proposals/phase3-d01-provenance-v1/verifier.py",
    "proposals/phase3-d01-provenance-v1/contract.json",
    "proposals/phase3-d01-capture-integration-v1/capture_adapter.py",
    "proposals/phase3-d01-capture-integration-v1/contract.json",
    "proposals/phase3-d01-tie-order-v1/tie_sql_proof.py",
    "proposals/phase3-d01-tie-order-v1/verifier_candidate.py",
    "proposals/phase3-d01-tie-order-v1/contract.json",
    "proposals/phase3-d01-tie-order-v1/run_validation.py",
    "proposals/phase3-d01-tie-order-v1/synthetic-config-v3.json"}

def sha(data):return hashlib.sha256(data).hexdigest()

def _retain(pins,names,root,retained):
    if not isinstance(pins,dict) or pins.keys()!=names:
        raise ValueError("incomplete or unexpected source manifest")
    for name in sorted(names):
        expected=pins[name]
        if not isinstance(expected,str) or re.fullmatch("[0-9a-f]{64}",expected) is None:
            raise ValueError("invalid source fingerprint")
        path=root/name
        if path.absolute()!=path.resolve() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("source link or outside checkout")
        data=path.read_bytes()
        if sha(data)!=expected:raise ValueError("source fingerprint mismatch: "+name)
        retained[str(path.resolve())]=data

def preflight(configuration):
    config=json.loads(Path(configuration).read_text())
    if (not isinstance(config,dict) or config.get("version")!="aalab-bounded-preparation-v2"
        or config.get("state")!="inactive_proposal" or config.get("activation") is not False
        or config.get("live_qualified") is not False
        or type(config.get("authorized_treatment_a_attempts")) is not int
        or config["authorized_treatment_a_attempts"]!=0
        or not isinstance(config.get("source_commit"),str)
        or re.fullmatch("[0-9a-f]{40}",config["source_commit"]) is None
        or config.get("approved_package_sha256")!="6c4762587e35edd6d0ed6babc10949c7b0f1ad67e308d264623e963812ccce46"):
        raise ValueError("inactive configuration/approval mismatch")
    retained={}
    _retain(config.get("source_sha256"),SOURCE,HERE,retained)
    _retain(config.get("dependency_sha256"),DEPENDENCIES,ROOT,retained)
    contract=json.loads(retained[str((HERE/"contract.json").resolve())])
    if (contract.get("state")!="inactive_proposal" or contract.get("version")!=config["version"]
        or contract.get("dependency_sha256")!=config["dependency_sha256"]
        or contract.get("claim_tolerance_percentage_points")!="0.2"):
        raise ValueError("integration contract mismatch")
    tie_path=ROOT/"proposals/phase3-d01-tie-order-v1/contract.json"
    tie=json.loads(retained[str(tie_path.resolve())])
    if (tie.get("version")!="phase3-d01-tie-order-v1"
        or tie.get("claim_tolerance_percentage_points")!=0.2
        or any(config["dependency_sha256"].get(k)!=v for k,v in tie["upstream_source_sha256"].items())):
        raise ValueError("upstream contract commitment mismatch")
    roster=json.loads(retained[str((HERE/"compatibility-roster.json").resolve())])
    if (roster.get("source_commit")!="15256f598e70bb09032120c0f0c0cf9e289a25fe"
        or roster.get("task_ids")!=["SB-A01","SB-C01","SB-C02","SB-D01","SB-E01","SB-G01","SB-H01"]
        or roster.get("bank_activation") is not False or roster.get("scientific_membership_accepted") is not False):
        raise ValueError("compatibility roster mismatch")
    for name,record in roster["source_files"].items():
        path="evals/system_benchmark/"+name
        if config["dependency_sha256"].get(path)!=record["sha256"]:
            raise ValueError("roster source fingerprint mismatch")
    tasks=json.loads(retained[str((ROOT/"evals/system_benchmark/development_tasks.json").resolve())])
    refs=json.loads(retained[str((ROOT/"evals/system_benchmark/development_references.json").resolve())])
    task_rows=tasks if isinstance(tasks,list) else tasks.get("tasks",[])
    ref_rows=refs if isinstance(refs,list) else refs.get("references",[])
    if (sorted(row.get("id") for row in task_rows)!=sorted(roster["task_ids"])
        or len(ref_rows)!=7 or any(row.get("split")!="development" for row in task_rows)):
        raise ValueError("exact development compatibility membership mismatch")
    return config,retained

class PinnedContract:
    def __init__(self,data):self._data=bytes(data)
    def read_bytes(self):return self._data
    def read_text(self,*args,**kwargs):return self._data.decode("utf-8")

def execute_source(name,path,retained):
    module=ModuleType(name);module.__file__=str(path);module.__package__=""
    sys.modules[name]=module
    exec(compile(retained[str(path.resolve())],str(path),"exec"),module.__dict__)
    return module

def load_candidate(retained):
    tie=ROOT/"proposals/phase3-d01-tie-order-v1"
    prior=sys.modules.get("tie_sql_proof")
    try:
        execute_source("tie_sql_proof",tie/"tie_sql_proof.py",retained)
        verifier=execute_source("_aal_v2_verifier",tie/"verifier_candidate.py",retained)
    finally:
        if prior is None:sys.modules.pop("tie_sql_proof",None)
        else:sys.modules["tie_sql_proof"]=prior
    verifier.CONTRACT_PATH=PinnedContract(retained[str((tie/"contract.json").resolve())])
    lineage=ModuleType("_aal_v2_lineage");lineage.verifier=verifier
    lineage.integration_contract_sha256=sha(retained[str((HERE/"contract.json").resolve())])
    sys.modules[lineage.__name__]=lineage
    # All modules are fresh even if a caller or a .pyc cache supplies names.
    return {name:execute_source(name,HERE/(name+".py"),retained) for name in MODULES}
