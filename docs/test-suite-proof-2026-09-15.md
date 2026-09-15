# Test Suite Proof - 2026-09-15

This proof captures the current public portfolio state after the blocker-rate
semantic guard and documentation updates.

Command:

```bash
python3 -m unittest discover -s tests
```

Result:

```text
........................
----------------------------------------------------------------------
Ran 24 tests in 0.004s

OK
```

Notes:

- The test run covers read-only SQL validation, blocker-rate semantic
  validation, the single-agent tool-call flow, the Ollama adapter, and the
  evaluation runner.
- This is safe to publish because it contains no secrets, private identifiers,
  raw benchmark data, or external user data.
