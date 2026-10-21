# phase3-d01-tie-order-v1 — inactive offline correction

This separately versioned candidate corrects D01-TIE-ORDER-01 in a copied,
synthetic-only proof/verifier. Original PR121/122 sources, frozen scorer,
configurations and all historical evidence remain byte-identical. Nothing imports
this candidate from an active worker, tool, scorer or benchmark entrypoint.
Every verdict remains `live_qualified=false`; Phase3 acceptance remains false.

## Root cause and exact semantic difference

The original interpreter stably sorts grouped rows and slices LIMIT. When every
explicit ORDER BY key ties at the cutoff, its particular representative need not
match the one returned by SQLite. The old reconciliation incorrectly requires
that particular representative even though the captured peer is legitimate.

The new interpreter retains the complete sorted pre-LIMIT relation, declared
key fields and requested limit. The verifier retains exact result cardinality,
unique team identities, projected keys and values, host identity/commitments and
all earlier population/lineage checks. For a truncated ordered result only:

- Every row strictly before the boundary equivalence class is mandatory.
- Remaining slots can contain any distinct peers equal on **all** declared sort
  keys at the boundary. A secondary or tertiary key cannot be ignored.
- The captured rows must be a subset of those admissible rows. No claim selects
  or substitutes a capture; the claimed team must be present in that capture.
- Boundary keys and global winners use exact rational values. Existing float
  reconciliation tolerance and the unchanged0.2percentage-point claim tolerance
  never define a tie. False uniqueness and rounded near-winner claims still fail.

No grammar expansion, automatic sorting of captured bytes, coercion, SQL rewrite,
retry, scoring-criteria edit or result normalization is introduced. The original
unordered full-result comparison remains unchanged. LIMIT0 remains unsupported.

## Version and trust boundary

`verify(claim, *, resolver, expected)` is unchanged. New `HostCapture` instances
pin this new inactive contract and metric version; old-version captures cannot be
silently relabelled and are never rescored. Capture records and commitments are
host-owned; claimant-provided resolver/expected fields do not replace them.
This remains a bounded synthetic reference interpreter, not general SQL support,
cryptographic live authentication or a malicious-Python-host sandbox.

The PR122 synthetic capture adapter remains pinned to its original verifier and
contract. This proposal does **not** wire the new verifier into it or any runtime.
The validation-only host creates new memory-SQLite captures for this candidate.
Any later adapter integration or activation needs a separate reviewed version.

## Offline validation

Run `run_validation.py --configuration synthetic-config.json --output NEW.json`
with Python3.11 or3.12. It refuses existing output paths and stale source pins
before creating even memory SQLite. The unchanged upstream runner installs audit
and import guards before candidate tests: no socket/network, process launch,
file-backed database or active runtime imports. Only new synthetic fixtures are
used in candidate checks.28 original verifier tests and60 named controls are also
reused against newly versioned host captures; original runners are independently
checked and historical reports preserved.

The initial RED control exposed two test-construction mistakes: duplicate fixture
IDs in multirow groups and an incorrect expectation that unsupported LIMIT0 was
contradicted rather than insufficient. Both initial records are retained. After
correcting test fixtures/expectation without expanding grammar, the unchanged
baseline fails9 of18 new methods. The corrected candidate passes those methods.
No live-model compliance or full SQL semantic completeness follows from this.

Exact command receipts, failed controls, independent review and preservation
manifest are retained in validation/. Frozen historical evidence is not modified.
