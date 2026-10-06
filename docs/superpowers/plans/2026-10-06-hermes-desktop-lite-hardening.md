# Hermes Desktop Lite trust-boundary hardening plan

> Execute each task with adversarial RED, minimal GREEN, and focused verification. Do not invoke Hermes/Qwen until all deterministic gates and the final review are clean.

### Task 1: Parent-owned Yellow manifest and repository-diff enforcement

- [x] Add adversarial tests for undeclared edits, checker edits, traversal, symlinks, baseline failure, and sensitive-path variants.
- [x] Witness focused RED.
- [x] Implement the smallest parent-owned manifest, baseline snapshot, write allowlist, and independent post-change verifier.
- [x] Witness focused GREEN.

### Task 2: Session-scoped delegation accounting

- [x] Add tests for same-session blocking, independent sessions, and deterministic concurrent isolation.
- [x] Witness focused RED.
- [x] Replace process-global accounting with session/run-scoped state without broadening concurrency.
- [x] Witness focused GREEN.

### Task 3: Ordered trajectory and approval scoring

- [x] Add adversarial fixtures for unknown tools, mismatched checks, invalid Yellow ordering, missing verification, true Red clarification, text-only Red, unnecessary approval, and Green completion.
- [x] Witness focused RED.
- [x] Bind acceptance to ordered observable events and deterministic Red classification.
- [x] Witness focused GREEN.

### Task 4: Preflight abort and malformed-evidence handling

- [x] Add tests proving invalid validation invokes no launcher and malformed/missing evidence fails closed with safe preservation.
- [x] Witness focused RED.
- [x] Implement preflight abort, strict evidence parsing, safe raw preservation, and credential redaction.
- [x] Witness focused GREEN.

### Task 5: Verification, review, and single gated live smoke

- [x] Run focused product tests, full repository suite once stable, Hermes retirement/one-worker tests, and profile/plugin validation.
- [x] Perform a fresh read-only trust-boundary review and resolve deterministic critical/high findings with RED→GREEN.
- [x] Preregister and execute one live smoke with zero retries after the deterministic gates were clean.
- [x] Record exact evidence on issue #91 and draft PR #93, preserving #89/#90.
