# Phase 2: SB-D01 Treatment A continuation (2026-10-12)

## Status and authorization

**Prepared, not executed. Phase 2 remains active and incomplete.**

The current authorization is one Treatment A run for [issue #73](https://github.com/AjaneeI/agentic-analytics-lab/issues/73), using `BoundedLocalExecutor` and the existing deterministic scorer, followed by evidence preservation and a stop. No Treatment B run, retry, prompt tuning, SQL normalization, guard relaxation, held-out work, or additional worker is included.

The actual run requires Ajanee's existing Mac/Ollama/ClickHouse environment. The preparation session was a Linux workspace without that Mac path, Ollama/Docker executables, or reachable loopback services. Those observations do not establish whether the Mac's services are currently running.

## Source reconciliation

Base: `58add5e58e581be21d3511fc4cd2cb5be44f49b7`, current main when prepared.

Existing repair reused without alteration: `84263bfdadfd3f07a81ed7133456287e687146ba`, originally recorded in [the October 5 #73 result](https://github.com/AjaneeI/agentic-analytics-lab/issues/73#issuecomment-6003343243).

The repair restores `num_predict=512` and `num_ctx=65536` in the existing Ollama client and preserves its existing regression test. The earlier repair and current main were separate children of `c681efef`; blindly fast-forwarding that historical local branch to main would not combine them.

This preparation carries the exact two repaired file blobs onto current main. It preserves main's already-approved active-work SB-D01 correction from #80 and all task, worker, prompt, tool, SQL-guard, scorer, reference, dataset, and policy-corpus files. It is only the candidate snapshot for this SB-D01 continuation; do not run unrelated frozen benchmark lanes from it.

Current fixture task text:

> Among active work items (status != done) in the seed-42 snapshot, identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.

Load this request from the pinned fixture. Never paste expected answers or reference metadata into the model prompt.

Historical successor branches #83, #88, and #90 contain separate preregistrations and failed/unscored SB-D01 attempts. Their passing SQL/delegation micro-studies are not accepted SB-D01 evidence. Their boundary-enforcement changes are not silently imported here.

## Deterministic preparation verification

Python 3.12.14, standard-library unittest, mocked HTTP transport:

| Check | Observed result |
|---|---|
| Existing five-test repair suite against current-main client | 4 passed; the context regression failed with `2048 != 65536`; exit 1 |
| Same suite against the prepared client | 5 passed; exit 0 |
| Prepared source versus original repair | Both files byte-for-byte identical |

Prepared file identities:

| File | Git blob SHA | SHA-256 |
|---|---|---|
| `src/agents/ollama_client.py` | `f2137780ebd657bb0c5229e8ca2a3e5412298923` | `ddffe7ffb31c9586077b1c2160d06da88e9ef2903aa84c8c32864413ee83ecd4` |
| `tests/test_ollama_client.py` | `752b2910eba9617151f615a22456a0b04eacdd79` | `e580dc29a196fe45d2d688367d33564b2f562aebc14e256fa42feef7848df424` |

These checks verify the request-payload repair only. They are not live model evidence, ClickHouse evidence, a full repository suite, or hosted CI for this new commit.

## Local setup

The immutable execution commit is recorded in the latest October 12 checkpoint on #73. Set `PHASE2_EXPECTED_SHA` to that exact SHA before these commands; do not substitute the current moving main or a successor branch.

Use the existing project Python environment. Inspect the existing checkout and preserve any local changes. Fetch only the prepared branch and create a separate detached worktree:

```bash
PHASE2_REPO=/Users/ajaneeigharo/Projects/agentic-analytics-lab
PHASE2_WORKTREE=/Users/ajaneeigharo/Projects/agentic-analytics-lab-phase2-treatment-a-20261012
git -C "$PHASE2_REPO" remote get-url origin
```

The origin must identify `AjaneeI/agentic-analytics-lab`. Then:

```bash
test -n "$PHASE2_EXPECTED_SHA" &&
git -C "$PHASE2_REPO" fetch origin refs/heads/phase2/sbd01-treatment-a-20261012:refs/remotes/origin/phase2/sbd01-treatment-a-20261012 &&
test "$(git -C "$PHASE2_REPO" rev-parse refs/remotes/origin/phase2/sbd01-treatment-a-20261012)" = "$PHASE2_EXPECTED_SHA" &&
git -C "$PHASE2_REPO" worktree add --detach "$PHASE2_WORKTREE" "$PHASE2_EXPECTED_SHA"
```

Stop on any failure. If the destination already exists, inspect it; do not delete or overwrite it. Do not reset, rebase, force, or alter the original checkout.

Load the existing trusted ignored local environment into this shell without printing credential values. Retain the existing local service startup procedure if a service needs resuming; do not install a replacement stack or change permissions/configuration.

Before any model invocation, verify:

- Exact pinned HEAD and clean worktree.
- Existing `hermes-local:qwen3.5-9b` identity and local Ollama endpoint.
- Repository preflight returns exactly 500 rows through authenticated read-only ClickHouse access.
- Existing task boundary: oracle route metadata, `multi_source`, only `query_clickhouse` and `retrieve_policy`, at most two evidence calls, at most six model steps.
- Local-only execution and zero paid fallback.

```bash
cd "$PHASE2_WORKTREE"
git rev-parse HEAD
git status --porcelain
ollama list
python scripts/preflight_benchmark_env.py
```

A failed preflight means **not run**, not a failed benchmark score. Stop before invoking the worker.

## One Treatment A run and evidence capture

Use a new evidence directory outside the worktree. The collector below only records the existing executor result; it does not alter the worker prompt, tool calls, result, or scoring. It does not retry.

```bash
PHASE2_EVIDENCE="$(mktemp -d /tmp/sbd01-treatment-a.XXXXXX)"
export PHASE2_EVIDENCE PHASE2_EXPECTED_SHA
ollama ps > "$PHASE2_EVIDENCE/ollama-before.txt"
python - <<'PY'
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
from src.evals.system_benchmark.runner import fingerprint_paths, run_trial

root = Path.cwd()
out = Path(os.environ["PHASE2_EVIDENCE"])
expected = os.environ["PHASE2_EXPECTED_SHA"]
def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()
head = git("rev-parse", "HEAD")
before = git("status", "--porcelain")
if head != expected or before:
    raise SystemExit("STOP: expected pinned clean worktree")
tasks = {t.case_id: t for t in load_tasks(root / "evals/system_benchmark/development_tasks.json")}
references = {r.reference_solution_id: r for r in load_references(root / "evals/system_benchmark/development_references.json")}
task = tasks["SB-D01"]
contract_paths = [
    "evals/system_benchmark/development_tasks.json",
    "evals/system_benchmark/development_references.json",
    "src/evals/system_benchmark/contracts.py",
    "src/evals/system_benchmark/loader.py",
    "src/evals/system_benchmark/references.py",
    "src/evals/system_benchmark/routing.py",
    "src/evals/system_benchmark/workers.py",
    "src/evals/system_benchmark/local_worker.py",
    "src/evals/system_benchmark/runner.py",
    "src/evals/system_benchmark/scoring.py",
    "src/agents/ollama_client.py",
    "src/tools/clickhouse_readonly.py",
    "src/tools/policy_retrieval.py",
    "scripts/generate_delivery_data.py",
]
contract_paths.extend(str(p.relative_to(root)) for p in (root / "evals/system_benchmark/corpus").rglob("*") if p.is_file())
manifest = {
    "attempt_status": "started",
    "start_commit": head,
    "task_id": task.case_id,
    "task_text": task.request,
    "benchmark_version": task.benchmark_version,
    "worker": "src.evals.system_benchmark.local_worker.BoundedLocalExecutor",
    "model": "hermes-local:qwen3.5-9b",
    "allowed_tools": ["query_clickhouse", "retrieve_policy"],
    "start_utc": datetime.now(timezone.utc).isoformat(),
    "status_before": before,
    "retries": 0,
    "reprompts": 0,
    "hands_on_minutes": None,
    "benchmark_contract": fingerprint_paths(root, contract_paths),
}
worker = BoundedLocalExecutor()
def capture_execution(*args):
    execution = worker(*args)
    (out / "execution.json").write_text(json.dumps(asdict(execution), indent=2, sort_keys=True) + "\n")
    return execution
started = time.monotonic()
try:
    result = run_trial(task, references[task.reference_solution_id], trial_number=1, executor=capture_execution)
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (out / "raw-result.json").write_text(raw)
    manifest["attempt_status"] = "completed"
    manifest["task_success"] = result["task_success"]
    print(raw, end="")
except Exception:
    manifest["attempt_status"] = "execution_error"
    (out / "error.txt").write_text(traceback.format_exc())
    raise
finally:
    manifest["end_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["wall_seconds"] = time.monotonic() - started
    manifest["end_commit"] = git("rev-parse", "HEAD")
    manifest["status_after"] = git("status", "--porcelain")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
PY
PHASE2_RUN_EXIT=$?
ollama ps > "$PHASE2_EVIDENCE/ollama-after.txt"
printf 'Run exit: %s\nEvidence: %s\n' "$PHASE2_RUN_EXIT" "$PHASE2_EVIDENCE"
```

If the shell is configured to exit on a nonzero command, run the postflight memory/status reads separately after an error. Preserve the existing error and do not invoke the worker again.

Capture exact Ollama/client/runtime versions and model identity separately, plus observed memory/context, measured Ajanee hands-on minutes, actual spend, and any setup/recovery action. Leave unavailable measurements unknown. `execution.json` exists only when the executor returns and contains the normalized response and runtime observations before scoring. On an exception, do not invent missing response, call counts, structured values, or scores. Keep the raw files unchanged and check them for credentials before publishing.

## Stop and reconciliation

- On `task_success: true`: preserve the raw response, runtime observations, deterministic score/reason codes, fingerprint, timing, resource observations, and clean before/after state; record accepted evidence on #73 and stop.
- On `task_success: false` or any execution error: preserve the exact outcome and stop. No manual answer repair, SQL rewriting, prompt changes, retries, or alternative worker.
- A changed HEAD/worktree or missing provenance is a qualification blocker.
- Keep historical failed attempts. Do not rescore them under the corrected active-work contract or present this one development task as generalization evidence.
- Update the existing Asana rerun task and Notion Phase 2 checkpoint from the actual result. Do not automatically advance research phases or start Treatment B.
