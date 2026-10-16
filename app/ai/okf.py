import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_BUNDLE_PATH = Path(__file__).parent.parent.parent / "knowledge"
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*", re.IGNORECASE)
_STOP_WORDS = {
    "a", "about", "and", "are", "can", "do", "does", "for", "he", "her",
    "his", "how", "i", "in", "is", "it", "me", "of", "on", "the", "to",
    "what", "when", "where", "which", "who", "with", "you",
}


@dataclass(frozen=True)
class KnowledgeEntry:
    path: str
    title: str
    kind: str
    tags: str
    body: str


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() not in {"entries"}:
            metadata[key.strip()] = value.strip()
    return metadata, text[end + 5:].strip()


def _indexed_paths(index_text: str) -> list[str]:
    if not index_text.startswith("---\n"):
        raise ValueError("OKF index.md requires YAML frontmatter")
    end = index_text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("OKF index.md frontmatter is not closed")
    lines = index_text[4:end].splitlines()
    collecting = False
    entries: list[str] = []
    for line in lines:
        if line.strip() == "entries:":
            collecting = True
            continue
        if collecting and re.match(r"^\s+-\s+", line):
            entries.append(re.sub(r"^\s+-\s+", "", line).strip())
        elif collecting and line.strip():
            break
    if not entries:
        raise ValueError("OKF index.md must list at least one entry")
    return entries


@lru_cache(maxsize=1)
def load_bundle() -> tuple[KnowledgeEntry, ...]:
    root = _BUNDLE_PATH.resolve()
    index = root / "index.md"
    paths = _indexed_paths(index.read_text(encoding="utf-8"))
    entries: list[KnowledgeEntry] = []
    for relative in paths:
        candidate = (root / relative).resolve()
        if root not in candidate.parents or candidate.suffix.lower() != ".md":
            raise ValueError(f"Unsafe OKF entry path: {relative}")
        metadata, body = _frontmatter(candidate.read_text(encoding="utf-8"))
        entries.append(KnowledgeEntry(
            path=relative,
            title=metadata.get("title", candidate.stem),
            kind=metadata.get("type", "concept"),
            tags=metadata.get("tags", ""),
            body=body,
        ))
    return tuple(entries)


def _tokens(value: str) -> set[str]:
    return {
        token.lower() for token in _WORD_RE.findall(value)
        if len(token) > 1 and token.lower() not in _STOP_WORDS
    }


def retrieve(query: str, topic: str = "general", limit: int = 4, max_chars: int = 12000) -> str:
    topic_terms = {
        "profile": "profile contact availability biography",
        "projects": "project architecture result technology",
        "skills": "skills technology stack tools programming",
        "experience": "experience employment internship career employer",
        "research": "research publications glycomics machine learning",
        "education": "education degrees certifications",
        "contact": "contact email social availability links",
    }.get(topic, "profile projects skills experience research")
    query_tokens = _tokens(f"{query} {topic_terms}")
    ranked: list[tuple[int, KnowledgeEntry]] = []
    for entry in load_bundle():
        title_tokens = _tokens(f"{entry.title} {entry.tags} {entry.path}")
        body_tokens = _tokens(entry.body)
        score = 5 * len(query_tokens & title_tokens) + len(query_tokens & body_tokens)
        if topic == "projects" and entry.path.startswith("projects/"):
            score += 3
        ranked.append((score, entry))
    ranked.sort(key=lambda item: (-item[0], item[1].path))
    selected = [entry for score, entry in ranked if score > 0][:limit]
    if not selected:
        selected = [entry for _, entry in ranked[:2]]
    chunks: list[str] = []
    used = 0
    for entry in selected:
        chunk = f"SOURCE: {entry.path}\n{entry.body}"
        if used + len(chunk) > max_chars:
            chunk = chunk[:max(0, max_chars - used)]
        if chunk:
            chunks.append(chunk)
            used += len(chunk)
        if used >= max_chars:
            break
    return "\n\n---\n\n".join(chunks)
