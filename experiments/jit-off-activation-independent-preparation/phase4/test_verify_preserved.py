"""Offline regression tests for the endpoint-only independent audit."""
import copy
import json
from pathlib import Path
import socket
import unittest


def denied(*args, **kwargs):
    raise AssertionError('Network/DNS access forbidden in this audit')


socket.socket = denied
socket.create_connection = denied
socket.getaddrinfo = denied
import verify_preserved as audit

ROOT = next(p / 'work' / 'phase4' for p in Path(__file__).resolve().parents if (p / 'work' / 'phase4' / 'AGENTS.md').is_file())
SOURCE = ROOT / 'experiments/phase4-calibration-20261017/existing-interval-simulation.json'


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(SOURCE.read_text())

    def test_preserved_all_scenarios_and_trials(self):
        result = audit.verify(self.original, ROOT)
        self.assertEqual([], result['errors'])
        self.assertEqual(3000, result['checked_trials'])
        self.assertEqual(6000, result['unique_seeds'])
        self.assertEqual(10, len(result['scenarios']))
        positive = result['scenarios'][-1]
        self.assertIsNone(positive['summary']['two_sided_null_false_positive'])
        self.assertIsNone(positive['summary']['positive_null_false_positive'])

    def test_wilson_zero_and_all_events_not_degenerate(self):
        zero = audit.rate(0, 300)
        full = audit.rate(300, 300)
        self.assertEqual(0, zero['mc_wilson_95_interval'][0])
        self.assertGreater(zero['mc_wilson_95_interval'][1], 0)
        self.assertEqual(1, full['mc_wilson_95_interval'][1])
        self.assertLess(full['mc_wilson_95_interval'][0], 1)
        self.assertAlmostEqual(zero['mc_wilson_95_interval'][1], 1-full['mc_wilson_95_interval'][0])

    def test_wilson_bounds_satisfy_score_equation(self):
        for k in (1, 63, 150, 203, 299):
            bounds = audit.rate(k, 300)['mc_wilson_95_interval']
            for p in bounds:
                score = (k-300*p)**2/(300*p*(1-p))
                self.assertAlmostEqual(score, audit.Z2, places=10)

    def test_corrupted_flags_widths_summary_seeds_and_truth_are_detected(self):
        mutations = [
            lambda d: d['scenarios'][0]['trials'][0].update(covers_truth=False),
            lambda d: d['scenarios'][0]['trials'][0].update(width=9),
            lambda d: d['scenarios'][0]['summary']['coverage'].update(count=1),
            lambda d: d['scenarios'][0]['trials'][0].update(data_seed=0),
            lambda d: d['scenarios'][0].update(true_effect=.2),
            lambda d: d['scenarios'][-1]['summary'].update(two_sided_null_false_positive={}),
            lambda d: d.update(implementation_sha256='wrong'),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(self.original)
                mutation(changed)
                self.assertTrue(audit.verify(changed, ROOT)['errors'])

    def test_reversed_or_nonfinite_endpoints_rejected(self):
        for interval in ([1,-1], [float('nan'),.2], [-2,.2]):
            changed = copy.deepcopy(self.original)
            changed['scenarios'][0]['trials'][0]['interval'] = interval
            with self.assertRaises(ValueError):
                audit.verify(changed, ROOT)

    def test_no_repository_runtime_or_random_imports(self):
        import sys
        self.assertFalse(any(k == 'src' or k.startswith('src.') for k in sys.modules))
        # Independent audit never draws outcomes or bootstrap samples.
        self.assertNotIn('random', audit.__dict__)

    def test_original_is_not_mutated(self):
        before = copy.deepcopy(self.original)
        audit.verify(self.original, ROOT)
        self.assertEqual(before, self.original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
