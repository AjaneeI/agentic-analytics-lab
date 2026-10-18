"""Independent evidence checks: altered records must not validate successfully."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import validate_statistical_calibration as validation


ROOT = Path(__file__).resolve().parents[1]
PRESERVED = ROOT / 'experiments/phase4-calibration-20261017/existing-interval-simulation.json'


class TestCalibrationValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preserved = json.loads(PRESERVED.read_text())

    def test_preserved_summary_recomputes_all_trials_without_bootstrap(self):
        result = validation.validate_report(self.preserved, root=ROOT)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['checked_trials'], 3000)
        self.assertEqual(result['unique_seeds'], 6000)
        self.assertEqual(result['scenarios'][6]['summary']['coverage']['count'], 237)
        self.assertEqual(result['scenarios'][7]['summary']['coverage']['count'], 97)
        self.assertEqual(result['scenarios'][8]['summary']['zero_width_count'], 73)
        self.assertIsNone(result['scenarios'][9]['summary']['two_sided_null_false_positive'])

    def test_summary_tampering_is_detected(self):
        report = copy.deepcopy(self.preserved)
        report['scenarios'][0]['summary']['coverage']['count'] += 1
        result = validation.validate_report(report, root=ROOT)
        self.assertFalse(result['valid'])
        self.assertTrue(any('coverage.count' in error for error in result['errors']))

    def test_trial_flags_width_and_seed_tampering_are_detected(self):
        for field, value in [('covers_truth', False), ('width', 0.0), ('bootstrap_seed', 1)]:
            with self.subTest(field=field):
                report = copy.deepcopy(self.preserved)
                report['scenarios'][0]['trials'][0][field] = value
                result = validation.validate_report(report, root=ROOT)
                self.assertFalse(result['valid'])
                self.assertTrue(any(field in error for error in result['errors']))

    def test_stored_estimate_is_reconstructed_from_seed_not_trusted(self):
        report = copy.deepcopy(self.preserved)
        report['scenarios'][0]['trials'][0]['estimate'] = 0.0
        report['scenarios'][0]['summary']['mean_estimate'] = 0.0
        result = validation.validate_report(report, root=ROOT)
        self.assertFalse(result['valid'])
        self.assertTrue(any('trials[0].estimate' in error for error in result['errors']))

    def test_invalid_endpoints_and_false_nonzero_null_label_are_detected(self):
        for endpoint in [float('nan'), float('inf'), -2.0]:
            with self.subTest(endpoint=endpoint):
                report = copy.deepcopy(self.preserved)
                report['scenarios'][0]['trials'][0]['interval'][0] = endpoint
                self.assertFalse(validation.validate_report(report, root=ROOT)['valid'])
        report = copy.deepcopy(self.preserved)
        report['scenarios'][-1]['summary']['two_sided_null_false_positive'] = {'rate': 0.51}
        self.assertFalse(validation.validate_report(report, root=ROOT)['valid'])

    def test_source_digest_drift_is_detected(self):
        report = copy.deepcopy(self.preserved)
        report['implementation_sha256'] = '0' * 64
        result = validation.validate_report(report, root=ROOT)
        self.assertFalse(result['valid'])
        self.assertTrue(any('implementation_sha256' in error for error in result['errors']))

    def test_claim_boundary_and_implementation_labels_cannot_be_rewritten(self):
        for field, value in [('status', 'methodology_approved'),
                             ('implementation', 'paired_repeat_bootstrap')]:
            with self.subTest(field=field):
                report = copy.deepcopy(self.preserved)
                report[field] = value
                result = validation.validate_report(report, root=ROOT)
                self.assertFalse(result['valid'])
                self.assertTrue(any(field in error for error in result['errors']))

    def test_all_replayed_dependency_cases_have_hand_checked_extremes(self):
        scenario = {'baseline_probabilities': [0.0, 0.0],
                    'candidate_probabilities': [1.0, 1.0], 'repeats': 3}
        for dependence in ['independent', 'paired', 'antithetic', 'family', 'run']:
            with self.subTest(dependence=dependence):
                self.assertEqual(validation.replay_estimate(dict(scenario, dependence=dependence), 7), 1.0)
        scenario = {'baseline_probabilities': [0.5] * 2,
                    'candidate_probabilities': [0.5] * 2, 'repeats': 3, 'dependence': 'paired'}
        self.assertEqual(validation.replay_estimate(scenario, 17), 0.0)

    def test_cli_writes_distinct_report_and_refuses_overwriting_input(self):
        before = hashlib.sha256(PRESERVED.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'validation.json'
            command = [sys.executable, str(ROOT / 'scripts/validate_statistical_calibration.py'),
                       '--input', str(PRESERVED), '--output', str(output)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(output.read_text())
            self.assertTrue(result['valid'])
            self.assertEqual(result['input_sha256'], before)
            output_before = output.read_bytes()
            refused_existing = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(refused_existing.returncode, 0)
            self.assertEqual(output.read_bytes(), output_before)
            refused = subprocess.run(command[:-1] + [str(PRESERVED)], cwd=ROOT,
                                     capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(hashlib.sha256(PRESERVED.read_bytes()).hexdigest(), before)

    def test_cli_returns_failure_and_preserves_errors_for_corrupted_evidence(self):
        report = copy.deepcopy(self.preserved)
        report['scenarios'][0]['summary']['coverage']['count'] = 0
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'corrupted.json'
            output = Path(directory) / 'validation.json'
            source.write_text(json.dumps(report))
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_statistical_calibration.py'),
                                  '--input', str(source), '--output', str(output)],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            result = json.loads(output.read_text())
            self.assertFalse(result['valid'])
            self.assertTrue(any('coverage.count' in error for error in result['errors']))

    def test_import_does_not_load_calibration_production_or_runtime(self):
        run = subprocess.run([sys.executable, '-c',
            "import sys; import scripts.validate_statistical_calibration; "
            "assert not any(n.startswith(('src', 'scripts.calibrate_statistical_interval', "
            "'requests', 'httpx', 'openai')) for n in sys.modules)"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
