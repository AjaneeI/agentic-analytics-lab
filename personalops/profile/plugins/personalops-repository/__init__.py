"""Repository-scoped Hermes tools for Desktop Lite Personal Ops."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from typing import Any


_MAX_FILE_BYTES = 65_536
_MAX_PATCH_BYTES = 32_768
_MAX_PROCESS_OUTPUT = 20_000
_MAX_SEARCH_MATCHES = 50
_SENSITIVE_PARTS = {".env", ".git", ".ssh", "credentials", "secrets"}
_SENSITIVE_NAMES = {
    ".envrc",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "application-default-credentials.json",
    "application_default_credentials.json",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
    "service-account.json",
    "service_account.json",
    "secrets.toml",
}
_PROTECTED_PATHS = {
    "scripts/check_project_context.py",
    "personalops/contracts.py",
    "personalops/smoke.py",
    "personalops/validate.py",
    "personalops/workflow.json",
    "personalops/profile/runtime-contract.json",
    "personalops/profile/plugins/personalops-repository/__init__.py",
    "personalops/profile/plugins/personalops-repository/plugin.yaml",
}
_SECRET_KEY_PATTERN = re.compile(
    r"(^|[_-])(authorization|api[_-]?key|private[_-]?key|token|password|secret|credential|credentials)($|[_-])",
    re.IGNORECASE,
)
_REQUIRED_CONTEXT = ["PROJECT.md", "STATUS.md", "DECISIONS.md", "ARCHITECTURE.md"]
_WORKER_FIELDS = ["Objective", "Inputs", "Allowed changes", "Acceptance", "Evidence", "Stop"]
_RED_CATEGORIES = (
    "external_write",
    "external_communication",
    "publish",
    "deploy",
    "push",
    "merge",
    "paid_provider",
    "meaningful_delete",
    "credential_change",
    "security_change",
    "new_external_permission",
    "ambiguous_high_impact_decision",
)
_SAFE_OUTCOME_RECOMMENDATIONS = {
    "none",
    "review_verified_local_change",
    "inspect_and_verify_current_changes",
    "run_full_verification_for_draft_pr",
    "run_verification_before_red_push_or_pr",
    "run_context_and_full_checks",
}
_RED_OUTCOME_RECOMMENDATIONS = {
    f"request_approval_{category}": category for category in _RED_CATEGORIES
}
_RED_ACTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(?:^|[.;]\s*|\b(?:to|will|should|must)\s+)(?:push|pushed|merge|merged|deploy|deployed|publish|published|upload|uploaded|submit|submitted)(?![-_])\b",
        r"(?:^|[.;]\s*|\b(?:to|will|should|must)\s+)(?:release|released)\s+(?:an?\s+|the\s+)?(?:app|application|version|build|artifact|product)\b",
        r"\b(?:approve|authorize)\s+(?:an?\s+|the\s+)?(?:git\s+)?(?:push|merge|deploy|publication|release|upload|submission|send|email|post)\b",
        r"\b(?:open|opened|create|created|file|filed|close|closed|reopen|reopened|edit|edited|update|updated|label|labeled|comment on|commented on|reply to|replied to|approve|approved)\s+(?:an?\s+|the\s+)?(?:github\s+)?(?:pull request|pr|issue)\b",
        r"(?:^|[.;]\s*|\b(?:to|will|should|must)\s+)(?:send|sent|email|emailed|message|messaged|notify|notified|contact|contacted)\s+(?:an?\s+|the\s+|to\s+)?(?:user|customer|team|client|stakeholder|recipient|owner|report|results?|update|message|email|notification|artifact|file|link)\b",
        r"\b(?:reply|replied|respond|responded)\s+to\s+\S+",
        r"(?:^|[.;]\s*|\b(?:to|will|should|must)\s+)(?:post|posted|share|shared)\s+(?:an?\s+|the\s+)?(?:update|message|comment|reply|report|results?|artifact|file|link)\b",
        r"(?:^|[.;]\s*|\b(?:to|will|should|must)\s+)(?:share|shared)\s+with\s+\S+",
        r"\b(?:delete|deleted|remove|removed|destroy|destroyed|drop|dropped)\s+(?:an?\s+|the\s+)?(?:file|directory|folder|repository|repo|database|table|record|account|branch|artifact|dataset|data)\b",
        r"\b(?:create|created|change|changed|rotate|rotated|revoke|revoked|grant|granted|modify|modified|update|updated|delete|deleted|remove|removed|expose|exposed)\s+(?:an?\s+|the\s+)?(?:credential|secret|password|token|private key|permission|access|role|security setting)\b",
        r"\b(?:purchase|purchased|buy|bought|subscribe|subscribed|charge|charged|use|used|call|called|invoke|invoked)\s+(?:an?\s+|the\s+)?(?:paid|billable|subscription)\b",
        r"\b(?:external write|external communication|paid provider)\b",
        r"\b(?:approve|decide|choose)\s+(?:production|security|permission|paid|purchase|deployment)\b",
    )
)
_lock = threading.Lock()
_state_lock = threading.Lock()
_settings: dict[str, Any] = {}
_manifests: dict[str, dict[str, Any]] = {}
_child_parents: dict[str, str] = {}


def _setting(name: str, environment: str) -> str:
    value = _settings.get(name) or os.environ.get(environment, "")
    return str(value) if value else ""


def _repo_root() -> Path:
    raw = _setting("repository_root", "PERSONALOPS_REPO_ROOT")
    if not raw:
        raise RuntimeError("PERSONALOPS_REPO_ROOT is required")
    root = Path(raw)
    if not root.is_absolute():
        raise RuntimeError("PERSONALOPS_REPO_ROOT must be absolute")
    root = root.resolve(strict=True)
    if not (root / ".git").exists():
        completed = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0 or completed.stdout.strip() != "true":
            raise RuntimeError("PERSONALOPS_REPO_ROOT must be a Git checkout")
    return root


def _contract_root() -> Path:
    raw = _setting("contract_root", "PERSONALOPS_CONTRACT_ROOT")
    if not raw:
        raise RuntimeError("PERSONALOPS_CONTRACT_ROOT is required")
    root = Path(raw)
    if not root.is_absolute():
        raise RuntimeError("PERSONALOPS_CONTRACT_ROOT must be absolute")
    root = root.resolve(strict=True)
    if not (root / "workflow.json").is_file():
        raise RuntimeError("Personal Ops workflow contract is missing")
    return root


def _workflow() -> dict[str, Any]:
    payload = json.loads((_contract_root() / "workflow.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Personal Ops workflow contract must be an object")
    return payload


def _event_log() -> Path:
    raw = _setting("evidence_log", "PERSONALOPS_EVIDENCE_LOG")
    if not raw:
        raise RuntimeError("PERSONALOPS_EVIDENCE_LOG is required")
    path = Path(raw)
    if not path.is_absolute():
        raise RuntimeError("PERSONALOPS_EVIDENCE_LOG must be absolute")
    return path


def _redact_text(value: str) -> str:
    value = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
    value = re.sub(
        r"(?is)-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----.*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----",
        "[REDACTED PRIVATE KEY]",
        value,
    )
    key = r'(?:authorization|api[_-]?key|private[_-]?key|(?:access[_-]?|refresh[_-]?|auth[_-]?)?token|password|secret|credentials?)'
    value = re.sub(
        rf'(?im)^([ \t]*["\']?{key}["\']?[ \t]*:[ \t]*(?:[|>][+-]?[ \t]*)?)\r?\n(?:(?:[ \t]+[^\r\n]*(?:\r?\n|$))+)',
        r"\1\n  [REDACTED]\n",
        value,
    )
    value = re.sub(
        rf'(?is)(["\']?{key}["\']?\s*[:=]\s*)(["\'])(.*?)\2',
        r"\1\2[REDACTED]\2",
        value,
    )
    return re.sub(
        rf'(?i)(["\']?{key}["\']?\s*[:=]\s*)[^"\'\s\n\r,}}]+',
        r"\1[REDACTED]",
        value,
    )


def _redact_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_KEY_PATTERN.search(str(key)) else _redact_evidence(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact_evidence(child) for child in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _write_event(event: dict[str, Any]) -> None:
    path = _event_log()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_redact_evidence(event), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _emit(tool: str, result: dict[str, Any], *, session_id: str = "") -> str:
    safe_result = _redact_evidence(result)
    event = {"tool": tool, "session_id": session_id, **safe_result}
    _write_event(event)
    return json.dumps(safe_result, sort_keys=True)


def _fail(tool: str, reason_code: str, *, session_id: str = "", **extra: Any) -> str:
    return _emit(tool, {"ok": False, "reason_code": reason_code, **extra}, session_id=session_id)


def _is_sensitive(relative: Path) -> bool:
    lowered = {part.lower() for part in relative.parts}
    name = relative.name.lower()
    return (
        bool(lowered & _SENSITIVE_PARTS)
        or name in _SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
        or relative.as_posix().lower().endswith((".docker/config.json", ".kube/config"))
    )


def _is_protected(relative: Path) -> bool:
    value = relative.as_posix()
    return value == "tests" or value.startswith("tests/") or value in _PROTECTED_PATHS


def _has_symlink_component(root: Path, relative: Path) -> bool:
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return True
    return False


def _resolve_path(raw: Any, *, require_file: bool = True) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "path_required"
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts or _has_symlink_component(_repo_root(), relative):
        return None, "path_outside_repository"
    root = _repo_root()
    try:
        candidate = (root / relative).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None, "path_outside_repository"
    normalized = candidate.relative_to(root)
    if _is_sensitive(normalized):
        return None, "sensitive_path_forbidden"
    if require_file and not candidate.is_file():
        return None, "file_required"
    return candidate, None


def _run(argv: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], timeout=30)


def _repository_snapshot() -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    files = _git("ls-files", "-co", "--exclude-standard", "-z")
    if any(row.returncode != 0 for row in (head, tree, files)):
        raise RuntimeError("repository baseline unavailable")
    hashes: dict[str, str] = {}
    for raw in files.stdout.split("\0"):
        if not raw:
            continue
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("repository baseline contains unsafe path")
        candidate = _repo_root() / relative
        try:
            if candidate.is_symlink():
                payload = ("symlink:" + os.readlink(candidate)).encode("utf-8")
            elif candidate.is_file():
                payload = candidate.read_bytes()
            else:
                raise OSError(f"unsupported repository entry: {raw}")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"repository baseline unreadable: {raw}") from exc
        hashes[relative.as_posix()] = hashlib.sha256(payload).hexdigest()
    return {
        "commit": head.stdout.strip(),
        "tree": tree.stdout.strip(),
        "file_hashes": hashes,
    }


def _normalize_allowed_path(raw: str) -> str:
    value = raw.strip()
    relative = Path(value)
    root = _repo_root()
    if (
        not value
        or relative.is_absolute()
        or value != relative.as_posix()
        or relative.as_posix() in {".", ""}
        or ".." in relative.parts
        or _is_sensitive(relative)
        or _has_symlink_component(root, relative)
    ):
        raise ValueError("invalid_allowed_path")
    if _is_protected(relative):
        raise ValueError("protected_path_forbidden")
    candidate = root / relative
    if not candidate.is_file():
        raise ValueError("invalid_allowed_path")
    return relative.as_posix()


def _parse_worker_contract(goal: Any) -> dict[str, str]:
    if not isinstance(goal, str):
        raise ValueError("six_field_contract_required")
    fields: dict[str, str] = {}
    for line in goal.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in _WORKER_FIELDS and value.strip() and key not in fields:
            fields[key] = value.strip()
        elif key in _WORKER_FIELDS:
            raise ValueError("six_field_contract_required")
    if set(fields) != set(_WORKER_FIELDS):
        raise ValueError("six_field_contract_required")
    return fields


def _contains_red_action(value: Any) -> bool:
    if isinstance(value, str):
        normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return normalized in _RED_CATEGORIES or any(
            pattern.search(value.strip()) for pattern in _RED_ACTION_PATTERNS
        )
    if isinstance(value, dict):
        return any(_contains_red_action(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_red_action(child) for child in value)
    return False


def _consultation_sections(value: Any) -> list[tuple[str, str]]:
    strings: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, str):
            strings.append(item)
        elif isinstance(item, dict):
            for child in item.values():
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)

    collect(value)
    text = "\n".join(strings)
    labels = ("Decision needed", "Why it matters", "Options/tradeoffs", "Hermes recommendation")
    for label in labels:
        text = re.sub(rf"\s*{re.escape(label)}\s*:", f"\n{label}:", text, flags=re.IGNORECASE)
    sections = re.findall(
        r"(?im)^\s*(Decision needed|Why it matters|Options/tradeoffs|Hermes recommendation)\s*:\s*(\S.*)$",
        text,
    )
    return sections


def _consultation_complete(value: Any) -> bool:
    sections = _consultation_sections(value)
    labels = ("Decision needed", "Why it matters", "Options/tradeoffs", "Hermes recommendation")
    return [name.lower() for name, _ in sections] == [label.lower() for label in labels]


def _consultation_red_category(value: Any) -> str:
    sections = _consultation_sections(value)
    if not sections or sections[0][0].lower() != "decision needed":
        return ""
    normalized = re.sub(r"[^a-z0-9]+", "_", sections[0][1].lower()).strip("_")
    return normalized if normalized in _RED_CATEGORIES else ""


def _build_manifest(goal: str, *, session_id: str, tool_call_id: str) -> dict[str, Any]:
    fields = _parse_worker_contract(goal)
    allowed = tuple(
        _normalize_allowed_path(value)
        for value in (part.strip() for part in fields["Allowed changes"].split(","))
        if value
    )
    if not allowed or len(set(allowed)) != len(allowed):
        raise ValueError("invalid_allowed_path")
    baseline = _repository_snapshot()
    available_checks = _workflow().get("checks", {})
    acceptance = fields["Acceptance"].lower()
    required_checks = ["diff"]
    if isinstance(available_checks, dict):
        required_checks.extend(
            check_id
            for check_id in available_checks
            if check_id != "diff" and re.search(rf"\b{re.escape(check_id.lower())}\b", acceptance)
        )
    return {
        "parent_session_id": session_id,
        "delegate_tool_call_id": tool_call_id,
        "goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "allowed_paths": list(allowed),
        "required_checks": required_checks,
        "expected_evidence": fields["Evidence"],
        "baseline_commit": baseline["commit"],
        "baseline_tree": baseline["tree"],
        "baseline_file_hashes": baseline["file_hashes"],
        "allowed_file_hashes": {
            path: baseline["file_hashes"].get(path) for path in allowed
        },
        "child_session_id": "",
        "child_writes": {},
        "delegation_completed": False,
    }


def _changed_since_manifest(manifest: dict[str, Any]) -> list[str]:
    current = _repository_snapshot()
    if current["commit"] != manifest.get("baseline_commit") or current["tree"] != manifest.get("baseline_tree"):
        raise RuntimeError("repository baseline changed")
    before = manifest.get("baseline_file_hashes")
    if not isinstance(before, dict):
        raise RuntimeError("repository baseline unavailable")
    after = current["file_hashes"]
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def _remote_slug() -> str | None:
    result = _git("remote", "get-url", "origin")
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", value)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def _github_state(branch: str) -> dict[str, Any]:
    slug = _remote_slug()
    if not slug:
        return {"available": False, "issues": [], "pull_requests": []}
    gh = os.environ.get("PERSONALOPS_GH_BIN", "gh")
    try:
        issues = subprocess.run(
            [gh, "issue", "list", "--repo", slug, "--state", "open", "--limit", "20", "--json", "number,title,url"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        prs = subprocess.run(
            [gh, "pr", "list", "--repo", slug, "--state", "open", "--limit", "20", "--json", "number,title,url,isDraft,headRefName"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if issues.returncode != 0 or prs.returncode != 0:
            raise RuntimeError("GitHub read failed")
        issue_rows = json.loads(issues.stdout)
        pr_rows = json.loads(prs.stdout)
        if not isinstance(issue_rows, list) or not isinstance(pr_rows, list):
            raise ValueError("GitHub result must be a list")
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, json.JSONDecodeError):
        return {"available": False, "issues": [], "pull_requests": []}
    return {
        "available": True,
        "repository": slug,
        "issues": issue_rows,
        "pull_requests": pr_rows,
        "current_branch_pull_requests": [row for row in pr_rows if row.get("headRefName") == branch],
    }


def _inspect_repository(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    del args
    try:
        root = _repo_root()
        branch_result = _git("branch", "--show-current")
        head_result = _git("rev-parse", "HEAD")
        status_result = _git("status", "--short")
        log_result = _git("log", "-5", "--pretty=format:%H%x09%s")
        if any(row.returncode != 0 for row in (branch_result, head_result, status_result, log_result)):
            return _fail("personalops_inspect_repository", "git_inspection_failed", session_id=session_id)
        branch = branch_result.stdout.strip()
        status = [line for line in status_result.stdout.splitlines() if line]
        github = _github_state(branch)
        upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        divergence = _git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        behind = ahead = 0
        if divergence.returncode == 0:
            parts = divergence.stdout.split()
            if len(parts) == 2:
                behind, ahead = int(parts[0]), int(parts[1])
        draft = any(row.get("isDraft") for row in github.get("current_branch_pull_requests", []))
        if status:
            recommendation = "inspect_and_verify_current_changes"
        elif draft:
            recommendation = "run_full_verification_for_draft_pr"
        elif ahead:
            recommendation = "run_verification_before_red_push_or_pr"
        else:
            recommendation = "run_context_and_full_checks"
        result = {
            "ok": True,
            "repository_root": str(root),
            "branch": branch,
            "head": head_result.stdout.strip(),
            "clean": not status,
            "status": status,
            "upstream": upstream.stdout.strip() if upstream.returncode == 0 else None,
            "ahead": ahead,
            "behind": behind,
            "recent_commits": [
                {"sha": line.split("\t", 1)[0], "subject": line.split("\t", 1)[1]}
                for line in log_result.stdout.splitlines()
                if "\t" in line
            ],
            "context_files_missing": [name for name in _REQUIRED_CONTEXT if not (root / name).is_file()],
            "github": github,
            "recommended_action": recommendation,
        }
        return _emit("personalops_inspect_repository", result, session_id=session_id)
    except Exception as exc:
        return _fail("personalops_inspect_repository", "inspection_error", session_id=session_id, error=f"{type(exc).__name__}: {exc}")


def _read_file(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    arguments = dict(args or {})
    try:
        path, error = _resolve_path(arguments.get("path"))
        if error:
            return _fail("personalops_read_file", error, session_id=session_id)
        assert path is not None
        if path.stat().st_size > _MAX_FILE_BYTES:
            return _fail("personalops_read_file", "file_too_large", session_id=session_id)
        data = path.read_bytes()
        if b"\x00" in data:
            return _fail("personalops_read_file", "binary_file_forbidden", session_id=session_id)
        content = data.decode("utf-8")
        relative = str(path.relative_to(_repo_root()))
        return _emit(
            "personalops_read_file",
            {"ok": True, "path": relative, "sha256": hashlib.sha256(data).hexdigest(), "content": content},
            session_id=session_id,
        )
    except (OSError, UnicodeError, RuntimeError) as exc:
        return _fail("personalops_read_file", "read_error", session_id=session_id, error=f"{type(exc).__name__}: {exc}")


def _search_repository(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    arguments = dict(args or {})
    query = arguments.get("query")
    paths = arguments.get("paths", ["."])
    if not isinstance(query, str) or not query or len(query) > 200:
        return _fail("personalops_search_repository", "invalid_query", session_id=session_id)
    if not isinstance(paths, list) or not paths or not all(isinstance(item, str) for item in paths):
        return _fail("personalops_search_repository", "invalid_paths", session_id=session_id)
    files: set[Path] = set()
    for raw in paths:
        try:
            base = (_repo_root() / raw).resolve(strict=True)
            base.relative_to(_repo_root())
        except (OSError, ValueError):
            return _fail("personalops_search_repository", "path_outside_repository", session_id=session_id)
        candidates = [base] if base.is_file() else base.rglob("*")
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                relative = candidate.resolve(strict=True).relative_to(_repo_root())
            except (OSError, ValueError):
                continue
            if _is_sensitive(relative) or candidate.stat().st_size > _MAX_FILE_BYTES:
                continue
            files.add(candidate)
    matches: list[dict[str, Any]] = []
    for path in sorted(files):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if query in line:
                matches.append({"path": str(path.relative_to(_repo_root())), "line": number, "text": line[:500]})
                if len(matches) >= _MAX_SEARCH_MATCHES:
                    break
        if len(matches) >= _MAX_SEARCH_MATCHES:
            break
    return _emit("personalops_search_repository", {"ok": True, "matches": matches, "truncated": len(matches) >= _MAX_SEARCH_MATCHES}, session_id=session_id)


def _run_named_check(check_id: Any) -> dict[str, Any]:
    checks = _workflow().get("checks", {})
    row = checks.get(check_id) if isinstance(check_id, str) else None
    if not isinstance(row, dict):
        return {"ok": False, "reason_code": "check_not_approved", "check_id": check_id}
    argv = row.get("command")
    timeout = row.get("timeout_seconds", 600)
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return {"ok": False, "reason_code": "invalid_check_contract", "check_id": check_id}
    try:
        completed = _run(argv, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason_code": "check_runtime_error", "check_id": check_id, "error": f"{type(exc).__name__}: {exc}"}
    output = (completed.stdout + completed.stderr)[-_MAX_PROCESS_OUTPUT:]
    return {
        "ok": completed.returncode == 0,
        "check_id": check_id,
        "argv": argv,
        "returncode": completed.returncode,
        "output": output,
        "truncated": len(completed.stdout) + len(completed.stderr) > _MAX_PROCESS_OUTPUT,
    }


def _run_check(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    result = _run_named_check(dict(args or {}).get("check_id"))
    return _emit("personalops_run_check", result, session_id=session_id)


def _is_delegated_child_context() -> bool:
    try:
        from agent.delegation_context import is_delegated_child_context
    except ImportError:
        return False
    return bool(is_delegated_child_context())


def _apply_patch(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    if not _is_delegated_child_context():
        return _fail("personalops_apply_patch", "delegated_child_required", session_id=session_id)
    arguments = dict(args or {})
    try:
        path, error = _resolve_path(arguments.get("path"))
        if error:
            return _fail("personalops_apply_patch", error, session_id=session_id)
        assert path is not None
        with _state_lock:
            parent_session_id = _child_parents.get(session_id, "")
            manifest = _manifests.get(parent_session_id)
            allowed_paths = set(manifest.get("allowed_paths", [])) if isinstance(manifest, dict) else set()
        relative_path = path.relative_to(_repo_root()).as_posix()
        if not parent_session_id or relative_path not in allowed_paths:
            return _fail("personalops_apply_patch", "path_not_allowed", session_id=session_id, path=relative_path)
        old = arguments.get("old_text")
        new = arguments.get("new_text")
        expected = arguments.get("expected_sha256")
        if not all(isinstance(item, str) for item in (old, new, expected)) or not old:
            return _fail("personalops_apply_patch", "invalid_patch", session_id=session_id)
        if len(old.encode("utf-8")) + len(new.encode("utf-8")) > _MAX_PATCH_BYTES:
            return _fail("personalops_apply_patch", "patch_too_large", session_id=session_id)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            return _fail("personalops_apply_patch", "file_changed", session_id=session_id)
        if b"\x00" in data:
            return _fail("personalops_apply_patch", "binary_file_forbidden", session_id=session_id)
        content = data.decode("utf-8")
        if content.count(old) != 1:
            return _fail("personalops_apply_patch", "patch_match_must_be_unique", session_id=session_id)
        updated = content.replace(old, new, 1)
        mode = path.stat().st_mode
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(updated)
            temporary = Path(handle.name)
        os.chmod(temporary, mode)
        with _state_lock:
            current_parent = _child_parents.get(session_id, "")
            current_manifest = _manifests.get(current_parent)
            if current_parent != parent_session_id or current_manifest is not manifest:
                temporary.unlink(missing_ok=True)
                return _fail("personalops_apply_patch", "manifest_binding_changed", session_id=session_id)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                temporary.unlink(missing_ok=True)
                return _fail("personalops_apply_patch", "file_changed", session_id=session_id)
            os.replace(temporary, path)
            updated_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            current_manifest.setdefault("child_writes", {})[relative_path] = updated_sha256
        return _emit(
            "personalops_apply_patch",
            {
                "ok": True,
                "path": relative_path,
                "sha256": updated_sha256,
                "parent_session_id": parent_session_id,
            },
            session_id=session_id,
        )
    except (OSError, UnicodeError, RuntimeError) as exc:
        return _fail("personalops_apply_patch", "patch_error", session_id=session_id, error=f"{type(exc).__name__}: {exc}")


def _verify_change(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    arguments = dict(args or {})
    check_ids = arguments.get("check_ids")
    if not isinstance(check_ids, list) or not check_ids or not all(isinstance(item, str) for item in check_ids):
        return _fail("personalops_verify_change", "check_ids_required", session_id=session_id)
    with _state_lock:
        manifest = _manifests.get(session_id)
        manifest = dict(manifest) if isinstance(manifest, dict) else None
    if manifest is None:
        return _fail("personalops_verify_change", "trusted_manifest_missing", session_id=session_id)
    if not manifest.get("delegation_completed"):
        return _fail("personalops_verify_change", "delegation_not_completed", session_id=session_id)
    required_checks = manifest.get("required_checks", [])
    missing_checks = sorted(set(required_checks) - set(check_ids))
    if missing_checks:
        return _fail(
            "personalops_verify_change", "required_checks_missing", session_id=session_id, missing_check_ids=missing_checks
        )
    try:
        changed = _changed_since_manifest(manifest)
    except RuntimeError as exc:
        return _fail(
            "personalops_verify_change", "baseline_unavailable", session_id=session_id, error=str(exc)
        )
    if not changed:
        return _fail("personalops_verify_change", "no_post_delegation_change", session_id=session_id)
    sensitive = [path for path in changed if _is_sensitive(Path(path))]
    if sensitive:
        return _fail(
            "personalops_verify_change", "sensitive_path_changed", session_id=session_id, sensitive_paths=sensitive
        )
    protected = [path for path in changed if _is_protected(Path(path))]
    if protected:
        return _fail(
            "personalops_verify_change", "protected_path_changed", session_id=session_id, protected_paths=protected
        )
    unexpected = sorted(set(changed) - set(manifest.get("allowed_paths", [])))
    if unexpected:
        return _fail(
            "personalops_verify_change",
            "changed_path_not_allowed",
            session_id=session_id,
            changed_paths=changed,
            unexpected_paths=unexpected,
        )
    child_writes = manifest.get("child_writes")
    if not isinstance(child_writes, dict) or not child_writes:
        return _fail("personalops_verify_change", "no_child_writes", session_id=session_id)
    if set(changed) != set(child_writes):
        return _fail(
            "personalops_verify_change",
            "child_write_attribution_failed",
            session_id=session_id,
            changed_paths=changed,
            child_write_paths=sorted(child_writes),
        )
    current_hashes = _repository_snapshot()["file_hashes"]
    if any(current_hashes.get(path) != expected for path, expected in child_writes.items()):
        return _fail(
            "personalops_verify_change", "child_write_attribution_failed", session_id=session_id
        )
    checks = [_run_named_check(check_id) for check_id in check_ids]
    result = {
        "ok": bool(checks) and all(row.get("ok") for row in checks),
        "changed_paths": changed,
        "checks": checks,
        "manifest": {
            "parent_session_id": manifest["parent_session_id"],
            "delegate_tool_call_id": manifest["delegate_tool_call_id"],
            "child_session_id": manifest["child_session_id"],
            "allowed_paths": manifest["allowed_paths"],
            "required_checks": manifest["required_checks"],
            "baseline_commit": manifest["baseline_commit"],
            "baseline_tree": manifest["baseline_tree"],
            "allowed_file_hashes": manifest["allowed_file_hashes"],
            "expected_evidence": manifest["expected_evidence"],
            "child_writes": child_writes,
        },
    }
    return _emit("personalops_verify_change", result, session_id=session_id)


def _record_outcome(args: dict[str, Any] | None, session_id: str = "", **_: Any) -> str:
    arguments = dict(args or {})
    required = _workflow().get("final_status_fields", [])
    missing = [field for field in required if not isinstance(arguments.get(field), str) or not arguments[field].strip()]
    if missing:
        return _fail("personalops_record_outcome", "missing_final_status_fields", session_id=session_id, missing=missing)
    recommendation = arguments["recommended_action"].strip()
    decision = arguments["decision_needed"].strip()
    red_category = _RED_OUTCOME_RECOMMENDATIONS.get(recommendation)
    boundary_valid = (
        recommendation in _SAFE_OUTCOME_RECOMMENDATIONS and decision == "none"
    ) or (
        red_category is not None and decision == red_category
    )
    if not boundary_valid:
        return _fail(
            "personalops_record_outcome",
            "invalid_outcome_boundary",
            session_id=session_id,
        )
    return _emit("personalops_record_outcome", {"ok": True, "outcome": {field: arguments[field].strip() for field in required}}, session_id=session_id)


def _runtime_guard_status() -> tuple[bool, list[str]]:
    raw = _setting("hermes_root", "PERSONALOPS_HERMES_ROOT")
    if not raw:
        return False, ["PERSONALOPS_HERMES_ROOT is required"]
    try:
        hermes = Path(raw).resolve(strict=True)
        contract = json.loads((_contract_root() / "runtime-contract.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        return False, [f"runtime guard load failed: {exc}"]
    rows = contract.get("files") if isinstance(contract, dict) else None
    if not isinstance(rows, list) or not rows:
        return False, ["runtime guard contract is empty"]
    errors: list[str] = []
    for row in rows:
        relative = row.get("path") if isinstance(row, dict) else None
        expected = row.get("sha256") if isinstance(row, dict) else None
        if not isinstance(relative, str) or not isinstance(expected, str):
            errors.append("runtime guard file entry is invalid")
            continue
        candidate = (hermes / relative).resolve()
        try:
            candidate.relative_to(hermes)
        except ValueError:
            errors.append(f"runtime guard path escape: {relative}")
            continue
        if not candidate.is_file():
            errors.append(f"runtime guard file missing: {relative}")
        elif hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            errors.append(f"runtime guard hash mismatch: {relative}")
    return not errors, errors


def _pre_tool_call(
    tool_name: str = "", args: Any = None, tool_call_id: str = "", session_id: str = "", **_: Any
):
    if tool_name != "delegate_task":
        event = {
            "tool": tool_name,
            "phase": "pre",
            "tool_call_id": tool_call_id,
            "session_id": session_id,
            "action": "allow",
        }
        if tool_name == "clarify":
            event["red_category"] = _consultation_red_category(args)
            event["red_boundary"] = bool(event["red_category"]) or _contains_red_action(args)
            event["consultation_complete"] = _consultation_complete(args)
        _write_event(event)
        return None
    arguments = args if isinstance(args, dict) else {}
    guard_ok, guard_errors = _runtime_guard_status()
    if not guard_ok:
        message = "Personal Ops blocked delegation because the runtime guard is invalid: " + "; ".join(guard_errors)
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "action": "block", "reason_code": "runtime_guard_invalid"})
        return {"action": "block", "message": message}
    if not session_id:
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "action": "block", "reason_code": "session_id_required"})
        return {"action": "block", "reason_code": "session_id_required", "message": "Personal Ops requires a session identity before delegation."}
    with _state_lock:
        already_delegated = session_id in _manifests
    if already_delegated:
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "session_id": session_id, "action": "block", "reason_code": "one_delegation_limit"})
        return {"action": "block", "reason_code": "one_delegation_limit", "message": "Personal Ops permits exactly one delegation per session."}
    tasks = arguments.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 1 or not isinstance(tasks[0], dict):
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "action": "block", "reason_code": "one_task_required"})
        return {"action": "block", "message": "Personal Ops requires exactly one delegated task using the six-field worker contract."}
    goal = tasks[0].get("goal")
    try:
        manifest = _build_manifest(goal, session_id=session_id, tool_call_id=tool_call_id)
    except ValueError as exc:
        reason_code = str(exc)
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "session_id": session_id, "action": "block", "reason_code": reason_code})
        if reason_code == "six_field_contract_required":
            message = "Personal Ops requires the exact six-field worker contract: " + ", ".join(_WORKER_FIELDS) + "."
        elif reason_code == "protected_path_forbidden":
            message = "Personal Ops does not permit a delegated worker to edit its checker, verifier, policy, or tests."
        else:
            message = "Personal Ops requires exact existing non-sensitive regular files in Allowed changes."
        return {"action": "block", "reason_code": reason_code, "message": message}
    except RuntimeError as exc:
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "session_id": session_id, "action": "block", "reason_code": "baseline_unavailable"})
        return {"action": "block", "reason_code": "baseline_unavailable", "message": f"Personal Ops could not establish a trusted repository baseline: {exc}"}
    with _state_lock:
        if session_id in _manifests:
            concurrent_duplicate = True
        else:
            _manifests[session_id] = manifest
            concurrent_duplicate = False
    if concurrent_duplicate:
        _write_event({"tool": tool_name, "phase": "pre", "tool_call_id": tool_call_id, "session_id": session_id, "action": "block", "reason_code": "one_delegation_limit"})
        return {"action": "block", "reason_code": "one_delegation_limit", "message": "Personal Ops permits exactly one delegation per session."}
    _write_event({
        "tool": tool_name,
        "phase": "pre",
        "tool_call_id": tool_call_id,
        "session_id": session_id,
        "action": "allow",
        "delegation_number": 1,
        "manifest": {
            key: manifest[key]
            for key in (
                "allowed_paths", "required_checks", "expected_evidence", "baseline_commit",
                "baseline_tree", "allowed_file_hashes", "goal_sha256",
            )
        },
    })
    return None


def _on_session_start(session_id: str = "", parent_session_id: str = "", **_: Any) -> None:
    if not session_id or parent_session_id:
        return
    with _state_lock:
        stale = _manifests.pop(session_id, None)
        if stale and stale.get("child_session_id"):
            _child_parents.pop(stale["child_session_id"], None)


def _on_session_end(session_id: str = "", **_: Any) -> None:
    # Hermes emits this hook at turn boundaries. A background child can finish
    # between turns, so trusted state must survive until session finalization.
    del session_id


def _on_session_finalize(session_id: str = "", **_: Any) -> None:
    if not session_id:
        return
    with _state_lock:
        if session_id in _child_parents:
            # The parent owns this state and removes it when the parent session
            # is finalized. Child finalization may precede the parent post-hook.
            return
        manifest = _manifests.pop(session_id, None)
        if manifest and manifest.get("child_session_id"):
            _child_parents.pop(manifest["child_session_id"], None)


def _subagent_start(
    parent_session_id: str = "", child_session_id: str = "", child_goal: str = "", **_: Any
) -> None:
    goal_sha256 = hashlib.sha256(child_goal.encode("utf-8")).hexdigest() if isinstance(child_goal, str) else ""
    with _state_lock:
        manifest = _manifests.get(parent_session_id)
        bound = bool(
            manifest
            and child_session_id
            and manifest.get("goal_sha256") == goal_sha256
            and not manifest.get("child_session_id")
        )
        if bound:
            manifest["child_session_id"] = child_session_id
            _child_parents[child_session_id] = parent_session_id
    _write_event({
        "tool": "delegate_task",
        "phase": "child_start",
        "parent_session_id": parent_session_id,
        "child_session_id": child_session_id,
        "manifest_bound": bound,
    })


def _post_tool_call(
    tool_name: str = "", tool_call_id: str = "", result: Any = None, session_id: str = "",
    status: str = "", **_: Any
) -> None:
    completed = status in {"", "ok"} and result is not None
    if tool_name == "delegate_task" and completed:
        with _state_lock:
            manifest = _manifests.get(session_id)
            if manifest and manifest.get("delegate_tool_call_id") == tool_call_id and manifest.get("child_session_id"):
                manifest["delegation_completed"] = True
    _write_event({"tool": tool_name, "phase": "post", "tool_call_id": tool_call_id, "session_id": session_id, "completed": completed, "result_present": result is not None})


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}


_PROMPT = """You are Hermes Desktop Lite for Ajanee. Use personalops_inspect_repository before making repository claims. Green actions are read-only inspection and named checks; perform them autonomously. Yellow actions are one bounded delegated child making reversible local edits through personalops_apply_patch; give the child Objective, Inputs, Allowed changes, Acceptance, Evidence, and Stop, then independently call personalops_verify_change. Red actions include external writes or communications, publish/deploy, push/merge, paid providers, deletion, credentials/security, new permissions, or ambiguous high-impact choices. For Red work call clarify with Decision needed, Why it matters, Options/tradeoffs, and Hermes recommendation; Decision needed must be the exact Red category token. Then wait. Never use ClickHouse for this workflow. Before the concise final answer, call personalops_record_outcome with current_state, recommended_action, action_taken, verification, and decision_needed. Use only the tool's enum tokens: a Red recommendation is request_approval_<category> with the matching decision_needed category; otherwise decision_needed is none. Do not expose internal orchestration logs."""


