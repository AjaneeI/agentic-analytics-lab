import unittest
import subprocess
import sys

from scripts import calibrate_statistical_interval as calibration


class TestStatisticalCalibration(unittest.TestCase):
    def test_wilson_interval_retains_uncertainty_at_boundaries(self):
        lower, upper = calibration.wilson_interval(0, 100)
        self.assertAlmostEqual(lower, 0.0)
        self.assertGreater(upper, 0.03)
        lower, upper = calibration.wilson_interval(100, 100)
        self.assertLess(lower, 0.97)
        self.assertAlmostEqual(upper, 1.0)

    def test_paired_and_clustered_generators_preserve_dependence(self):
        scenarios = {item.name: item for item in calibration.SCENARIOS}
        baseline, candidate = calibration.generate_outcomes(
            scenarios['perfect_pairing'], 12
        )
        self.assertEqual(baseline, candidate)
        baseline, _ = calibration.generate_outcomes(scenarios['run_shock'], 12)
        self.assertTrue(all(row == baseline[0] for row in baseline))
        baseline, _ = calibration.generate_outcomes(scenarios['family_shock'], 12)
        self.assertEqual(baseline[0], baseline[1])
        self.assertEqual(baseline[1], baseline[2])

    def test_trial_replays_existing_implementation_exactly(self):
        scenario = calibration.SCENARIOS[0]
        report = calibration.calibrate(scenario, trials=2, samples=100, seed=17)
        first = report['trials'][0]
        baseline, candidate = calibration.generate_outcomes(
            scenario, first['data_seed']
        )
        from src.evals.statistical_evidence import paired_hierarchical_bootstrap
        expected = paired_hierarchical_bootstrap(
            baseline, candidate, samples=100, seed=first['bootstrap_seed']
        )
        self.assertEqual(first['interval'], [expected['lower_95'], expected['upper_95']])
        self.assertEqual(report, calibration.calibrate(
            scenario, trials=2, samples=100, seed=17
        ))

    def test_known_nonzero_truth_is_not_reported_as_null_false_positive(self):
        scenario = next(item for item in calibration.SCENARIOS if item.name == 'positive_effect')
        report = calibration.calibrate(scenario, trials=2, samples=100, seed=17)
        self.assertAlmostEqual(report['true_effect'], 0.2)
        self.assertIsNone(report['summary']['two_sided_null_false_positive'])
        self.assertIsNotNone(report['summary']['coverage'])

    def test_invalid_precision_budget_rejected(self):
        with self.assertRaises(ValueError):
            calibration.calibrate(calibration.SCENARIOS[0], trials=0, samples=100, seed=1)
        with self.assertRaises(ValueError):
            calibration.calibrate(calibration.SCENARIOS[0], trials=2, samples=99, seed=1)

    def test_deterministic_truth_has_exact_interval_and_counts(self):
        scenario = calibration.Scenario('deterministic', (0.0, 0.0), (1.0, 1.0))
        report = calibration.calibrate(scenario, trials=3, samples=100, seed=1)
        self.assertEqual(report['true_effect'], 1.0)
        self.assertEqual(report['summary']['coverage']['count'], 3)
        self.assertEqual(report['summary']['zero_width_count'], 3)
        self.assertEqual(report['summary']['zero_exclusion_rate']['count'], 3)
        self.assertTrue(all(item['interval'] == [1.0, 1.0] for item in report['trials']))

    def test_import_does_not_load_agent_model_or_tool_runtime(self):
        result = subprocess.run(
            [sys.executable, '-c',
             "import sys; import scripts.calibrate_statistical_interval; "
             "assert not any(n.startswith(('src.agents', 'src.tools', 'src.routing', "
             "'src.evals.system_benchmark', 'requests', 'httpx', 'openai')) "
             "for n in sys.modules)"],
            cwd=calibration.ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
