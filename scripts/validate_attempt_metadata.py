#!/usr/bin/env python3
"""Manually validate one proposed metadata JSON file, offline and read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.attempt_metadata import CLAIM_BOUNDARY, validate_attempt_metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors = [{"path": "input", "code": "unreadable_or_invalid_json"}]
    else:
        errors = validate_attempt_metadata(payload)
    print(json.dumps({"valid": not errors, "errors": errors, "claim_boundary": CLAIM_BOUNDARY}, sort_keys=True))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
