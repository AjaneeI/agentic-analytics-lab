#!/usr/bin/env python3
"""Report whether System Benchmark development interfaces are ready to freeze."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.system_benchmark.freeze_audit import audit_development_freeze
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references


def main() -> int:
    root = Path.cwd()
    audit = audit_development_freeze(
        load_tasks(root / "evals/system_benchmark/development_tasks.json"),
        load_references(root / "evals/system_benchmark/development_references.json"),
    )
    print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    return 0 if audit.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
