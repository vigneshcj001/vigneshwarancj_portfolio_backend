import re
from dataclasses import dataclass
from functools import lru_cache

from app.content import load_documents, searchable_text

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


@dataclass(frozen=True)
class KnowledgeResult:
    context: str
    sources: tuple[dict[str, str], ...]


@lru_cache(maxsize=1)
def load_bundle() -> tuple[KnowledgeEntry, ...]:
    return tuple(
        KnowledgeEntry(
            path=document.path,
            title=document.title,
            kind=document.kind,
            tags=document.kind.replace("_", " "),
            body=searchable_text(document),
        )
        for document in load_documents()
    )


def _tokens(value: str) -> set[str]:
    return {
        token.lower() for token in _WORD_RE.findall(value)
        if len(token) > 1 and token.lower() not in _STOP_WORDS
    }


def retrieve_with_sources(query: str, topic: str = "general", limit: int = 4, max_chars: int = 12000) -> KnowledgeResult:
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
        if topic == "projects" and entry.kind == "project":
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
    sources = tuple(
        {
            "title": entry.title,
            "kind": entry.kind.replace("_", " ").title(),
            "path": entry.path,
            "url": source_url(entry),
        }
        for entry in selected[:len(chunks)]
    )
    return KnowledgeResult("\n\n---\n\n".join(chunks), sources)


def source_url(entry: KnowledgeEntry) -> str:
    if entry.path.startswith("projects/"):
        slug = entry.path.removeprefix("projects/").removesuffix(".md")
        if slug.startswith("glycanbench-"):
            return "/projects/glycanbench"
        if slug in {"pocketpet", "syncly"}:
            return f"/projects/{slug}"
        return "/projects"
    if "aiora" in f"{entry.title} {entry.body}".casefold():
        return "/projects/aiora"
    if entry.kind == "publication":
        return "/publications"
    if entry.kind == "experience":
        return "/experience"
    if entry.kind == "skills":
        return "/skills"
    if entry.kind in {"education", "certification", "profile"}:
        return "/about"
    return "/"


def retrieve(query: str, topic: str = "general", limit: int = 4, max_chars: int = 12000) -> str:
    return retrieve_with_sources(query, topic, limit, max_chars).context
