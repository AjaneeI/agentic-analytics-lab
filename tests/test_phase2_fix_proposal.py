"""Exercise the inactive proposal in a disposable copy, never the frozen runtime."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / 'proposals/phase2-runtime-schema-v1'


class TestInactivePhase2FixProposal(unittest.TestCase):
    def test_patch_applies_only_to_exact_sources_and_passes_offline_contracts(self):
        manifest = json.loads((PROPOSAL / 'manifest.json').read_text())
        patch_file = PROPOSAL / 'candidate.patch'
        self.assertEqual(hashlib.sha256(patch_file.read_bytes()).hexdigest(), manifest['patch_sha256'])
        for name, identities in manifest['files'].items():
            if identities['base_sha256']:
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                                 identities['base_sha256'], name)
            else:
                self.assertFalse((ROOT / name).exists(), 'candidate must remain inactive')
        with tempfile.TemporaryDirectory(prefix='phase2-proposal-') as directory:
            target = Path(directory)
            for name in ('src', 'tests', 'scripts', 'evals'):
                shutil.copytree(ROOT / name, target / name, ignore=shutil.ignore_patterns('__pycache__'))
            for path in ROOT.glob('*.md'):
                shutil.copyfile(path, target / path.name)
            result = subprocess.run(['git', 'apply', '--check', str(patch_file)], cwd=target,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['git', 'apply', str(patch_file)], cwd=target, check=True)
            for name, identities in manifest['files'].items():
                self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(),
                                 identities['candidate_sha256'], name)
            code = '''
import sys, unittest
def deny_network(event, arguments):
    if event in ('socket.connect', 'socket.getaddrinfo', 'urllib.Request'):
        raise AssertionError('live network prohibited in offline candidate tests')
sys.addaudithook(deny_network)
unittest.main(module='tests.test_phase2_schema_candidate', verbosity=2)
'''
            result = subprocess.run([sys.executable, '-c', code], cwd=target,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Ran 6 tests', result.stderr)


if __name__ == '__main__':
    unittest.main()
