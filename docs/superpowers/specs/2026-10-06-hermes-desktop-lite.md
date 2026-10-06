# Hermes Desktop Lite Design

**Status:** Approved for implementation on 2026-10-06  
**Product track:** Hermes Personal Ops  
**Evaluation provenance:** Agentic Analytics Lab issues #89 and #90 remain unchanged historical evidence

## Objective

Make Hermes Desktop a usable local front door for one bounded repository-engineering workflow:

> Check Agentic Analytics Lab, tell me the highest-value safe next step, and move it forward as far as you safely can.

The first workflow does not use ClickHouse. It recovers current state from the repository, Git, and read-only GitHub metadata; selects a justified safe next action; performs Green work directly; uses no more than one bounded child for Yellow work; independently verifies any child result; and stops for Ajanee before Red work.

## Architecture

```text
Hermes Desktop
    -> isolated personalops profile
    -> Personal Ops policy prompt + repository plugin
    -> local Qwen3.5-9B/Ollama
    -> repository-scoped read/search/check/patch tools
    -> optional one Hermes child
    -> deterministic independent verification
```

Agentic Analytics Lab versions the `personalops` package and product evidence. Hermes continues to own its Desktop, `clarify`, approval, delegation, and post-success delegation-retirement mechanisms. The product package does not modify Hermes core and does not depend on ClickHouse or the benchmark runners.

The product branch starts from `main`; it does not contain or depend on PR #90. Issue #89 and PR #90 are linked only as provenance for the previously verified one-child safety work.

## Versioned package

`personalops/` contains:

- `VERSION`: package version;
- `policy.json`: the inspectable Green/Yellow/Red action policy;
- `workflow.json`: the repository workflow, check allowlist, worker contract, acceptance contract, and final-response contract;
- `profile/config.yaml`: the local-only Hermes profile template;
- `profile/plugins/personalops-repository/`: self-contained repository tools, safety hooks, and the injected Personal Ops prompt;
- `install.py`: idempotent profile installation with explicit repository and Hermes-runtime inputs;
- `validate.py`: deterministic package/profile/runtime validation;
- `smoke.py`: one-shot product acceptance runner that preserves raw evidence and scores the observable trajectory.

No new framework or non-standard Python dependency is introduced.

## Tool boundary

The profile exposes only:

- built-in `clarify`;
- built-in `delegate_task`;
- the `personalops_repository` plugin toolset.

It does not expose generic terminal, file, browser, web, MCP, memory, cron, messaging, deployment, payment, or credential tools.

The repository plugin provides bounded operations:

1. `personalops_inspect_repository` — read-only Git, context-file, and read-only GitHub issue/PR state;
2. `personalops_read_file` — bounded UTF-8 reads inside the approved repository;
3. `personalops_search_repository` — bounded ripgrep search inside the approved repository;
4. `personalops_run_check` — only named commands from `workflow.json`;
5. `personalops_apply_patch` — delegated-child-only, compare-and-swap text replacement inside the approved repository;
6. `personalops_verify_change` — parent-callable diff inspection plus named deterministic checks after a child returns;
7. `personalops_record_outcome` — structured final-status evidence.

Paths must remain under the configured repository root after symlink resolution. Sensitive paths, binary files, oversized inputs, shell strings, arbitrary commands, and unrecognized check identifiers fail closed. Tool activity is appended to a profile-scoped JSONL evidence log without secrets.

## Permission policy

### Green — autonomous

Read and inspect files; inspect Git status, branch, history, and diffs; retrieve read-only issue/PR metadata; search repository text; run allowlisted deterministic checks; and summarize evidence.

### Yellow — autonomous plus independent verification

One bounded delegated child may make reversible local text edits within the approved repository. Its request must include exactly these fields:

- Objective
- Inputs
- Allowed changes
- Acceptance
- Evidence
- Stop

Only the child may call the patch tool. After the child returns, the parent must call `personalops_verify_change`; the final response cannot claim completion without the verifier's evidence.

### Red — approval required

External communication, issue or PR mutation, publishing, deployment, consequential push or merge, spending or paid providers, meaningful deletion, credentials or security changes, new external permissions, and ambiguous high-impact decisions require Ajanee's approval.

No Red execution tool is present in Desktop Lite. When Red work is next, Hermes uses `clarify` and presents:

- Decision needed
- Why it matters
- Options/tradeoffs
- Hermes recommendation

The workflow then waits. Routine implementation decisions are not escalated.

## Worker enforcement

The profile pins one concurrent child, one spawn depth, and one one-shot child. The plugin also blocks malformed or repeated delegation calls.

The product freezes a runtime contract containing the verified Hermes core guard files and hashes. At runtime, a missing or mismatched guard disables delegation through the plugin's pre-tool hook. Installation and validation also fail closed. This is defense in depth; it does not replace Hermes's own one-worker and post-success retirement behavior.

## Local-only model contract

The profile is pinned to:

- model: `hermes-local:qwen3.5-9b`;
- provider: `custom`;
- base URL: `http://127.0.0.1:11434/v1`;
- context length: `65536`;
- temperature: `0` for delegated requests;
- terminal timeout: `600` seconds where the Hermes runtime requires it.

There is no secondary model, provider, remote fallback, or paid API configuration. Incremental paid spend must remain `$0`.

## State recovery and next-action selection

The inspection tool returns the resolved repository root, branch, HEAD, clean/dirty state, upstream divergence, recent commits, required context-file availability, and read-only GitHub issue/PR summaries when `gh` is available.

The tool emits one deterministic recommended action:

1. dirty worktree -> inspect and verify the existing changes;
2. current branch has an open draft PR -> run the bounded product verification set;
3. current branch is ahead of its upstream -> run verification before requesting approval to push/open a PR;
4. otherwise -> run the repository context and full test checks.

The recommendation is evidence-backed operational guidance, not a claim that the heuristic is globally optimal.

## Acceptance evidence

The smoke runner sends the exact natural-language product request through the installed `personalops` Hermes profile once. It preserves command metadata, stdout, stderr, usage, plugin events, profile validation, and request dumps with authorization values redacted.

Acceptance requires:

- the profile and package validate;
- the inspected repository root, branch, and HEAD match the live checkout;
- no ClickHouse or benchmark evidence tool is visible or called;
- a safe recommended action is recorded;
- the corresponding Green check runs successfully;
- no more than one delegation and child occur;
- any patch is child-only and followed by successful independent verification;
- any Red next action is expressed as an approval request rather than executed;
- the runtime worker guard is valid and post-child `delegate_task` retirement is observable if delegation occurs;
- the structured outcome and concise final response are present;
- retries, paid spend, and silent fallbacks remain zero.

A smoke with no Yellow work may pass without delegation. That establishes the first useful Green workflow while the deterministic tests establish the bounded Yellow path. It does not establish unrestricted autonomy or general model reliability.

## UX

Ajanee selects the `personalops` profile in Hermes Desktop and types the natural-language request. Ordinary use does not require Terminal, knowledge of Ollama, profile plumbing, worker routing, or benchmark infrastructure. The final response reports current state, recommended action, action taken, verification, and any decision needed without exposing orchestration logs.

## Stop boundaries

This increment does not add ACS, ASSERT, memory/vector storage, multiple workers, new agent frameworks, broad MCPs, phone/voice, public networking, cloud/paid fallback, or unrelated benchmark repairs. PR #90 remains draft and unmodified.
