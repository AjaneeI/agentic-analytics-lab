---
name: project-health-report
description: Collect GitHub repository signals in parallel, analyze maintainability and contribution readiness, and render a source-backed visual project-health report without collapsing evidence into an opaque score.
---

# Project Health Report

Use this skill when a repository needs a fast, audience-ready health readout for maintainers, collaborators, recruiters, or portfolio review.

The workflow is intentionally evidence-first:

1. **Collect** independent GitHub signals in parallel.
2. **Analyze** maintainability, contribution flow, documentation, release practice, and automation using explicit heuristics.
3. **Render** the evidence into a visual report whose claims remain traceable to source metrics.

## Data collection

Collect these independent surfaces in parallel when GitHub access permits:

- repository metadata and default branch
- recent commits and commit authors
- open and closed issues
- open and merged pull requests
- open good-first issues
- releases
- repository root contents
- GitHub Actions workflow files

Prefer GitHub API or GitHub connector results over scraping rendered pages. Preserve the collection timestamp and the commit/ref used for the snapshot.

## Analysis framework

### Activity and concentration

Report recent commit velocity and observed author distribution. Treat author concentration as a maintenance-risk signal, not a judgment about project quality. Break automated or assistant-authored commits out from human authors when they can be identified reliably.

### Issue and pull-request flow

Report open and closed issue counts, open and merged pull requests, and median resolution time for closed issues when timestamps are available. Small samples and administrative issues can distort resolution statistics, so always show the underlying count and caveat.

### Contribution readiness

Check for README, CONTRIBUTING, LICENSE, SECURITY, architecture documentation, and open good-first issues. If CONTRIBUTING exists, scan it for contribution workflow, testing expectations, and any AI-assisted contribution policy. Do not infer a policy from absence.

### Reliability and release practice

Report the number and names of CI/workflow definitions and release count. Missing releases are a watch item, not an automatic failure for an early-stage or research repository.

### Good-first issue review

When open good-first issues exist, rank them only with an explicit rubric: bounded scope, clear acceptance criteria, low dependency risk, testability, and documentation/context quality. Never fabricate a ranking when issue bodies are unavailable.

## Visual contract

Follow TEMPLATE.md. Produce:

- a compact SVG snapshot suitable for a README
- a durable Markdown explanation
- a self-contained HTML report for deeper review
- a machine-readable JSON snapshot for reuse

Emphasize a few high-signal metrics, then show watch items and provenance. Avoid a single composite health score unless the user explicitly requests one and the weighting model is documented.

## Claim boundaries

- Report only source-backed metrics.
- Label proxies as proxies.
- Timestamp snapshots.
- Do not call a repository healthy or unhealthy solely because one metric is high or low.
- Do not interpret missing releases, issues, or contributors without project-stage context.
- Keep recruiter-facing language evidence-based and easy to verify.

## Default command

    python scripts/render_project_health_report.py --repo OWNER/REPO

The default output directory is docs/project-health.