def register(ctx) -> None:
    global _settings, _manifests, _child_parents
    _settings = {
        name: ctx.get_config(name, "")
        for name in ("repository_root", "contract_root", "evidence_log", "hermes_root")
    }
    _manifests = {}
    _child_parents = {}
    ctx.register_system_prompt_section("personalops.desktop-lite", _PROMPT, position="after_memory", max_chars=4000)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("subagent_start", _subagent_start)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("on_session_finalize", _on_session_finalize)
    definitions = [
        ("personalops_inspect_repository", "Inspect the approved repository, Git state, context files, and read-only GitHub metadata.", {}, [], _inspect_repository),
        ("personalops_read_file", "Read one bounded UTF-8 file inside the approved repository.", {"path": {"type": "string"}}, ["path"], _read_file),
        ("personalops_search_repository", "Search bounded repository text without leaving the approved root.", {"query": {"type": "string"}, "paths": {"type": "array", "items": {"type": "string"}}}, ["query"], _search_repository),
        ("personalops_run_check", "Run one approved deterministic repository check by identifier.", {"check_id": {"type": "string", "enum": ["context", "diff", "full"]}}, ["check_id"], _run_check),
        ("personalops_apply_patch", "Apply one compare-and-swap text replacement. Delegated child only.", {"path": {"type": "string"}, "expected_sha256": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, ["path", "expected_sha256", "old_text", "new_text"], _apply_patch),
        (
            "personalops_verify_change",
            "Independently inspect changed paths and run approved checks after a worker.",
            {
                "check_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["context", "diff", "full"]},
                }
            },
            ["check_ids"],
            _verify_change,
        ),
        (
            "personalops_record_outcome",
            "Record the structured final status before answering Ajanee.",
            {
                "current_state": {"type": "string"},
                "recommended_action": {
                    "type": "string",
                    "enum": sorted(_SAFE_OUTCOME_RECOMMENDATIONS | set(_RED_OUTCOME_RECOMMENDATIONS)),
                },
                "action_taken": {"type": "string"},
                "verification": {"type": "string"},
                "decision_needed": {"type": "string", "enum": ["none", *_RED_CATEGORIES]},
            },
            ["current_state", "recommended_action", "action_taken", "verification", "decision_needed"],
            _record_outcome,
        ),
    ]
    for name, description, properties, required, handler in definitions:
        ctx.register_tool(name=name, toolset="personalops_repository", schema=_schema(name, description, properties, required), handler=handler)
