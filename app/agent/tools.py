import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import yaml
from pydantic import BaseModel, Field

from app.ai.okf import retrieve_with_sources
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


def project_slug(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    for alias, slug in PROJECT_ALIASES.items():
        if alias in normalized:
            return slug
    return None


def _dump(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120).strip()


def search_portfolio(payload: SearchPortfolioInput) -> ToolOutcome:
    result = retrieve_with_sources(payload.query, payload.topic, payload.limit)
    return ToolOutcome(result.context, result.sources, summary=f"Found {len(result.sources)} verified sources")


def get_project_details(payload: GetProjectDetailsInput) -> ToolOutcome:
    slug = project_slug(payload.project)
    result = retrieve_with_sources(f"{payload.project} architecture role result limitations", "projects", 3)
    action: tuple[UiAction, ...] = ()
    if slug:
        action = (UiAction(type="highlight", target=PROJECT_TARGETS[slug], label=f"Highlight {payload.project}"),)
    return ToolOutcome(result.context, result.sources, action, f"Loaded verified details for {payload.project}")


def get_skills(payload: GetSkillsInput) -> ToolOutcome:
    skills = load_portfolio()["skills"]
    if payload.category:
        match = next((value for key, value in skills.items() if payload.category.casefold() in key.casefold()), None)
        content = {payload.category: match} if match else skills
    else:
        content = skills
    return ToolOutcome(f"VERIFIED SKILLS\n{_dump(content)}", ({"title": "Technical skills", "kind": "Skills", "url": "/skills"},), summary="Loaded verified skills")


def get_experience(payload: GetExperienceInput) -> ToolOutcome:
    result = retrieve_with_sources(payload.query or "work experience roles responsibilities", "experience", 4)
    return ToolOutcome(result.context, result.sources, summary="Loaded verified experience")


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
    action = UiAction(type="navigate", target=payload.target, label="Open relevant portfolio section", auto_execute=True)
    return ToolOutcome(actions=(action,), summary=f"Prepared navigation to {payload.target}")


def highlight_element(payload: HighlightElementInput) -> ToolOutcome:
    action = UiAction(type="highlight", target=payload.target, label="Highlight relevant section", auto_execute=True)
    return ToolOutcome(actions=(action,), summary=f"Prepared highlight for {payload.target}")


def start_project_walkthrough(payload: StartProjectWalkthroughInput) -> ToolOutcome:
    slug = project_slug(payload.project)
    if not slug:
        return ToolOutcome(summary="Walkthrough unavailable for this project")
    action = UiAction(
        type="walkthrough", target=PROJECT_TARGETS[slug], label=f"Start {payload.project} walkthrough",
        data={"project": slug, "steps": ["Overview", "Problem and role", "Architecture", "Decisions and result"]},
    )
    return ToolOutcome(actions=(action,), summary=f"Prepared {payload.project} walkthrough")


def prepare_contact_action(payload: PrepareContactActionInput) -> ToolOutcome:
    action = UiAction(
        type="contact", target="contact.form", label="Prepare contact message",
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
