"""Offline tamper checks in private copied fixtures; never mutate prior sources."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
import marshal
import struct
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEPENDENCIES=(
 'proposals/phase3-d01-provenance-v1/run_validation.py',
 'proposals/phase3-d01-provenance-v1/test_verifier.py',
 'proposals/phase3-d01-provenance-v1/verifier.py',
 'proposals/phase3-d01-provenance-v1/sql_proof.py',
 'proposals/phase3-d01-provenance-v1/contract.json',
 'proposals/phase3-d01-capture-integration-v1/capture_adapter.py',
 'proposals/phase3-d01-capture-integration-v1/contract.json')

class DependencyImportAttempt(RuntimeError):pass

class PreflightControls(unittest.TestCase):
 def fixture(self,directory):
  root=Path(directory).resolve();here=root/'proposals/phase3-d01-tie-order-v1';here.mkdir(parents=True)
  for f in HERE.iterdir():
   if f.is_file():shutil.copyfile(f,here/f.name)
  for relative in DEPENDENCIES:
   dst=root/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,dst)
  config_file=here/next(name for name in ['synthetic-config-v3.json','synthetic-config-v2.json','synthetic-config.json'] if (here/name).exists())
  config=json.loads(config_file.read_text());config['source_sha256']={name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in config['source_sha256']};config['dependency_sha256']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in DEPENDENCIES}
  config_file=here/'test-config.json';config_file.write_text(json.dumps(config))
  return root,here,config_file,config

 def check_rejected(self,mutate):
  with tempfile.TemporaryDirectory() as directory:
   root,here,path,config=self.fixture(directory);mutate(root,here,path,config)
   attempted=[];original=importlib.util.spec_from_file_location
   def loader(name,location,*args,**kwargs):
    if Path(location).resolve().is_relative_to(root) and Path(location).resolve()!=here/'run_validation.py':
     attempted.append(str(location));raise DependencyImportAttempt(str(location))
    return original(name,location,*args,**kwargs)
   code=None;stderr=io.StringIO();output=root/'result.json'
   with patch.object(importlib.util,'spec_from_file_location',loader),redirect_stderr(stderr),redirect_stdout(io.StringIO()):
    try:
     spec=original('_isolated_preflight_test',here/'run_validation.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
     with patch.object(sys,'argv',['run_validation.py','--configuration',str(path),'--output',str(output)]):module.main()
    except SystemExit as e:code=e.code
    except DependencyImportAttempt:pass
   self.assertEqual(attempted,[], 'dependency code loaded before rejection')
   self.assertEqual(code,2,stderr.getvalue());self.assertFalse(output.exists())

 def test_tamper_each_dependency_rejected_before_import(self):
  for relative in DEPENDENCIES:
   with self.subTest(path=relative):
    self.check_rejected(lambda root,here,path,config:(root/relative).write_bytes((root/relative).read_bytes()+b'\nTAMPERED\n'))

 def test_missing_dependency_rejected_before_import(self):
  for relative in DEPENDENCIES:
   with self.subTest(path=relative):self.check_rejected(lambda root,here,path,config:(root/relative).unlink())

 def test_incomplete_extra_and_forged_manifest_rejected(self):
  for kind in ['missing','extra','forged','type','traversal']:
   def mutation(root,here,path,config):
    if kind=='missing':config['dependency_sha256'].pop(DEPENDENCIES[0])
    elif kind=='extra':config['dependency_sha256']['unexpected.py']='0'*64
    elif kind=='forged':config['dependency_sha256'][DEPENDENCIES[0]]='0'*64
    elif kind=='type':config['dependency_sha256']=[]
    else:config['dependency_sha256']['../../private.py']='0'*64
    path.write_text(json.dumps(config))
   with self.subTest(kind=kind):self.check_rejected(mutation)

 def test_modified_contract_pin_cannot_be_overridden_by_config(self):
  def mutation(root,here,path,config):
   key=DEPENDENCIES[2];target=root/key;target.write_bytes(target.read_bytes()+b'\n')
   config['dependency_sha256'][key]=hashlib.sha256(target.read_bytes()).hexdigest()
   path.write_text(json.dumps(config))
  self.check_rejected(mutation)

 def test_old_configuration_refuses_before_import(self):
  def mutation(root,here,path,config):path.write_bytes((here/'synthetic-config.json').read_bytes())
  self.check_rejected(mutation)

 def test_import_is_inert_and_valid_preflight_verifies_all_dependencies(self):
  with tempfile.TemporaryDirectory() as directory:
   root,here,path,config=self.fixture(directory);attempted=[];original=importlib.util.spec_from_file_location
   def loader(name,location,*args,**kwargs):
    if Path(location).resolve().is_relative_to(root):attempted.append(str(location));raise DependencyImportAttempt(str(location))
    return original(name,location,*args,**kwargs)
   module=None
   with patch.object(importlib.util,'spec_from_file_location',loader):
    try:
     spec=original('_inert_import_control',here/'run_validation.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    except DependencyImportAttempt:pass
   self.assertEqual(attempted,[], 'import executes upstream code')
   self.assertTrue(callable(getattr(module,'preflight',None)))
   verified,receipt=module.preflight(path)
   self.assertEqual(verified['dependency_sha256'],config['dependency_sha256'])
   self.assertEqual(receipt['dependency_sha256'],config['dependency_sha256'])
   self.assertEqual(receipt['verified_dependency_count'],7)


 def test_verified_source_executes_instead_of_stale_bytecode_or_cached_modules(self):
  names=['sql_proof','verifier','test_verifier','_tie_guard_upstream','tie_sql_proof',
         'verifier_candidate','test_tie_order','test_preflight']
  with tempfile.TemporaryDirectory() as directory:
   root,here,path,config=self.fixture(directory)
   targets=[root/key for key in DEPENDENCIES if key.endswith('.py') and 'capture_adapter' not in key]
   targets += [here/name for name in ['tie_sql_proof.py','verifier_candidate.py','test_tie_order.py','test_preflight.py']]
   for target in targets:
    stat=target.stat();cache=Path(importlib.util.cache_from_source(str(target)));cache.parent.mkdir(exist_ok=True)
    marker=compile('raise RuntimeError("UNVERIFIED_BYTECODE_EXECUTED")',str(target),'exec')
    cache.write_bytes(importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(stat.st_mtime),stat.st_size)+marshal.dumps(marker))
   spec=importlib.util.spec_from_file_location('_verified_source_execution_control',here/'run_validation.py')
   module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   module.preflight(path)
   previous={name:sys.modules.get(name) for name in names};old_path=list(sys.path);old_meta=list(sys.meta_path)
   try:
    for name in names:sys.modules.pop(name,None)
    try:module._load_verified_dependencies()
    except RuntimeError as error:self.fail('unverified bytecode selected: '+str(error))
    self.assertEqual(module.test_tie_order.v.VERSION,'phase3-d01-tie-order-v1')
    # Replacing already-cached modules must not change the verified selection.
    sys.modules['test_tie_order']=object()
    module._load_verified_dependencies()
    self.assertEqual(module.test_tie_order.v.VERSION,'phase3-d01-tie-order-v1')
   finally:
    sys.path[:]=old_path;sys.meta_path[:]=old_meta
    for name,value in previous.items():
     if value is None:sys.modules.pop(name,None)
     else:sys.modules[name]=value

if __name__=='__main__':unittest.main()
