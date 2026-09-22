"""Run three matched oracle-metadata routed benchmark passes."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path


PREFLIGHT_SCRIPT = Path("scripts/preflight_benchmark_env.py")
EVAL_SCRIPT = Path("scripts/run_oracle_metadata_routed_eval.py")
SUMMARIZE_SCRIPT = Path("scripts/summarize_repeatability.py")
RAW_RESULT = Path(
    "experiments/results/oracle_metadata_routed_v0_qwen2.5_7b.json"
)
SUMMARY_OUTPUT = Path(
    "docs/generated/oracle-metadata-routed-v0-repeatability-summary.md"
)
RUN_COUNT = 3


Runner = Callable[[Path, list[str]], None]
CopyFn = Callable[[Path, Path], Path]
OutputFn = Callable[[str], None]


def run_python_script(script: Path, args: list[str]) -> None:
    subprocess.run([sys.executable, str(script), *args], check=True)


def preserved_run_paths() -> list[Path]:
    return [
        Path(
            "experiments/results/"
            f"oracle_metadata_routed_v0_qwen2.5_7b_run{index}.json"
        )
        for index in range(1, RUN_COUNT + 1)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run preflight, three oracle-metadata routed benchmark passes, "
            "and a repeatability summary."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing preserved routed run files.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=SUMMARY_OUTPUT,
        help=f"Destination Markdown path (default: {SUMMARY_OUTPUT}).",
    )
    return parser.parse_args()


def run_oracle_routed_repeatability_pass(
    *,
    force: bool = False,
    raw_result: Path = RAW_RESULT,
    run_outputs: Sequence[Path] | None = None,
    summary_output: Path = SUMMARY_OUTPUT,
    runner: Runner = run_python_script,
    copy_fn: CopyFn = shutil.copy2,
    output_fn: OutputFn = print,
) -> int:
    preserved_outputs = list(run_outputs or preserved_run_paths())

    existing = [path for path in preserved_outputs if path.exists()]
    if existing and not force:
        joined = ", ".join(str(path) for path in existing)
        output_fn(
            "FAIL: Refusing to overwrite preserved routed run file(s): "
            f"{joined}. Use --force to overwrite safely."
        )
        return 1

    output_fn("Running benchmark preflight...")
    try:
        runner(PREFLIGHT_SCRIPT, [])
    except subprocess.CalledProcessError as exc:
        output_fn(f"FAIL: Preflight failed (exit code {exc.returncode}).")
        return exc.returncode or 1

    for index, destination in enumerate(preserved_outputs, start=1):
        output_fn(
            f"Running oracle-metadata routed benchmark pass {index}/{RUN_COUNT}..."
        )
        try:
            runner(EVAL_SCRIPT, [])
        except subprocess.CalledProcessError as exc:
            output_fn(
                f"FAIL: Routed benchmark run {index} failed "
                f"(exit code {exc.returncode})."
            )
            return exc.returncode or 1

        if not raw_result.exists():
            output_fn(
                "FAIL: Expected routed benchmark result was not produced: "
                f"{raw_result}"
            )
            return 1

        destination.parent.mkdir(parents=True, exist_ok=True)
        if force and destination.exists():
            destination.unlink()
        copy_fn(raw_result, destination)
        output_fn(f"Preserved routed run {index}: {destination}")

    output_fn("Generating routed repeatability summary...")
    try:
        runner(
            SUMMARIZE_SCRIPT,
            [str(path) for path in preserved_outputs]
            + [
                "--output",
                str(summary_output),
                "--title",
                "Oracle-Metadata Routed Repeatability Summary",
            ],
        )
    except subprocess.CalledProcessError as exc:
        output_fn(
            f"FAIL: Routed repeatability summary failed "
            f"(exit code {exc.returncode})."
        )
        return exc.returncode or 1

    output_fn(f"Routed repeatability summary generated: {summary_output}")
    output_fn(
        "SUCCESS: Oracle-metadata routed three-run repeatability pass completed."
    )
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(
        run_oracle_routed_repeatability_pass(
            force=args.force,
            summary_output=args.summary_output,
        )
    )


if __name__ == "__main__":
    main()
