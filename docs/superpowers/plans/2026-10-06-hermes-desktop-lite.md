# Hermes Desktop Lite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver an isolated, local-only Hermes `personalops` profile that can inspect Agentic Analytics Lab, advance one safe repository action, verify bounded worker changes, and stop for approval at Red actions.

**Architecture:** A self-contained `personalops` package owns the policy, workflow manifest, Hermes profile template, repository-scoped plugin, installer, validator, and smoke runner. Hermes core remains unchanged; its existing Desktop, `clarify`, delegation, one-worker enforcement, and retirement mechanisms are reused and runtime-attested.

**Tech Stack:** Python 3 standard library, `unittest`, Hermes directory plugins, Git, GitHub CLI read-only queries, local Qwen3.5-9B/Ollama.

**Spec:** `docs/superpowers/specs/2026-10-06-hermes-desktop-lite.md`

## Global Constraints

- Start from repository `main`; do not modify or depend on PR #90.
- Use only local `hermes-local:qwen3.5-9b` at `http://127.0.0.1:11434/v1`, 65,536 context, and `$0` paid spend.
- Do not modify Hermes core, benchmark prompts/contracts, ClickHouse, or M0 evidence.
- Expose only `clarify`, one `delegate_task`, and repository-scoped Personal Ops tools.
- No arbitrary shell, generic file write, network-write, credential, deployment, payment, deletion, or paid fallback path.
- Apply strict RED -> GREEN TDD for production behavior; run the full repository suite once after the bounded change is stable.
- Run the natural-language smoke exactly once after profile validation and GitHub draft-PR setup.

## Review Focus

- Repository escape through `..` or symlinks must be rejected by read, search, and patch operations; Task 2 tests each path class.
- A missing or changed Hermes delegation guard must block delegation while leaving Green inspection available; Task 3 tests both states.
- Parent-level patching or a second delegation must fail closed; Task 3 tests both attempts.
- Missing `gh`, malformed GitHub JSON, or network-read failure must not corrupt local state recovery; Task 2 tests graceful degradation.
- A child result without subsequent verifier evidence must not be accepted as completed Yellow work; Task 4 tests the scorer.

---

### Task 1: Versioned policy and workflow contracts

**Files:**
- Create: `personalops/__init__.py`
- Create: `personalops/VERSION`
- Create: `personalops/policy.json`
- Create: `personalops/workflow.json`
- Create: `personalops/contracts.py`
- Test: `tests/test_personalops_contracts.py`

**Interfaces:**
- Produces: `load_policy(root: Path) -> dict`, `load_workflow(root: Path) -> dict`, and `validate_contracts(root: Path) -> list[str]`.
- Produces contract values consumed by Tasks 2-5: action levels, named checks, worker fields, model identity, tool allowlist, and final-status fields.

- [ ] **Step 1: Write failing contract tests**

Test valid repository contracts, missing required policy categories, an arbitrary command in a named check, a paid/remote fallback, missing worker fields, and mismatched package version.

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_personalops_contracts -v`  
Expected: FAIL because `personalops.contracts` does not exist.

- [ ] **Step 3: Implement the minimal contracts and validator**

Use JSON plus standard-library validation. Require exact action levels `green`, `yellow`, `red`; exact model/provider/base URL/context; a list-form command allowlist; exactly one worker; and the six worker-contract fields from the spec.

- [ ] **Step 4: Run GREEN**

Run: `python3 -m unittest tests.test_personalops_contracts -v`  
Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: define Personal Ops product contracts`

### Task 2: Repository-scoped Green and Yellow tools

**Files:**
- Create: `personalops/profile/plugins/personalops-repository/plugin.yaml`
- Create: `personalops/profile/plugins/personalops-repository/__init__.py`
- Test: `tests/test_personalops_repository_plugin.py`

**Interfaces:**
- Consumes: `load_policy`, `load_workflow`, and the workflow check definitions from Task 1.
- Produces handlers for inspection, bounded read/search, named checks, delegated-child-only compare-and-swap patching, deterministic verification, and structured outcome recording.

- [ ] **Step 1: Write failing behavior tests**

Exercise a real temporary Git repository. Pin correct inspection evidence and recommendation, graceful GitHub degradation, named check execution, traversal/symlink rejection, parent patch rejection, child compare-and-swap patch success, changed-file mismatch, and independent verification output.

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_personalops_repository_plugin -v`  
Expected: FAIL because the plugin does not exist.

- [ ] **Step 3: Implement the smallest repository plugin**

Use `subprocess.run` with argument lists and no shell. Resolve every path beneath `PERSONALOPS_REPO_ROOT`; cap text, search, process output, and runtime; reject sensitive or binary paths; write patches atomically; and append JSONL events under `PERSONALOPS_EVIDENCE_LOG`.

- [ ] **Step 4: Run GREEN**

Run: `python3 -m unittest tests.test_personalops_repository_plugin -v`  
Expected: all Task 2 tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add bounded Personal Ops repository tools`

### Task 3: Profile installation and worker fail-closed enforcement

