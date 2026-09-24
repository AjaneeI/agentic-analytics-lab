# Project Health Visual Contract

The project-health report uses four layers so a reader can understand the repository in seconds and inspect the evidence when needed.

## Layer 1: README snapshot

Show four primary metrics when available:

- commits in the last 7 days
- merged pull requests
- open issues
- CI workflow count

Immediately below them, surface a short evidence line for issue flow and contributor concentration.

## Layer 2: Watch items

Use explicit, source-backed watch items such as:

- one human author accounts for most observed commits
- CONTRIBUTING.md is absent
- LICENSE is absent
- no release cadence exists yet
- no good-first issues are open

Watch items are prompts for review, not failures or scores.

## Layer 3: Durable report

The Markdown and HTML reports should include snapshot metadata and source ref, activity and contributor signals, issue and pull-request flow, documentation and contribution readiness, automation/reliability, release practice, caveats, and limitations.

## Layer 4: Machine-readable evidence

Write snapshot.json with the same metrics used by the human-facing artifacts so future automation and portfolio tooling can reuse the evidence without parsing prose.

## Visual standards

- Keep visuals readable on GitHub light and dark themes.
- Use SVG for README-native visuals whenever possible.
- Add accessible title and description text to SVGs.
- Keep labels visible without hover.
- Prefer direct metrics over decorative graphics.
- Include an as-of timestamp and source commit/ref.
- Do not hide uncertainty behind a composite score.
