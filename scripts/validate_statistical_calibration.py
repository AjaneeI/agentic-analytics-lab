#!/usr/bin/env python3
"""Independently check preserved synthetic calibration records, without resampling.

No imports from the simulation script, production inference, benchmark or runtime.
Endpoints are inputs, not independently verified bootstrap outputs. This checks
their summaries and replays only seeded Bernoulli data to check point estimates.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import random
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
NUMERIC_TOLERANCE = 1e-12  # Floating-point agreement, not a calibration criterion.


def replay_estimate(scenario: dict, seed: int) -> float:
    """Reconstruct net successes from the declared RNG stream, without helpers."""
    rng = random.Random(seed)
    repeats = scenario['repeats']
    dependence = scenario['dependence']
    net_successes = 0
    shared = {}
    for task, (base_p, candidate_p) in enumerate(zip(
        scenario['baseline_probabilities'], scenario['candidate_probabilities']
    )):
        if dependence in ('family', 'run'):
            group = task // 3 if dependence == 'family' else 0
            if group not in shared:
                shared[group] = [[rng.random() for _ in range(repeats)] for _ in range(2)]
            baseline_draws, candidate_draws = shared[group]
        else:
            baseline_draws = [rng.random() for _ in range(repeats)]
            if dependence == 'paired':
                candidate_draws = baseline_draws
            elif dependence == 'antithetic':
                candidate_draws = [1 - draw for draw in baseline_draws]
            else:
                candidate_draws = [rng.random() for _ in range(repeats)]
        net_successes += sum(draw < candidate_p for draw in candidate_draws)
        net_successes -= sum(draw < base_p for draw in baseline_draws)
    return net_successes / (repeats * len(scenario['baseline_probabilities']))


def _rate(events: int, trials: int) -> dict:
    """Invert the binomial score inequality for outer-simulation uncertainty."""
    rate = events / trials
    z_squared = NormalDist().inv_cdf(0.975) ** 2
    # Roots of (n+z²)p² - (2k+z²)p + k²/n <= 0.
    a = trials + z_squared
    b = -(2 * events + z_squared)
    discriminant = z_squared * (z_squared + 4 * events * (1 - rate))
    radius = math.sqrt(discriminant)
    return {
        'count': events, 'trials': trials, 'rate': rate,
        'mc_standard_error': math.sqrt(events * (trials - events) / trials ** 3),
        'mc_wilson_95_interval': [max(0.0, (-b - radius) / (2 * a)),
                                  min(1.0, (-b + radius) / (2 * a))],
    }


def validate_report(report: dict, *, root: Path = ROOT) -> dict:
    """Return all disagreements; never mutate the evidence or call inference."""
    errors = []
    result = {
        'valid': False, 'errors': errors, 'checked_trials': 0, 'unique_seeds': 0,
        'numeric_absolute_and_relative_tolerance': NUMERIC_TOLERANCE,
        'scenarios': [],
        'claim_boundary': (
            'Independent summaries of stored endpoints and seeded synthetic point '
            'estimates only. Bootstrap endpoints are not independently regenerated. '
            'No method selection, calibration acceptance, hypothesis-test approval '
            'or Phase 4/5 advancement. Monte Carlo intervals concern the preserved '
            'finite-draw simulation, not real benchmark dependence or model quality.'
        ),
    }

    def agree(actual, expected, path):
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                errors.append(f'{path}: expected object')
                return
            if actual.keys() != expected.keys():
                errors.append(f'{path}: fields differ')
            for key, value in expected.items():
                agree(actual.get(key), value, f'{path}.{key}')
        elif isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) != len(expected):
                errors.append(f'{path}: list shape differs')
                return
            for index, value in enumerate(expected):
                agree(actual[index], value, f'{path}[{index}]')
        elif type(expected) is float:
            if (type(actual) not in (int, float) or not math.isfinite(actual)
                    or not math.isclose(actual, expected, rel_tol=NUMERIC_TOLERANCE,
                                        abs_tol=NUMERIC_TOLERANCE)):
                errors.append(f'{path}: {actual!r} != recomputed {expected!r}')
        elif type(actual) is not type(expected) or actual != expected:
            errors.append(f'{path}: {actual!r} != recomputed {expected!r}')

    try:
        agree(report['status'], 'nonconfirmatory_model_free_preparation_not_methodology_approval', 'status')
        agree(report['implementation'], 'src.evals.statistical_evidence.paired_hierarchical_bootstrap',
              'implementation')
        for field, source in [
            ('implementation_sha256', 'src/evals/statistical_evidence.py'),
            ('script_sha256', 'scripts/calibrate_statistical_interval.py'),
        ]:
            agree(report[field], hashlib.sha256((root / source).read_bytes()).hexdigest(), field)
        parameters = report['parameters']
        trials = parameters['outer_trials_per_scenario']
        master_seed = parameters['master_seed']
        if type(trials) is not int or trials < 2 or type(master_seed) is not int:
            raise ValueError('invalid outer trial count or master seed')
        if type(parameters['bootstrap_samples']) is not int or parameters['bootstrap_samples'] < 100:
            raise ValueError('invalid bootstrap draw count')
        agree(parameters['scenario_seed_rule'], 'master_seed + 100000 * scenario_index',
              'parameters.scenario_seed_rule')
        agree(parameters['trial_seed_rule'], 'data=scenario_seed+2*trial; bootstrap=data+1',
              'parameters.trial_seed_rule')
        if not report['scenarios']:
            raise ValueError('no scenarios')
        seeds, names = set(), set()
        for index, stored in enumerate(report['scenarios']):
            path = f'scenarios[{index}]'
            scenario = stored['scenario']
            name = scenario['name']
            if not isinstance(name, str) or not name or name in names:
                raise ValueError(f'{path}: empty or duplicate scenario name')
            names.add(name)
            baseline = scenario['baseline_probabilities']
            candidate = scenario['candidate_probabilities']
            if not baseline or len(baseline) != len(candidate):
                raise ValueError(f'{path}: probability arrays must align and be nonempty')
            if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
                   for p in baseline + candidate):
                raise ValueError(f'{path}: invalid Bernoulli probability')
            if type(scenario['repeats']) is not int or scenario['repeats'] < 1:
                raise ValueError(f'{path}: invalid repeat count')
            if scenario['dependence'] not in ('independent', 'paired', 'antithetic', 'family', 'run'):
                raise ValueError(f'{path}: unknown dependence')
            exact_truth = sum((Fraction(str(c)) - Fraction(str(b))
                               for b, c in zip(baseline, candidate)), Fraction()) / len(baseline)
            truth = float(exact_truth)
            agree(stored['true_effect'], truth, f'{path}.true_effect')
            agree(stored['target'], 'fixed_task_equal_weight_mean_probability_difference', f'{path}.target')
            if len(stored['trials']) != trials:
                raise ValueError(f'{path}: trial count does not match parameters')
            widths, estimates = [], []
            coverage = exclusions = positives = zero_widths = 0
            for trial_index, record in enumerate(stored['trials']):
                trial_path = f'{path}.trials[{trial_index}]'
                agree(record['trial'], trial_index, f'{trial_path}.trial')
                data_seed = master_seed + 100000 * index + 2 * trial_index
                for field, expected in [('data_seed', data_seed), ('bootstrap_seed', data_seed + 1)]:
                    agree(record[field], expected, f'{trial_path}.{field}')
                    if type(record[field]) is not int or record[field] in seeds:
                        errors.append(f'{trial_path}.{field}: non-integer or duplicate seed')
                    else:
                        seeds.add(record[field])
                endpoints = record['interval']
                if (not isinstance(endpoints, list) or len(endpoints) != 2
                        or any(type(value) not in (int, float) or not math.isfinite(value)
                               for value in endpoints)
                        or not -1 <= endpoints[0] <= endpoints[1] <= 1):
                    raise ValueError(f'{trial_path}.interval: invalid endpoints')
                lower, upper = endpoints
                width = upper - lower
                covers = lower <= truth <= upper
                excludes = lower > 0 or upper < 0
                positive = lower > 0
                estimate = replay_estimate(scenario, data_seed)
                for field, value in [('width', width), ('covers_truth', covers),
                                     ('excludes_zero', excludes), ('positive_claim', positive),
                                     ('estimate', estimate)]:
                    agree(record[field], value, f'{trial_path}.{field}')
                widths.append(width)
                estimates.append(estimate)
                coverage += covers
                exclusions += excludes
                positives += positive
                zero_widths += width == 0
                result['checked_trials'] += 1
            average_width = math.fsum(widths) / trials
            width_se = math.sqrt(math.fsum((width - average_width) ** 2 for width in widths)
                                 / (trials * (trials - 1)))
            summary = {
                'coverage': _rate(coverage, trials),
                'two_sided_null_false_positive': _rate(exclusions, trials) if exact_truth == 0 else None,
                'positive_null_false_positive': _rate(positives, trials) if exact_truth == 0 else None,
                'zero_exclusion_rate': _rate(exclusions, trials),
                'mean_width': average_width, 'width_mc_standard_error': width_se,
                'mean_width_mc_normal_95_interval': [average_width - 1.96 * width_se,
                                                     average_width + 1.96 * width_se],
                'zero_width_count': zero_widths,
                'mean_estimate': math.fsum(estimates) / trials,
            }
            agree(stored['summary'], summary, f'{path}.summary')
            result['scenarios'].append({'name': name, 'true_effect': truth, 'summary': summary})
        result['unique_seeds'] = len(seeds)
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as error:
        errors.append(f'invalid evidence: {error}')
    result['valid'] = not errors
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('output must differ from the preserved input')
    if args.output.exists():
        parser.error('output already exists; choose a new validation artifact')
    raw = args.input.read_bytes()
    result = validate_report(json.loads(raw))
    result.update({
        'input_sha256': hashlib.sha256(raw).hexdigest(),
        'validator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python_version': platform.python_version(),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(f"valid={result['valid']} trials={result['checked_trials']} seeds={result['unique_seeds']}")
    for error in result['errors']:
        print(error)
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
