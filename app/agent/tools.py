import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import yaml
from pydantic import BaseModel, Field

from app.ai.okf import retrieve_with_sources
from app.ai.presentation import PROJECT_NAMES, reading_status
from app.content import load_portfolio
from app.agent.protocol import UiAction


class SearchPortfolioInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    topic: Literal["general", "profile", "projects", "skills", "experience", "research", "education", "contact"] = "general"
    limit: int = Field(default=4, ge=1, le=4)


class GetProjectDetailsInput(BaseModel):
    project: str = Field(min_length=1, max_length=100)


class GetSkillsInput(BaseModel):
    category: str | None = Field(default=None, max_length=100)


class GetExperienceInput(BaseModel):
    query: str | None = Field(default=None, max_length=200)


class GetResumeInput(BaseModel):
    section: Literal["summary", "skills", "experience", "education", "all"] = "summary"


class NavigateToSectionInput(BaseModel):
    target: str = Field(min_length=1, max_length=80)


class HighlightElementInput(BaseModel):
    target: str = Field(min_length=1, max_length=80)


class StartProjectWalkthroughInput(BaseModel):
    project: str = Field(min_length=1, max_length=100)


class PrepareContactActionInput(BaseModel):
    topic: str = Field(min_length=1, max_length=240)


@dataclass(frozen=True)
class ToolOutcome:
    context: str = ""
    sources: tuple[dict[str, str], ...] = ()
    actions: tuple[UiAction, ...] = ()
    summary: str = ""


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


PROJECT_ALIASES = {
    "aiora": "aiora",
    "pocketpet": "pocketpet",
    "pocket pet": "pocketpet",
    "glycanbench": "glycanbench",
    "glycan bench": "glycanbench",
    "syncly": "syncly",
}
PROJECT_TARGETS = {slug: f"projects.{slug}" for slug in ("aiora", "pocketpet", "glycanbench", "syncly")}
_FOLLOWUP_RE = re.compile(
    r"\b(it|its|this|that|these|those|architecture|technologies|safety|controls|limitations|contribution|walkthrough|deployment|features|stack|validation)\b",
    re.I,
)
TARGET_LABELS = {
    **{target: f"{PROJECT_NAMES[slug]} case study" for slug, target in PROJECT_TARGETS.items()},
    "home.hero": "CJ's introduction", "home.projects": "selected projects",
    "about.profile": "CJ's profile and education", "experience.timeline": "career timeline",
    "projects.list": "project catalog", "skills.grid": "technical skills",
    "publications.list": "research publications", "resume.document": "CJ's résumé",
    "contact.form": "contact form",
}


