"""ATS-oriented résumé content model, rendered to PDF, DOCX, and plain text.

Layout rules follow common applicant-tracking-system guidance:
single column; standard section headings; contact details in the body (not in
page headers/footers); no tables, text boxes, icons, or images; plain bullets;
consistent "Mon YYYY – Mon YYYY" dates; skills listed early as plain keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.content import load_portfolio

LOCATION = "Coimbatore, Tamil Nadu, India"
HEADLINE = "AI Engineer | Full-Stack Developer | Python, TypeScript, React, Node.js, FastAPI"

SUMMARY = (
    "AI engineer and full-stack developer building production AI applications, conversational "
    "commerce platforms, and cloud-deployed web services. Ships Python, Node.js, and TypeScript "
    "APIs with React front ends, PostgreSQL and Redis data layers, and Docker-based deployments. "
    "Experienced with LLM integration, multi-agent workflows, OCR and document AI, payment and "
    "logistics integrations, and usage metering. M.Tech in Big Data Biology with published "
    "machine-learning research in computational biology."
)

# Research projects already appear under Publications, so they are not repeated.
FEATURED_PROJECTS = [
    "PocketPet",
    "Syncly",
    "GlycanBench: a unified resource for working with glycans",
]

MAX_ROLE_BULLETS = {0: 5}  # current role gets more room
DEFAULT_ROLE_BULLETS = 3
BULLET_CHARS = 210

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_MARKERS = (" — ", " – ", "; ", ", then ", ", and ", ": ", ", ")


@dataclass
class Block:
    kind: str  # name|headline|contact|heading|title|meta|text|bullet|labeled
    text: str
    label: str = ""


@dataclass
class ResumeDocument:
    name: str
    keywords: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)

    def add(self, kind: str, text: str, label: str = "") -> None:
        text = " ".join(str(text).split())
        if text:
            self.blocks.append(Block(kind, text, label))


def clip(text: str, limit: int = BULLET_CHARS) -> str:
    """Shorten to whole sentences where possible, never mid-word."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    kept = ""
    sentences = _SENTENCE_END.split(text)
    for index, sentence in enumerate(sentences):
        candidate = f"{kept} {sentence}".strip()
        if len(candidate) > limit:
            # A short opener ("Platform built solo end to end.") carries few
            # keywords; borrow the next sentence's leading clauses for detail.
            if kept and len(kept) < limit * 0.55:
                remainder = clip(" ".join(sentences[index:]), limit - len(kept) - 1)
                return f"{kept} {remainder}"
            break
        kept = candidate
    if kept:
        return kept
    # No whole sentence fits: end at the last clause boundary so the bullet still
    # reads as a complete statement rather than trailing off with an ellipsis.
    window = text[:limit]
    cut = max(window.rfind(marker) for marker in _CLAUSE_MARKERS)
    if cut < limit // 2:
        cut = window.rfind(" ")
    return window[:cut].rstrip(" ,;:—–-") + "."


def _link(url: str) -> str:
    return url.removeprefix("https://").removeprefix("http://").rstrip("/")


def build_resume() -> ResumeDocument:
    data = load_portfolio()
    personal = data["personal"]
    doc = ResumeDocument(name=personal["name"])

    doc.add("name", personal["name"])
    doc.add("headline", HEADLINE)
    contact = [
        LOCATION,
        personal.get("phone", ""),
        personal.get("email", ""),
        _link(personal.get("linkedin", "")),
        _link(personal.get("github", "")),
        _link(personal.get("leetcode", "")),
        _link(personal.get("portfolio", "")),
    ]
    doc.add("contact", " | ".join(part for part in contact if part))

    doc.add("heading", "Professional Summary")
    doc.add("text", SUMMARY)

    skills = data.get("skills", {})
    doc.add("heading", "Technical Skills")
    for category, items in skills.items():
        doc.add("labeled", ", ".join(items), label=category)
        doc.keywords.extend(items[:4])

    doc.add("heading", "Work Experience")
    for index, role in enumerate(data.get("work_experience", [])):
        doc.add("title", role["role"])
        doc.add("meta", " | ".join(part for part in (
            role.get("company", ""), role.get("location", ""), role.get("period", ""),
        ) if part))
        limit = MAX_ROLE_BULLETS.get(index, DEFAULT_ROLE_BULLETS)
        bullets: list[str] = []
        projects = role.get("projects", [])
        if not projects and role.get("overview"):
            bullets.append(clip(role["overview"]))
        for project in projects:
            tech = ", ".join(project.get("tech", [])[:5])
            line = f"{project['name']}: {clip(project.get('description', ''), BULLET_CHARS - len(tech) - 10)}"
            bullets.append(f"{line} ({tech})" if tech else line)
        bullets.extend(clip(item) for item in role.get("additional_responsibilities", []))
        for bullet in bullets[:limit]:
            doc.add("bullet", bullet)

    doc.add("heading", "Projects")
    projects = data.get("projects", {})
    for name in FEATURED_PROJECTS:
        project = projects.get(name)
        if not project:
            continue
        doc.add("title", f"{name} | {project['subtitle']}" if project.get("subtitle") else name)
        doc.add("bullet", clip(project.get("description", ""), 280))
        if project.get("tech_stack"):
            doc.add("labeled", ", ".join(project["tech_stack"][:10]), label="Tech")
        links = [project.get(key) for key in ("live_link", "github", "github_frontend", "pypi", "doi")]
        links = [_link(link) for link in links if link]
        if links:
            doc.add("labeled", " | ".join(links[:3]), label="Links")

    doc.add("heading", "Education")
    for education in data.get("education", []):
        doc.add("title", education["degree"])
        doc.add("meta", " | ".join(part for part in (
            education.get("institution", ""), education.get("location", ""), education.get("period", ""),
            f"Grade: {education['grade']}" if education.get("grade") else "",
        ) if part))
        if education.get("focus"):
            doc.add("bullet", f"Focus: {education['focus']}")

    publications = data.get("publications", [])
    if publications:
        doc.add("heading", "Publications")
        for publication in publications:
            doc.add("bullet", " | ".join(part for part in (
                publication["title"], publication.get("status", ""),
                publication.get("institution", ""), str(publication.get("year", "")),
            ) if part))

    certifications = data.get("certifications", [])
    if certifications:
        doc.add("heading", "Certifications")
        for certification in certifications:
            doc.add("bullet", " | ".join(part for part in (
                certification["title"], certification.get("issuer", ""),
            ) if part))

    doc.keywords = list(dict.fromkeys(doc.keywords))[:30]
    return doc


def render_text(doc: ResumeDocument) -> str:
    lines: list[str] = []
    for block in doc.blocks:
        if block.kind == "heading":
            lines += ["", block.text.upper(), "-" * len(block.text)]
        elif block.kind == "title":
            lines += ["", block.text]
        elif block.kind == "bullet":
            lines.append(f"- {block.text}")
        elif block.kind == "labeled":
            lines.append(f"{block.label}: {block.text}")
        else:
            lines.append(block.text)
    return "\n".join(lines).strip() + "\n"
