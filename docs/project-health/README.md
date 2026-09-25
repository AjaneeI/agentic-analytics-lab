# Project Health Report

![Project health snapshot](overview.png)

Repository: **AjaneeI/agentic-analytics-lab**  
As of: **2026-09-24T19:32:00Z**  
Source ref: **4e22b6f4fbeab8183f5313de3b71865367faf6af**

This report keeps source signals visible instead of collapsing them into a single opaque health score.

## Snapshot

| Signal | Value |
| --- | ---: |
| Commits in the last 7 days | 31 |
| Commits observed | 49 |
| Open issues | 4 |
| Closed issues | 7 |
| Median closed-issue resolution | 20 min |
| Open pull requests | 7 |
| Merged pull requests | 28 |
| Open good-first issues | 0 |
| CI workflows | 5 |
| Releases | 0 |

## Contributor signal

Observed human commit authorship: AjaneeI: 47. Automation-like authorship: Copilot: 2.

This is a commit-authorship proxy, not a complete bus-factor measurement. Reviews, issue triage, design ownership, and unpublished work are not captured here.

## Documentation and contribution readiness

README=yes, ARCHITECTURE=yes, SECURITY=yes, CONTRIBUTING=no, LICENSE=no.

## Reliability and release practice

Detected workflows: assert-q3-smoke.yml, codeql.yml, oracle-routed-repeatability.yml, repeatability-benchmark.yml, tests.yml. GitHub releases published: **0**.

## Watch items

- Observed human commit authorship is concentrated (100% from one author).
- CONTRIBUTING.md is not present.
- No repository license file is present.
- No GitHub releases have been published yet.
- No open good-first issues are currently available.

## Caveats

- Commit collection is capped at the latest 100 commits.
- Contributor concentration uses commit authorship as a proxy, not organizational ownership.
- Issue resolution speed is descriptive and can be skewed by small or administrative issues.
- No opaque composite health score is produced; the report keeps source signals visible.

## Regenerate

    python scripts/render_project_health_report.py --repo AjaneeI/agentic-analytics-lab