def project_slug(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    for alias, slug in PROJECT_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            return slug
    return None


def resolve_project(message: str, history=()) -> str | None:
    explicit = project_slug(message)
    if explicit:
        return explicit
    # Only inherit a project for an actual follow-up, not a fresh biography/contact question.
    if not _FOLLOWUP_RE.search(message):
        return None
    for item in reversed(history):
        if item.get("role") != "user":
            continue
        named = project_slug(item.get("content", ""))
        if named:
            return named
        # A new subject ends the previous project context.
        if not _FOLLOWUP_RE.search(item.get("content", "")):
            return None
    return None


def tool_progress(invocation: ToolInvocation) -> str:
    args = invocation.arguments
    name = invocation.name
    if name == "search_portfolio":
        return reading_status(args.get("query", ""), project_slug(args.get("query", "")))
    if name == "get_project_details":
        return f"Reading {PROJECT_NAMES.get(args.get('project'), 'project')} implementation, contribution, and limitations"
    if name == "get_skills":
        return "Reading CJ's documented programming, AI, and full-stack skills"
    if name == "get_experience":
        return "Reading CJ's Ceiyone roles and research internship"
    if name == "get_resume":
        return f"Reading CJ's résumé: {args.get('section', 'summary')}"
    if name in {"navigate_to_section", "highlight_element"}:
        verb = "Preparing to open" if name == "navigate_to_section" else "Locating"
        return f"{verb} {TARGET_LABELS.get(args.get('target'), 'portfolio section')}"
    if name == "start_project_walkthrough":
        return f"Preparing {PROJECT_NAMES.get(args.get('project'), 'project')} walkthrough steps"
    return "Preparing a contact draft for your review; nothing will be sent"


def _dump(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120).strip()


def search_portfolio(payload: SearchPortfolioInput) -> ToolOutcome:
    result = retrieve_with_sources(payload.query, payload.topic, payload.limit)
    titles = ", ".join(dict.fromkeys(source["title"] for source in result.sources))
    return ToolOutcome(result.context, result.sources, summary=f"Read {len(result.sources)} sources: {titles}"[:160])


def get_project_details(payload: GetProjectDetailsInput) -> ToolOutcome:
    slug = project_slug(payload.project)
    result = retrieve_with_sources(f"{payload.project} architecture role result limitations", "projects", 3)
    action: tuple[UiAction, ...] = ()
    if slug:
        action = (UiAction(type="highlight", target=PROJECT_TARGETS[slug], label=f"Highlight {PROJECT_NAMES[slug]} case study"),)
    return ToolOutcome(result.context, result.sources, action, f"Read {PROJECT_NAMES.get(slug, payload.project)} implementation, contribution, and limitations")


def get_skills(payload: GetSkillsInput) -> ToolOutcome:
    skills = load_portfolio()["skills"]
    if payload.category:
        match = next((value for key, value in skills.items() if payload.category.casefold() in key.casefold()), None)
        content = {payload.category: match} if match else skills
    else:
        content = skills
    return ToolOutcome(f"VERIFIED SKILLS\n{_dump(content)}", ({"title": "Technical skills", "kind": "Skills", "url": "/skills"},), summary=f"Read {len(content)} documented skill categories")


def get_experience(payload: GetExperienceInput) -> ToolOutcome:
    result = retrieve_with_sources(payload.query or "work experience roles responsibilities", "experience", 4)
    titles = ", ".join(dict.fromkeys(source["title"] for source in result.sources))
    return ToolOutcome(result.context, result.sources, summary=f"Read career sources: {titles}"[:160])


def get_resume(payload: GetResumeInput) -> ToolOutcome:
    portfolio = load_portfolio()
    sections = {
        "summary": {"personal": portfolio["personal"], "stats": portfolio["stats"]},
        "skills": portfolio["skills"],
        "experience": portfolio["work_experience"],
        "education": portfolio["education"],
        "all": {key: portfolio[key] for key in ("personal", "skills", "work_experience", "education")},
    }
    return ToolOutcome(f"VERIFIED RESUME DATA\n{_dump(sections[payload.section])}", ({"title": "Resume", "kind": "Resume", "url": "/resume"},), summary=f"Loaded resume {payload.section}")


def navigate_to_section(payload: NavigateToSectionInput) -> ToolOutcome:
    label = TARGET_LABELS.get(payload.target, "portfolio section")
    action = UiAction(type="navigate", target=payload.target, label=f"Open {label}", auto_execute=True)
    return ToolOutcome(actions=(action,), summary=f"Prepared link to {label}; opening happens in your browser")


def highlight_element(payload: HighlightElementInput) -> ToolOutcome:
    label = TARGET_LABELS.get(payload.target, "portfolio section")
    action = UiAction(type="highlight", target=payload.target, label=f"Highlight {label}", auto_execute=True)
    return ToolOutcome(actions=(action,), summary=f"Located {label} for highlighting in your browser")


def start_project_walkthrough(payload: StartProjectWalkthroughInput) -> ToolOutcome:
    slug = project_slug(payload.project)
    if not slug:
        return ToolOutcome(summary="Walkthrough unavailable for this project")
    action = UiAction(
        type="walkthrough", target=PROJECT_TARGETS[slug], label=f"Explore {PROJECT_NAMES[slug]} in 4 steps",
        data={"project": slug, "steps": [f"{PROJECT_NAMES[slug]} overview", "Problem and CJ's contribution", "Components and data flow", "Design decisions and delivered result"]},
    )
    return ToolOutcome(actions=(action,), summary=f"Prepared 4 {PROJECT_NAMES[slug]} walkthrough steps; select Explore to start")


def prepare_contact_action(payload: PrepareContactActionInput) -> ToolOutcome:
    action = UiAction(
        type="contact", target="contact.form", label="Review a contact draft with CJ",
        requires_confirmation=True, data={"topic": payload.topic},
    )
    return ToolOutcome(actions=(action,), summary="Prepared contact handoff; visitor must confirm before sending")


TOOL_REGISTRY: dict[str, tuple[type[BaseModel], Callable[[Any], ToolOutcome]]] = {
    "search_portfolio": (SearchPortfolioInput, search_portfolio),
    "get_project_details": (GetProjectDetailsInput, get_project_details),
    "get_skills": (GetSkillsInput, get_skills),
    "get_experience": (GetExperienceInput, get_experience),
    "get_resume": (GetResumeInput, get_resume),
    "navigate_to_section": (NavigateToSectionInput, navigate_to_section),
    "highlight_element": (HighlightElementInput, highlight_element),
    "start_project_walkthrough": (StartProjectWalkthroughInput, start_project_walkthrough),
    "prepare_contact_action": (PrepareContactActionInput, prepare_contact_action),
}


def execute_tool(invocation: ToolInvocation) -> ToolOutcome:
    model, handler = TOOL_REGISTRY[invocation.name]
    return handler(model.model_validate(invocation.arguments))
