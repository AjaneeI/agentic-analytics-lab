"""Deterministic, repository-local policy retrieval for System Benchmark v1."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_CORPUS_ROOT = (
    Path(__file__).resolve().parents[2] / "evals" / "system_benchmark" / "corpus"
)
MAX_TOP_K = 5
MAX_EXCERPT_CHARS = 600

_CALENDAR_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")


class PolicyCorpusError(ValueError):
    """Raised when the local policy corpus violates its read-only contract."""


@dataclass(frozen=True)
class PolicyEvidence:
    """Auditable section-level evidence returned by policy retrieval."""

    document_id: str
    document_version: str
    section_id: str
    excerpt: str
    effective_date: str
    status: str


@dataclass(frozen=True)
class _ManifestDocument:
    document_id: str
    version: str
    status: str
    effective_date: date
    scope: str
    path: Path


def retrieve_policy(
    query: str,
    *,
    as_of: str | None = None,
    top_k: int = 3,
) -> list[PolicyEvidence]:
    """Return deterministic section-level policy evidence for a text query."""

    if not isinstance(query, str):
        raise TypeError("query must be a string")
    cutoff = _parse_calendar_date(as_of, field="as_of") if as_of is not None else None
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")
    if not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")
    if not query.strip():
        return []

    documents = _load_manifest(DEFAULT_CORPUS_ROOT)
    selected = _select_document_versions(documents, cutoff=cutoff)
    query_tokens = set(_tokens(query))

    candidates: list[tuple[int, PolicyEvidence]] = []
    for document in selected:
        content = document.path.read_text(encoding="utf-8")
        for section_id, heading, body in _sections(content, document.path):
            score = _score_section(
                query_tokens,
                document.document_id,
                document.path,
                heading,
                body,
            )
            if score <= 0:
                continue
            excerpt = _bounded_excerpt(heading, body)
            candidates.append(
                (
                    score,
                    PolicyEvidence(
                        document_id=document.document_id,
                        document_version=document.version,
                        section_id=section_id,
                        excerpt=excerpt,
                        effective_date=document.effective_date.isoformat(),
                        status=document.status,
                    ),
                )
            )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].document_id,
            item[1].document_version,
            item[1].section_id,
        )
    )
    return [evidence for _, evidence in candidates[:top_k]]


def _load_manifest(root: Path) -> list[_ManifestDocument]:
    resolved_root = root.resolve()
    manifest_path = resolved_root / "manifest.json"

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyCorpusError(f"Unable to read policy corpus manifest: {exc}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("documents"), list):
        raise PolicyCorpusError("Policy corpus manifest must contain a documents list")
    corpus_version = raw.get("corpus_version")
    if not isinstance(corpus_version, str) or not corpus_version.strip():
        raise PolicyCorpusError(
            "Policy corpus manifest field 'corpus_version' must be a non-empty string"
        )

    documents: list[_ManifestDocument] = []
    seen: set[tuple[str, str]] = set()
    seen_effective_dates: set[tuple[str, date]] = set()

    for index, item in enumerate(raw["documents"]):
        if not isinstance(item, dict):
            raise PolicyCorpusError(f"Manifest document {index} must be an object")

        document_id = _required_text(item, "document_id", index)
        version = _required_text(item, "version", index)
        status = _required_text(item, "status", index)
        scope = _required_text(item, "scope", index)
        relative_path = _required_text(item, "path", index)
        effective_text = _required_text(item, "effective_date", index)

        if status not in {"current", "superseded"}:
            raise PolicyCorpusError(
                f"Manifest document {document_id!r} has unsupported status {status!r}"
            )

        try:
            effective_date = _parse_calendar_date(effective_text, field="effective_date")
        except ValueError as exc:
            raise PolicyCorpusError(
                f"Manifest document {document_id!r} has invalid effective_date"
            ) from exc

        candidate_path = (resolved_root / relative_path).resolve()
        if candidate_path == resolved_root or resolved_root not in candidate_path.parents:
            raise PolicyCorpusError(
                f"Manifest path escapes policy corpus root: {relative_path!r}"
            )
        if candidate_path.suffix.lower() != ".md":
            raise PolicyCorpusError(
                f"Manifest path must reference a Markdown policy file: {relative_path!r}"
            )
        if not candidate_path.is_file():
            raise PolicyCorpusError(
                f"Manifest path does not exist: {relative_path!r}"
            )

        identity = (document_id, version)
        if identity in seen:
            raise PolicyCorpusError(
                f"Duplicate policy document/version in manifest: {document_id} {version}"
            )
        seen.add(identity)

        effective_identity = (document_id, effective_date)
        if effective_identity in seen_effective_dates:
            raise PolicyCorpusError(
                "Policy versions for one document_id must have unique effective_date "
                f"values: {document_id} {effective_date.isoformat()}"
            )
        seen_effective_dates.add(effective_identity)

        documents.append(
            _ManifestDocument(
                document_id=document_id,
                version=version,
                status=status,
                effective_date=effective_date,
                scope=scope,
                path=candidate_path,
            )
        )

    if not documents:
        raise PolicyCorpusError("Policy corpus manifest must not be empty")

    current_counts: dict[str, int] = {}
    versions_by_document: dict[str, list[_ManifestDocument]] = {}
    for document in documents:
        current_counts.setdefault(document.document_id, 0)
        versions_by_document.setdefault(document.document_id, []).append(document)
        if document.status == "current":
            current_counts[document.document_id] += 1
    invalid_current = {
        document_id: count
        for document_id, count in current_counts.items()
        if count != 1
    }
    if invalid_current:
        details = ", ".join(
            f"{document_id}={count}"
            for document_id, count in sorted(invalid_current.items())
        )
        raise PolicyCorpusError(
            "Each policy document_id must have exactly one current version: "
            + details
        )

    for document_id, versions in versions_by_document.items():
        current = next(doc for doc in versions if doc.status == "current")
        newer_superseded = [
            doc for doc in versions
            if doc.status == "superseded" and doc.effective_date > current.effective_date
        ]
        if newer_superseded:
            latest = max(newer_superseded, key=lambda doc: doc.effective_date)
            raise PolicyCorpusError(
                "Current policy version must have the latest effective_date for "
                f"{document_id}: current={current.effective_date.isoformat()}, "
                f"newer_superseded={latest.effective_date.isoformat()}"
            )

    return documents


def _required_text(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PolicyCorpusError(
            f"Manifest document {index} field {key!r} must be a non-empty string"
        )
    return value.strip()


def _parse_calendar_date(value: str, *, field: str) -> date:
    """Accept only ASCII calendar dates, not compact or ISO week-date forms."""
    message = f"{field} must be a valid calendar date in YYYY-MM-DD format"
    if not isinstance(value, str) or _CALENDAR_DATE_RE.fullmatch(value) is None:
        raise ValueError(message)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(message) from exc


def _select_document_versions(
    documents: list[_ManifestDocument],
    *,
    cutoff: date | None,
) -> list[_ManifestDocument]:
    if cutoff is None:
        return sorted(
            (doc for doc in documents if doc.status == "current"),
            key=lambda doc: (doc.document_id, doc.version),
        )

    applicable: dict[str, _ManifestDocument] = {}
    for document in documents:
        if document.effective_date > cutoff:
            continue

        previous = applicable.get(document.document_id)
        if previous is None or (
            document.effective_date,
            document.version,
        ) > (
            previous.effective_date,
            previous.version,
        ):
            applicable[document.document_id] = document

    return [applicable[key] for key in sorted(applicable)]


def _sections(content: str, source: Path) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    seen_ids: set[str] = set()

    def flush() -> None:
        if current_heading is None:
            return
        section_id = _slug(current_heading)
        if not section_id:
            raise PolicyCorpusError(f"Policy section heading is not identifiable: {source}")
        if section_id in seen_ids:
            raise PolicyCorpusError(
                f"Duplicate section id {section_id!r} in policy document {source.name}"
            )
        seen_ids.add(section_id)
        sections.append(
            (
                section_id,
                current_heading,
                "\n".join(current_lines).strip(),
            )
        )

    for line in content.splitlines():
        match = _SECTION_RE.match(line)
        if match:
            flush()
            current_heading = match.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    flush()

    if not sections:
        raise PolicyCorpusError(f"Policy document has no level-2 sections: {source.name}")
    return sections


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _slug(text: str) -> str:
    return "-".join(_tokens(text))


def _score_section(
    query_tokens: set[str],
    document_id: str,
    source: Path,
    heading: str,
    body: str,
) -> int:
    document_tokens = set(_tokens(document_id)) | set(_tokens(source.stem))
    heading_tokens = set(_tokens(heading))
    body_tokens = set(_tokens(body))
    section_score = (
        3 * len(query_tokens & heading_tokens)
        + len(query_tokens & body_tokens)
    )
    # A complete document-id query should retrieve that source as a document,
    # while partial source-name overlap remains only a tie-break/fallback.
    document_id_tokens = set(_tokens(document_id))
    exact_source_match = query_tokens == document_id_tokens
    if exact_source_match:
        return 1_000 + section_score
    source_match = int(bool(query_tokens & document_tokens))
    return 2 * section_score + source_match


def _bounded_excerpt(heading: str, body: str) -> str:
    normalized = " ".join(f"{heading}: {body}".split())
    return normalized[:MAX_EXCERPT_CHARS]
