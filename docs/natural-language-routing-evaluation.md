# Natural-language routing evaluation

The current routed comparison uses oracle benchmark metadata to isolate
execution-layer value. That is useful, but it does not measure whether a system
can infer the right route from a user's words.

This lane keeps those questions separate.

## What is implemented

- `src/routing/natural_language_baseline.py` provides a small, inspectable
  lexical baseline that consumes only free text.
- `src/evals/natural_language_routing.py` evaluates route decisions separately
  from answer correctness.
- `evals/natural_language_routing_dev.json` contains paraphrased development
  fixtures spanning deterministic, local-reasoning, ambiguity, and unsupported
  external-source cases.
- `scripts/evaluate_natural_language_routing.py` reports accuracy,
  false-cheap routes, unnecessary escalations, and mismatches.

## Claim boundary

The development set is a regression fixture set, not evidence of generalization.
A classifier matching these reviewed examples does not prove it will route novel
requests correctly.

The oracle-metadata routed benchmark remains the execution-layer comparison
anchor. Natural-language route inference should be evaluated independently so a
routing-classification error is not confused with worker or tool performance.

## Next evidentiary step

Freeze a separate paraphrase/novel-request set after the classifier interface is
stable. Evaluate route inference without tuning against that set, then preserve
the result artifact and exact commit. Only after that evidence exists should the
lab make claims about end-to-end natural-language routing.

## Why this matters

This creates two explicit questions:

1. **Execution value:** if the route is known, does the routed architecture
   improve task success or efficiency enough to justify complexity?
2. **Inference quality:** can the system infer that route reliably from realistic
   user language?

Keeping them separate makes failures attributable and prevents oracle metadata
from inflating an end-to-end routing claim.
