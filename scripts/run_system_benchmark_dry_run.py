#!/usr/bin/env python3
"""Run the seven scripted development controls without a model or live database."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evals.system_benchmark.dry_run import run_rehearsal
from src.evals.system_benchmark.execution import canonical_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-faults', action='store_true', help='Exercise explicitly labelled negative controls')
    parser.add_argument('--output', type=Path, help='New JSON file; existing files are never overwritten')
    args = parser.parse_args()
    try:
        report = run_rehearsal(include_faults=args.include_faults)
        serialized = canonical_json(report)
        if args.output is None:
            sys.stdout.write(serialized)
        else:
            with args.output.open('x', encoding='utf-8', newline='\n') as destination:
                destination.write(serialized)
        return 0 if report['rehearsal_passed'] else 1
    except (ValueError, OSError) as exc:
        print(f'Dry-run failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