**Files:**
- Create: `personalops/profile/config.yaml`
- Create: `personalops/profile/runtime-contract.json`
- Create: `personalops/install.py`
- Create: `personalops/validate.py`
- Test: `tests/test_personalops_profile.py`

**Interfaces:**
- Consumes: policy/workflow contracts and plugin directory from Tasks 1-2.
- Produces: `install_profile(...) -> dict`, `validate_profile(...) -> dict`, and plugin delegation hooks that require an attested runtime, exactly one structured task, and no repeat delegation.

- [ ] **Step 1: Write failing install and enforcement tests**

Test isolated installation, idempotent replacement of package-owned files, preservation of unrelated profile files, exact local-only model/tool configuration, valid guard hashes, missing/mismatched guard failure, malformed worker contract rejection, one valid delegation, and second-delegation rejection.

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_personalops_profile -v`  
Expected: FAIL because installer, validator, and runtime contract do not exist.

- [ ] **Step 3: Implement installation and enforcement**

Render only the approved repository path into the installed config/plugin settings. Freeze the current verified Hermes guard file hashes after their focused tests pass. Keep plugin inspection tools available when the guard is invalid, but make every delegation pre-hook return a block action.

- [ ] **Step 4: Run GREEN and the Hermes focused tests**

Run: `python3 -m unittest tests.test_personalops_profile -v`  
Expected: all Task 3 tests pass.  
Run: focused Hermes one-worker and retirement tests named by `runtime-contract.json`.  
Expected: all focused Hermes tests pass before installation.

- [ ] **Step 5: Commit**

Commit message: `feat: install isolated Personal Ops profile`

### Task 4: Product smoke runner and deterministic acceptance

**Files:**
- Create: `personalops/smoke.py`
- Test: `tests/test_personalops_smoke.py`

**Interfaces:**
- Consumes: `validate_profile`, installed profile paths, plugin events, Hermes request dumps, and the workflow acceptance contract.
- Produces: a timestamped raw-evidence directory and `acceptance.json` with explicit pass/fail checks.

- [ ] **Step 1: Write failing acceptance tests**

Use fixture subprocess outputs and event streams to test an accepted Green workflow, rejected ClickHouse use, more than one delegation, unverified Yellow work, Red execution instead of approval, paid usage, missing outcome, wrong live repository identity, and observable post-child retirement when delegation occurs.

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_personalops_smoke -v`  
Expected: FAIL because `personalops.smoke` does not exist.

- [ ] **Step 3: Implement the minimal runner and scorer**

Launch `hermes -p personalops --in <repo> -z <exact prompt>` once, with request dumping and usage evidence enabled. Preserve raw stdout/stderr/events/requests; redact only authorization values in repository copies; never retry; score observable events and live Git identity.

- [ ] **Step 4: Run GREEN**

Run: `python3 -m unittest tests.test_personalops_smoke -v`  
Expected: all Task 4 tests pass.

- [ ] **Step 5: Commit**

Commit message: `test: add Desktop Lite acceptance runner`

### Task 5: Product documentation, installation, and one live smoke

**Files:**
- Create: `personalops/README.md`
- Modify: `DECISIONS.md`
- Modify: `STATUS.md`
- Create after execution: `personalops/evidence/<timestamp>/...`

**Interfaces:**
- Consumes: all earlier tasks plus the approved product issue and draft PR.
- Produces: an installed `personalops` profile, one preserved live smoke result, user-facing Desktop instructions, and final product status.

- [ ] **Step 1: Write documentation and state updates**

Document profile selection, the exact prompt, no-Terminal normal use, policy behavior, evidence limits, and Track A/Track B separation. Record the durable product-policy decision without rewriting historical M0 results.

- [ ] **Step 2: Run focused product tests**

Run: `python3 -m unittest tests.test_personalops_contracts tests.test_personalops_repository_plugin tests.test_personalops_profile tests.test_personalops_smoke -v`  
Expected: all focused tests pass.

- [ ] **Step 3: Run the full repository suite once**

Run: `python3 -m unittest discover -s tests -v`  
Expected: all repository tests pass.

- [ ] **Step 4: Install and validate the isolated profile**

Run the checked-in installer against `/Users/ajaneeigharo/.hermes/profiles/personalops`, the live Hermes checkout, and the approved Agentic Analytics Lab product worktree.  
Expected: install and post-install validation both report accepted local-only state.

- [ ] **Step 5: Create/push the product branch and draft PR**

Push only `feat/hermes-desktop-lite`; create one draft PR against `main`; cross-link its product issue plus #89/#90. Do not change PR #90.

- [ ] **Step 6: Run the natural-language smoke exactly once**

Run the checked-in smoke runner with the exact approved prompt.  
Expected: one preserved attempt and a deterministic acceptance decision. Do not retry a failed model run.

- [ ] **Step 7: Record result and commit evidence**

Update the product issue and draft PR with the exact commit, tests, raw-evidence paths, spend, and acceptance decision. If the smoke passes, record Desktop Lite operational only within this bounded workflow. If it fails, preserve the failure and stop without tuning/retry.

- [ ] **Step 8: Commit**

Commit message: `docs: record Desktop Lite product evidence`
