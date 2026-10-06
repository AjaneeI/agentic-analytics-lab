# Hermes Desktop Lite trust-boundary hardening plan

> Execute each task with adversarial RED, minimal GREEN, and focused verification. Do not invoke Hermes/Qwen until all deterministic gates and the final review are clean.

### Task 1: Parent-owned Yellow manifest and repository-diff enforcement

- [ ] Add adversarial tests for undeclared edits, checker edits, traversal, symlinks, baseline failure, and sensitive-path variants.
- [ ] Witness focused RED.
- [ ] Implement the smallest parent-owned manifest, baseline snapshot, write allowlist, and independent post-change verifier.
- [ ] Witness focused GREEN.

### Task 2: Session-scoped delegation accounting

- [ ] Add tests for same-session blocking, independent sessions, and deterministic concurrent isolation.
- [ ] Witness focused RED.
- [ ] Replace process-global accounting with session/run-scoped state without broadening concurrency.
- [ ] Witness focused GREEN.

### Task 3: Ordered trajectory and approval scoring

- [ ] Add adversarial fixtures for unknown tools, mismatched checks, invalid Yellow ordering, missing verification, true Red clarification, text-only Red, unnecessary approval, and Green completion.
- [ ] Witness focused RED.
- [ ] Bind acceptance to ordered observable events and deterministic Red classification.
- [ ] Witness focused GREEN.

### Task 4: Preflight abort and malformed-evidence handling

- [ ] Add tests proving invalid validation invokes no launcher and malformed/missing evidence fails closed with safe preservation.
- [ ] Witness focused RED.
- [ ] Implement preflight abort, strict evidence parsing, safe raw preservation, and credential redaction.
- [ ] Witness focused GREEN.

### Task 5: Verification, review, and single gated live smoke

- [ ] Run focused product tests, full repository suite once stable, Hermes retirement/one-worker tests, and profile/plugin validation.
- [ ] Perform a fresh read-only trust-boundary review and resolve deterministic critical/high findings with RED→GREEN.
- [ ] If and only if every gate is clean, preregister and execute one live smoke with zero retries.
- [ ] Record exact evidence on issue #91 and draft PR #93, preserving #89/#90.
