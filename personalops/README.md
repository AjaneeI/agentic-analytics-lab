# Hermes Desktop Lite — Personal Ops

This package installs the bounded `personalops` Hermes profile for one product workflow:

> Check Agentic Analytics Lab, tell me the highest-value safe next step, and move it forward as far as you safely can.

## Normal use

1. Open Hermes Desktop.
2. Select the `personalops` profile.
3. Send the exact request above.

Normal use does not require Terminal, Ollama commands, profile editing, worker routing, or benchmark tooling. The profile is pinned to the local `hermes-local:qwen3.5-9b` model through loopback Ollama with a 65,536-token context. It has no paid provider or remote fallback.

## What Hermes may do

- **Green:** inspect the approved repository, Git state, context files, and read-only GitHub issue/PR metadata; read/search bounded repository text; run the named context, diff, and full-suite checks.
- **Yellow:** delegate exactly one structured task to one non-concurrent child for a reversible local text edit. The parent must independently inspect the diff and run approved checks before claiming completion.
- **Red:** stop and ask Ajanee before external writes or communications, push/merge, publish/deploy, spending, deletion, credential/security changes, new permissions, or ambiguous high-impact choices. Desktop Lite contains no Red execution tool.

Every worker request must include `Objective`, `Inputs`, `Allowed changes`, `Acceptance`, `Evidence`, and `Stop`. The installed plugin verifies the frozen Hermes one-worker/retirement runtime before it allows delegation and blocks repeat delegation. Repository paths are resolved beneath the approved root, and patching uses compare-and-swap semantics.

## Evidence and limits

The deterministic smoke runner permits exactly one model attempt. It preserves the command metadata, final stdout, stderr, usage, plugin events, profile validation, and redacted request dumps under `personalops/evidence/<timestamp>/`. Acceptance checks the live repository identity, local-only request path, approved tool surface, successful Green check, one-worker ceiling, independent Yellow verification, post-child retirement, Red approval behavior, structured outcome, and `$0` paid spend.

A passing smoke establishes only this bounded repository workflow. It does not establish unrestricted autonomy, general model reliability, benchmark superiority, or permission to expand the architecture.

The 2026-10-06 post-hardening smoke passed all 22 frozen deterministic checks, but its user-visible final answer contradicted the structured outcome and observed test evidence. The formal PASS is preserved; Desktop Lite is not marked operational because the product-level requirement for an evidence-consistent final result was not met. See `evidence/20261006T201339.337217Z/RESULT.md`.

## Track separation

- **Track A — benchmark evidence:** issues #73–#90 and their preserved artifacts remain historical M0 evaluation evidence. This package does not change their prompts, contracts, treatments, or conclusions.
- **Track B — Personal Ops product:** issue #91 and its draft PR own Desktop Lite implementation and product evidence. Issue #89 and draft PR #90 are provenance links only; PR #90 is not modified or merged by this work.

## Maintainer operations

Installation is idempotent for package-owned files and preserves unrelated profile files. It requires explicit absolute paths for the package, profile, approved repository, and Hermes checkout. `personalops.validate.validate_profile` performs post-install validation, and `personalops.smoke.run_smoke` performs the single-attempt acceptance run. Do not rerun a failed live smoke merely to obtain a pass.
