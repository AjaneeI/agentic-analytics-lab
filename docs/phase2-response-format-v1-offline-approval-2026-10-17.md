# Offline response-format proposal authorization

On October 17, 2026 EDT the owner explicitly instructed implementation of the Response-Format Compliance and Research Decision Brief plan. Authorized deliverables are an isolated inactive proposal from execution commit `57c3007a25af4ff21bec42138aa1df7268ee7d95`, a prompt-only candidate patch with hashes/fingerprint, offline strict-parser and delivery checks on Python 3.11/3.12, one independent offline review, a Phase 3–4 decision brief, a draft PR and evidence-backed tracker reconciliation.

The approved field guidance preserves existing response types: dispositions answer/clarify/unsupported/handoff; nonempty string answer_text; string/null uncertainty; object/null clarification and handoff, using unquoted null when inapplicable. The candidate must preserve the existing prompt prefix, evidence/tool instructions, parser, scorer, optional-field behavior, model/settings, SQL security, budgets and historical evidence.

This authorization is **offline preparation only**. It does not activate the prompt, enable provider structured-output mode, normalize invalid responses, increase budgets, authorize a new live attempt, merge a PR, trigger automatic review, change frozen research methodology or accept a research phase. The prior scope-observation approval is resolved and its single live attempt is consumed; its failure must not be corrected, rescored or repeated.

Independent Phase 3 and Phase 4 recommendations remain owner decisions, not implemented evaluation changes. Existing numerical evidence must be reused without selecting a new statistical method or inventing scientific thresholds. Statistical freeze is deferred where existing evidence cannot justify a selection.
