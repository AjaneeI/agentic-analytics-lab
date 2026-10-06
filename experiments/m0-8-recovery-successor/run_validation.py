#!/usr/bin/env python3
"""Run the single preregistered M0.8 recovery successor."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")
PREVIOUS_RUNNER = (
    ROOT
    / "experiments"
    / "m0-8-final-bounded-validation"
    / "run_validation.py"
)


def _load_previous():
    spec = importlib.util.spec_from_file_location("m0_8_original_runner", PREVIOUS_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = _load_previous()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.verify_only:
        print(
            json.dumps(
                previous.m0_6.previous.verify_frozen_state(root, manifest),
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --verify-only is used")
    return previous.run_once(root, args.output_dir.resolve(), manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
