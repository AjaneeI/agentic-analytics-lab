# Offline validation evidence

Independent exact-candidate review:069407889c46e0a554f25950e77c667589f3138a.
Inactive preparation accepted only; no must-fix findings. Full original outputs,
commands, initial failures, corrected controls and688-case-per-version probes
are in offline-validation-evidence.zip. archive-files-sha256.json fingerprints
every archived path; archive SHA is recorded in final-receipt.json.

Per Python3.11.16/3.12.6:18new+28reused verifier test methods,60reused
named controls,16new tie matrix cases; all match;211memory SQLite connections
and0unexpected guard denials. Eight preflight/overwrite controls refuse before
SQLite. Independent688new probes per version pass. Separate unchanged PR122
runner retains50passing unit methods and its known1scientific tie mismatch
within8integration cases. It is not retrospectively corrected.

Broader repository command:python -m unittest discover -s tests -v;297pass
per interpreter under inherited network/file-backed-database denial. Broader
suite subprocess exceptions permit only inspected same-interpreter offline test
children and exact git rev-parse --is-inside-work-tree. The initial stricter
guard blocked that readonly Git metadata check, causing1reported failure;
original guard/log/receipt are preserved. Candidate-specific validation denies
all process launch, network, external database and active runtime imports.

Corrected baseline red control fails9of18new methods. Initial baseline10failure
and candidate3failure records include two author test-construction mistakes:
duplicate synthetic IDs and an incorrect LIMIT0 expected outcome. These are
retained, separately explained and corrected without changing grammar/scoring.

Commands use the explicitly recorded interpreter paths in command receipts.
Candidate command from repository root:

    python proposals/phase3-d01-tie-order-v1/run_validation.py --configuration proposals/phase3-d01-tie-order-v1/synthetic-config.json --output NEW.json

Evidence outputs are exclusive-create; never reuse an existing output path.

Non-blocking review limitation: standalone candidate preflight pins its five
candidate source/contract files, but does not itself enforce declared upstream
dependency hashes. This delivery separately verifies every304base path and all
five declared upstream pins. Retain exact-tree/preservation verification for
future offline use; do not treat configuration preflight alone as dependency
verification or permission to activate.

Synthetic tests cannot establish live SQL completeness, capture authentication,
model compliance or Phase3 acceptance. No active wiring/activation, historical
attempt rescore, failed SQL replay, model/service/resource operation, held-out,
statistical method adoption, TreatmentA, paid fallback, automatic review or merge.
