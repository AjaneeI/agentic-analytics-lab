#!/usr/bin/env bash
set -euo pipefail

REPO="AjaneeI/agentic-analytics-lab"

command -v gh >/dev/null || { echo "GitHub CLI (gh) is required."; exit 1; }
gh auth status

if [ ! -d .git ]; then
  git init
fi

git add .
if ! git diff --cached --quiet; then
  git commit -m "Initialize agentic analytics lab"
fi

git branch -M main

if gh repo view "$REPO" >/dev/null 2>&1; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/${REPO}.git"
  fi
  git push -u origin main
else
  gh repo create "$REPO" --private --source=. --remote=origin --push \
    --description "Private portfolio lab for a cost-aware agentic analytics system built from a ClickHouse workshop baseline."
fi

echo "Private repo ready: https://github.com/${REPO}"
