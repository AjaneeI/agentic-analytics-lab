"""Inactive synthetic metadata eligibility only; never computes a scientific estimate.

The caller supplies the host-owned exact target. This module does not establish
host ownership, scientific approval, provenance, or actual runtime pairing.
"""
from collections import Counter
import math

IDENTITY = ('task_id', 'task_version', 'family', 'arm', 'repeat_id', 'block_id')
EXPECTED_FIELDS = set(IDENTITY) | {'n_family', 'synthetic', 'metadata_approved'}
OBSERVED_FIELDS = set(IDENTITY) | {'status', 'scored', 'success'}
TIMEOUT_FIELDS = {'elapsed_seconds', 'stage', 'artifact_available'}
STATUSES = ('not_started', 'started_timeout', 'transport_error', 'worker_error',
            'contract_error', 'scorer_error', 'scored_success', 'scored_failure')


def _finite_nonnegative_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except (OverflowError, ValueError):
        return False


def _identity(row):
    if not isinstance(row, dict) or not set(IDENTITY) <= row.keys():
        return None
    for key in ('task_id', 'task_version', 'family', 'arm', 'block_id'):
        if type(row[key]) is not str or not row[key].strip():
            return None
    if row['family'] not in 'ABCDEFGH' or len(row['family']) != 1:
        return None
    if row['arm'] not in ('baseline', 'candidate'):
        return None
    if type(row['repeat_id']) is not int or row['repeat_id'] <= 0:
        return None
    return tuple(row[k] for k in IDENTITY)


def evaluate_metadata(expected: list[dict], observed: list[dict]) -> dict:
    """Validate complete approved *synthetic* A-H metadata without scoring it.

    `eligible_for_primary` means this draft's metadata conditions hold, not that
    any actual analysis, scientific method or live execution has been accepted.
    Invalid, missing, duplicate, unmatched and unscored outcomes withhold it.
    All inputs are preserved. Missing values are never imputed or replaced.
    """
    reasons = []
    target, actual = {}, {}
    status_counts = Counter()
    scored_count = unscored_count = 0
    if type(expected) is not list or not expected:
        reasons.append('invalid_or_empty_expected_list')
        expected = []
    if type(observed) is not list:
        reasons.append('invalid_observed_list')
        observed = []
    for index, row in enumerate(expected):
        identity = _identity(row)
        if identity is None or set(row) != EXPECTED_FIELDS:
            reasons.append(f'invalid_expected_row:{index}')
            continue
        if (row['synthetic'] is not True or row['metadata_approved'] is not True or
                type(row['n_family']) is not int or row['n_family'] <= 0):
            reasons.append(f'unapproved_or_invalid_synthetic_metadata:{index}')
            continue
        if identity in target:
            reasons.append(f'duplicate_expected_identity:{index}')
        target[identity] = row
    # A task cannot change family/version, and each expected task-repeat must
    # contain both arms in the identical prospective block.
    tasks, pairs, families = {}, {}, {}
    for identity, row in target.items():
        task = row['task_id']
        signature = (row['family'], row['task_version'], row['n_family'])
        if task in tasks and tasks[task] != signature:
            reasons.append(f'inconsistent_task_metadata:{task}')
        tasks[task] = signature
        families.setdefault(row['family'], set()).add(task)
        pair = pairs.setdefault((task, row['repeat_id']), {})
        if row['arm'] in pair:
            reasons.append(f'duplicate_expected_task_arm_repeat:{task}:{row["repeat_id"]}')
        pair[row['arm']] = row['block_id']
    if set(families) != set('ABCDEFGH'):
        reasons.append('incomplete_A_H_families')
    for task, (family, version, count) in tasks.items():
        if count != len(families[family]):
            reasons.append(f'invalid_n_family:{task}')
    for pair_id, arms in pairs.items():
        if set(arms) != {'baseline', 'candidate'} or len(set(arms.values())) != 1:
            reasons.append(f'unmatched_expected_pair:{pair_id[0]}:{pair_id[1]}')
    for index, row in enumerate(observed):
        identity = _identity(row)
        if identity is None:
            reasons.append(f'invalid_observed_identity:{index}')
            continue
        if identity in actual:
            reasons.append(f'duplicate_observed_identity:{index}')
        actual[identity] = row
        if identity not in target:
            reasons.append(f'unknown_or_unmatched_observed_identity:{index}')
        status = row.get('status')
        if type(status) is not str or status not in STATUSES:
            reasons.append(f'invalid_status:{index}')
            continue
        status_counts[status] += 1
        allowed = OBSERVED_FIELDS | (TIMEOUT_FIELDS if status == 'started_timeout' else set())
        if set(row) != allowed or type(row.get('scored')) is not bool or 'success' not in row:
            reasons.append(f'invalid_observed_fields:{index}')
            continue
        if status == 'started_timeout':
            elapsed = row['elapsed_seconds']
            if (not _finite_nonnegative_number(elapsed) or
                    type(row['stage']) is not str or not row['stage'].strip() or
                    type(row['artifact_available']) is not bool or
                    (row['scored'] and not row['artifact_available'])):
                reasons.append(f'invalid_timeout_metadata:{index}')
        if row['scored']:
            scored_count += 1
            if type(row['success']) is not bool:
                reasons.append(f'scored_outcome_not_boolean:{index}')
            if status not in ('scored_success', 'scored_failure', 'started_timeout'):
                reasons.append(f'status_score_contradiction:{index}')
            if status == 'scored_success' and row['success'] is not True:
                reasons.append(f'status_score_contradiction:{index}')
            if status == 'scored_failure' and row['success'] is not False:
                reasons.append(f'status_score_contradiction:{index}')
        else:
            unscored_count += 1
            reasons.append(f'unscored_required_outcome:{index}')
            if row['success'] is not None or status in ('scored_success', 'scored_failure'):
                reasons.append(f'status_score_contradiction:{index}')
    missing = set(target) - set(actual)
    if missing:
        reasons.append(f'missing_required_outcomes:{len(missing)}')
    valid = not reasons
    weights = {task: {'numerator': 1, 'denominator': 8 * count}
               for task, (family, version, count) in sorted(tasks.items())} if valid else {}
    return {'contract_version': 'inactive-synthetic-metadata-v2', 'inactive': True,
            'live_qualified': False, 'metadata_valid': valid, 'eligible_for_primary': valid,
            'aggregate': None, 'weights': weights, 'reasons': sorted(set(reasons)),
            'expected_count': len(expected), 'observed_count': len(observed),
            'scored_count': scored_count, 'unscored_count': unscored_count,
            'missing_count': len(missing), 'status_counts': dict(sorted(status_counts.items())),
            'new_attempts': 0}
