#!/usr/bin/env python3
"""Model-free diagnostics of the EXISTING interval; no proposed inference change.

Uses only generated Boolean matrices, the existing statistical helper and Python's
standard library. Never loads benchmark tasks, model/runtime code or held-out data.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import random
from statistics import mean, stdev
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evals.statistical_evidence import paired_hierarchical_bootstrap


@dataclass(frozen=True)
class Scenario:
    name: str
    baseline_probabilities: tuple[float, ...]
    candidate_probabilities: tuple[float, ...]
    dependence: str = 'independent'
    repeats: int = 3


SCENARIOS = (
    Scenario('small_independent', (0.5,) * 6, (0.5,) * 6),
    Scenario('independent', (0.5,) * 24, (0.5,) * 24),
    Scenario('perfect_pairing', (0.5,) * 24, (0.5,) * 24, 'paired'),
    Scenario('negative_pairing', (0.5,) * 24, (0.5,) * 24, 'antithetic'),
    Scenario('heterogeneous_difficulty', tuple(p for p in (.1, .2, .3, .4, .6, .7, .8, .9) for _ in range(3)), tuple(p for p in (.1, .2, .3, .4, .6, .7, .8, .9) for _ in range(3))),
    Scenario('heterogeneous_effect', (.2,) * 12 + (.8,) * 12, (.8,) * 12 + (.2,) * 12),
    Scenario('family_shock', (0.5,) * 24, (0.5,) * 24, 'family'),
    Scenario('run_shock', (0.5,) * 24, (0.5,) * 24, 'run'),
    Scenario('near_ceiling', (.99,) * 24, (.99,) * 24),
    Scenario('positive_effect', (.5,) * 24, (.7,) * 24),
)


def wilson_interval(successes: int, count: int) -> list[float]:
    """95% Wilson binomial interval for OUTER Monte Carlo uncertainty only."""
    z = 1.959963984540054
    proportion = successes / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def generate_outcomes(scenario: Scenario, seed: int) -> tuple[list[list[bool]], list[list[bool]]]:
    """Generate fixed-task Bernoulli outcomes with declared dependence."""
    rng = random.Random(seed)
    baseline, candidate = [], []
    cluster_draws = {}
    for task, (p_baseline, p_candidate) in enumerate(zip(scenario.baseline_probabilities, scenario.candidate_probabilities)):
        if scenario.dependence in ('family', 'run'):
            cluster = task // 3 if scenario.dependence == 'family' else 0
            if cluster not in cluster_draws:
                cluster_draws[cluster] = (
                    [rng.random() for _ in range(scenario.repeats)],
                    [rng.random() for _ in range(scenario.repeats)],
                )
            draw_baseline, draw_candidate = cluster_draws[cluster]
        else:
            draw_baseline = [rng.random() for _ in range(scenario.repeats)]
            if scenario.dependence == 'paired':
                draw_candidate = draw_baseline
            elif scenario.dependence == 'antithetic':
                draw_candidate = [1 - value for value in draw_baseline]
            else:
                draw_candidate = [rng.random() for _ in range(scenario.repeats)]
        baseline.append([draw < p_baseline for draw in draw_baseline])
        candidate.append([draw < p_candidate for draw in draw_candidate])
    return baseline, candidate


def calibrate(scenario: Scenario, *, trials: int, samples: int, seed: int) -> dict:
    if trials < 2 or samples < 100:
        raise ValueError('Require at least two outer trials and 100 bootstrap samples.')
    truth = mean(c - b for b, c in zip(scenario.baseline_probabilities, scenario.candidate_probabilities))
    # Exact symmetry in heterogeneous_effect is mathematical zero, despite fp noise.
    if abs(truth) < 1e-12:
        truth = 0.0
    outcomes = []
    for trial in range(trials):
        data_seed = seed + 2 * trial
        bootstrap_seed = seed + 2 * trial + 1
        baseline, candidate = generate_outcomes(scenario, data_seed)
        interval = paired_hierarchical_bootstrap(baseline, candidate, samples=samples, seed=bootstrap_seed)
        lower, upper = interval['lower_95'], interval['upper_95']
        estimate = mean(mean(c) - mean(b) for b, c in zip(baseline, candidate))
        outcomes.append({
            'trial': trial, 'data_seed': data_seed, 'bootstrap_seed': bootstrap_seed,
            'estimate': estimate, 'interval': [lower, upper], 'width': upper - lower,
            'covers_truth': lower <= truth <= upper,
            'excludes_zero': lower > 0 or upper < 0,
            'positive_claim': lower > 0,
        })

    def proportion(field):
        count = sum(item[field] for item in outcomes)
        rate = count / trials
        return {'count': count, 'trials': trials, 'rate': rate,
                'mc_standard_error': math.sqrt(rate * (1 - rate) / trials),
                'mc_wilson_95_interval': wilson_interval(count, trials)}

    widths = [item['width'] for item in outcomes]
    width_se = stdev(widths) / math.sqrt(trials)
    return {
        'scenario': asdict(scenario), 'true_effect': truth,
        'target': 'fixed_task_equal_weight_mean_probability_difference',
        'summary': {
            'coverage': proportion('covers_truth'),
            'two_sided_null_false_positive': proportion('excludes_zero') if truth == 0 else None,
            'positive_null_false_positive': proportion('positive_claim') if truth == 0 else None,
            'zero_exclusion_rate': proportion('excludes_zero'),
            'mean_width': mean(widths), 'width_mc_standard_error': width_se,
            'mean_width_mc_normal_95_interval': [mean(widths) - 1.96 * width_se, mean(widths) + 1.96 * width_se],
            'zero_width_count': sum(width == 0 for width in widths),
            'mean_estimate': mean(item['estimate'] for item in outcomes),
        },
        'trials': outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=300)
    parser.add_argument('--bootstrap-samples', type=int, default=500)
    parser.add_argument('--seed', type=int, default=20261017)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {
        'status': 'nonconfirmatory_model_free_preparation_not_methodology_approval',
        'implementation': 'src.evals.statistical_evidence.paired_hierarchical_bootstrap',
        'implementation_sha256': hashlib.sha256((ROOT / 'src/evals/statistical_evidence.py').read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python_version': platform.python_version(),
        'parameters': {'outer_trials_per_scenario': args.trials, 'bootstrap_samples': args.bootstrap_samples, 'master_seed': args.seed,
                       'scenario_seed_rule': 'master_seed + 100000 * scenario_index',
                       'trial_seed_rule': 'data=scenario_seed+2*trial; bootstrap=data+1'},
        'claim_boundary': 'Synthetic fixed-task diagnostics only. No model calls or benchmark/held-out access. Interval exclusion is a diagnostic, not an approved hypothesis test. Monte Carlo uncertainty does not include model misspecification or bootstrap discretization.',
        'scenarios': [],
    }
    for index, scenario in enumerate(SCENARIOS):
        result = calibrate(scenario, trials=args.trials, samples=args.bootstrap_samples, seed=args.seed + 100000 * index)
        report['scenarios'].append(result)
        print(f"{scenario.name}: coverage={result['summary']['coverage']['rate']:.3f} width={result['summary']['mean_width']:.3f}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
