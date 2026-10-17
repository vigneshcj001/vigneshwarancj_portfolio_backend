"""Load canonical portfolio content from structured Markdown documents."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONTENT_ROOT = Path(__file__).parent.parent / "knowledge"


@dataclass(frozen=True)
class ContentDocument:
    path: str
    kind: str
    title: str
    order: int
    data: Any
    body: str


def _split_markdown(text: str, path: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError(f"Missing YAML frontmatter: {path}")
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"Unclosed YAML frontmatter: {path}")
    metadata = yaml.safe_load(normalized[4:end])
    if not isinstance(metadata, dict):
        raise ValueError(f"Frontmatter must be a mapping: {path}")
    return metadata, normalized[end + 5:].strip()


@lru_cache(maxsize=1)
def load_documents() -> tuple[ContentDocument, ...]:
    root = CONTENT_ROOT.resolve()
    index_path = root / "index.md"
    index, _ = _split_markdown(index_path.read_text(encoding="utf-8"), "index.md")
    if index.get("schema") != "portfolio-okf-v1":
        raise ValueError("knowledge/index.md must use schema portfolio-okf-v1")
    paths = index.get("entries")
    if not isinstance(paths, list) or not paths:
        raise ValueError("knowledge/index.md must list entries")
    if len(paths) != len(set(paths)):
        raise ValueError("knowledge/index.md contains duplicate entries")

    documents: list[ContentDocument] = []
    for relative in paths:
        if not isinstance(relative, str):
            raise ValueError("Every knowledge entry must be a relative Markdown path")
        candidate = (root / relative).resolve()
        if root not in candidate.parents or candidate.suffix.lower() != ".md":
            raise ValueError(f"Unsafe knowledge entry path: {relative}")
        metadata, body = _split_markdown(candidate.read_text(encoding="utf-8"), relative)
        kind = metadata.get("type")
        title = metadata.get("title")
        if not isinstance(kind, str) or not isinstance(title, str) or "data" not in metadata:
            raise ValueError(f"Knowledge entry needs type, title, and data: {relative}")
        order = metadata.get("order", 0)
        if not isinstance(order, int):
            raise ValueError(f"Knowledge order must be an integer: {relative}")
        documents.append(ContentDocument(relative, kind, title, order, metadata["data"], body))
    return tuple(documents)


@lru_cache(maxsize=1)
def load_portfolio() -> dict[str, Any]:
    portfolio: dict[str, Any] = {
        "personal": {},
        "education": [],
        "certifications": [],
        "research_interests": [],
        "publications": [],
        "skills": {},
        "projects": {},
        "employer": {},
        "work_experience": [],
        "stats": {},
    }
    ordered: dict[str, list[tuple[int, Any]]] = {
        "education": [],
        "certifications": [],
        "publications": [],
        "work_experience": [],
    }

    for document in load_documents():
        if document.kind == "profile":
            if not isinstance(document.data, dict):
                raise ValueError("Profile data must be a mapping")
            for key in ("personal", "employer", "stats"):
                portfolio[key] = document.data.get(key, {})
        elif document.kind == "education":
            ordered["education"].append((document.order, document.data))
        elif document.kind == "certification":
            ordered["certifications"].append((document.order, document.data))
        elif document.kind == "research_interests":
            portfolio["research_interests"] = document.data
        elif document.kind == "publication":
            ordered["publications"].append((document.order, document.data))
        elif document.kind == "skills":
            portfolio["skills"] = document.data
        elif document.kind == "project":
            portfolio["projects"][document.title] = document.data
        elif document.kind == "experience":
            ordered["work_experience"].append((document.order, document.data))
        else:
            raise ValueError(f"Unsupported knowledge type {document.kind!r} in {document.path}")

    for key, items in ordered.items():
        portfolio[key] = [value for _, value in sorted(items, key=lambda item: item[0])]

    required = ("personal", "education", "skills", "projects", "work_experience")
    missing = [key for key in required if not portfolio[key]]
    if missing:
        raise ValueError(f"Structured Markdown content missing required sections: {', '.join(missing)}")
    return portfolio


def searchable_text(document: ContentDocument) -> str:
    structured = yaml.safe_dump(document.data, allow_unicode=True, sort_keys=False, width=120)
    return f"{document.body}\n\n{structured}".strip()
