"""Read-only verification of authorized source/config and historical evidence."""
from pathlib import Path
import hashlib,json,subprocess,sys
b=Path(__file__).resolve().parent.parent;r=b/'work/phase2-jit-off-authorized';o=b/'outputs/jit-off-one-attempt-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=r,text=True).strip()
parent='4d98b8f09b89e9d44aad39d41409cfcec67740ee'
prep=json.loads((o/'authorization-preparation.json').read_text());cfgpath=Path(prep['configuration']);cfg=json.loads(cfgpath.read_text())
assert sha(cfgpath)==prep['configuration_sha256']=='f1afa4f6d3b6238b87155729d63453dd43d7d001f6aeb45c99cd64dd9e8ca27b'
old=json.loads(subprocess.check_output(['git','show',parent+':configurations/phase2-runtime-schema-v1-scope-observation-v1-response-format-v1-expression-jit-off-v1.activated.json'],cwd=r,text=True))
changes={k:{'before':old.get(k),'after':v} for k,v in cfg.items() if old.get(k)!=v}
assert set(changes)=={'live_treatment_a_authorization','authorized_live_attempts','authorization_record_id','authorization_configuration_parent_commit','authorization_configuration_parent_sha256','live_authorization_record','live_authorization_source','authorized_evidence_directory','authorization_consumption'}
assert cfg['live_treatment_a_authorization']=='approved' and type(cfg['authorized_live_attempts']) is int and cfg['authorized_live_attempts']==1
paths=git('ls-tree','-r','--name-only',parent).splitlines();preserved={}
for name in paths:
    if name=='STATUS.md':continue
    raw=subprocess.check_output(['git','show',parent+':'+name],cwd=r)
    assert (r/name).read_bytes()==raw,name
    if name.startswith(('src/','evals/','scripts/','configurations/')):preserved[name]=sha(r/name)
sys.path.insert(0,str(r));from scripts.passive_capture import contract_fingerprint
fingerprint=contract_fingerprint(r);assert fingerprint['benchmark_contract_sha256']==cfg['benchmark_contract_sha256']=='6d6403103d690cb48827f233fdf059925c15fc6c81e50316fdf845b7bd049df4'
oldpacket=b/'outputs/jit-off-activation-v1';inventory=json.loads((oldpacket/'sha256.json').read_text())
assert all(sha(oldpacket/name)==value for name,value in inventory.items())
prior=json.loads((oldpacket/'preservation-receipt.json').read_text());archives=prior['seven_prior_archives_unchanged'].copy();archives['outputs/jit-off-activation-v1/jit-off-activation-evidence.zip']='30af16da527325ce8c7630f289154304851bbc40e2cac636a91cc90cd7254636'
assert all(sha(b/name)==value for name,value in archives.items())
raws={}
for name in ['treatment-a-20261017','treatment-a-scope-v1-20261017','treatment-a-response-format-v1-20261017']:
    root=b/'outputs'/name;sealed=root/'sha256.json';assert sha(sealed)==prior['historical_seals'][name]['seal_sha256'];items=json.loads(sealed.read_text());assert all(sha(root/k)==v for k,v in items.items());raws[name]={'files':len(items),'seal_sha256':sha(sealed),'unchanged':True}
report={'parent_activation_commit':parent,'configuration_sha256':sha(cfgpath),'configuration_changes_only_authorization_fields':changes,'runtime_source_changes':[],
 'frozen_existing_source_and_configuration_files':preserved,'experimental_contract':fingerprint,
 'historical_raw_runs':raws,'eight_historical_archives':archives,'activation_evidence_inventory_verified':len(inventory),
 'existing_dataset_csv_sha256':sha(Path('/Users/ajaneeigharo/Projects/agentic-analytics-lab/data/delivery_work_items.csv')),
 'new_Treatment_A_attempts_at_verification':1 if (b/'outputs/treatment-a-jit-off-v1-20261018/INVOCATION_STARTED.json').exists() else 0}
target=o/('source-and-preservation-after.json' if '--after' in sys.argv else 'source-and-preservation-before.json')
with target.open('x') as stream:stream.write(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'unchanged_runtime':True,'unchanged_existing_files':len(preserved),'historical_raw_files':sum(x['files'] for x in raws.values()),'archives':len(archives),'contract':fingerprint['benchmark_contract_sha256']},indent=2))
