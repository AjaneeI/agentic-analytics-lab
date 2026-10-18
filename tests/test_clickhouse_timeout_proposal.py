"""Keep the versioned timeout candidate inactive and exercise it offline."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / 'proposals/runtime-clickhouse-expression-jit-off-v1'

class TestInactiveClickHouseTimeoutProposal(unittest.TestCase):
    def test_pinned_patch_is_inactive_and_passes_fake_http_contracts_in_disposable_copy(self):
        manifest = json.loads((PROPOSAL/'manifest.json').read_text())
        patch_file = PROPOSAL/'candidate.patch'
        self.assertFalse(manifest['activation_authorized'])
        self.assertEqual(manifest['live_attempts_authorized'], 0)
        self.assertEqual(hashlib.sha256(patch_file.read_bytes()).hexdigest(), manifest['patch_sha256'])
        config = PROPOSAL/'candidate-configuration.inactive.json'
        self.assertEqual(hashlib.sha256(config.read_bytes()).hexdigest(), manifest['candidate_configuration_sha256'])
        self.assertFalse(json.loads(config.read_text())['active'])
        probe = PROPOSAL/'test_candidate_transport.py'
        self.assertEqual(hashlib.sha256(probe.read_bytes()).hexdigest(), manifest['candidate_test_sha256'])
        for relative, hashes in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(), hashes['base_sha256'])
        with tempfile.TemporaryDirectory(prefix='clickhouse-timeout-offline-') as directory:
            target = Path(directory)
            shutil.copytree(ROOT/'src', target/'src', ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run(['git','apply','--check',str(patch_file)],cwd=target,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            subprocess.run(['git','apply',str(patch_file)],cwd=target,check=True)
            for relative, hashes in manifest['files'].items():
                self.assertEqual(hashlib.sha256((target/relative).read_bytes()).hexdigest(), hashes['candidate_sha256'])
            shutil.copyfile(probe,target/'test_candidate_transport.py')
            code = '''
import sys, unittest
def deny(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo'):
        raise AssertionError('live network forbidden')
sys.addaudithook(deny)
unittest.main(module='test_candidate_transport', verbosity=2)
'''
            result = subprocess.run([sys.executable,'-B','-c',code],cwd=target,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Ran 6 tests',result.stderr)

if __name__ == '__main__':
    unittest.main()
