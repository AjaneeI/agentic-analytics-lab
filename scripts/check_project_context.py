#!/usr/bin/env python3
"""Deterministic checks for Project Context Protocol v1."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["AGENTS.md", "PROJECT.md", "STATUS.md", "DECISIONS.md"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


for name in REQUIRED:
    path = ROOT / name
    if not path.exists():
        fail(f"missing required context file: {name}")
    if not path.read_text(encoding="utf-8").strip():
        fail(f"context file is empty: {name}")

status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
decisions = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")

for token in ["PROJECT.md", "STATUS.md", "DECISIONS.md"]:
    if token not in agents:
        fail(f"AGENTS.md does not require reading {token}")

if "GitHub is the technical source of truth" not in (ROOT / "PROJECT.md").read_text(encoding="utf-8"):
    fail("PROJECT.md must state the technical source of truth")

if not re.search(r"Last reviewed|_Last reviewed", status, re.IGNORECASE):
    fail("STATUS.md must include a last-reviewed marker")

if "unknown" not in decisions or "not_reached" not in decisions:
    fail("DECISIONS.md must preserve uncertainty semantics for failure attribution")

# Basic reference checks for Markdown code spans that look like repository paths.
for source_name in ["PROJECT.md", "STATUS.md", "DECISIONS.md"]:
    text = (ROOT / source_name).read_text(encoding="utf-8")
    refs = re.findall(r"`((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)`", text)
    for ref in refs:
        # Skip illustrative/generated paths that are not intended as direct references.
        if ref in {"qwen2.5:7b"}:
            continue
        if "/" in ref or ref.endswith(".md"):
            candidate = ROOT / ref
            if ref in REQUIRED or candidate.exists():
                continue
            # A named doc may intentionally be mentioned at a higher level; fail only on explicit paths.
            if "/" in ref:
                fail(f"{source_name} references missing path: {ref}")

# Check that repository metadata is available when run inside git.
try:
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
except (FileNotFoundError, subprocess.CalledProcessError):
    fail("repository git metadata unavailable")

print("PASS: Project Context Protocol v1 checks passed")
