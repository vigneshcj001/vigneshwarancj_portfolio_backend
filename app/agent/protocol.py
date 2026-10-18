from typing import Any, Literal

from pydantic import BaseModel, Field


NavigationTarget = Literal[
    "home.hero", "home.projects", "about.profile", "experience.timeline",
    "projects.list", "projects.aiora", "projects.pocketpet",
    "projects.glycanbench", "projects.syncly", "skills.grid",
    "publications.list", "resume.document", "contact.form",
]


class UiAction(BaseModel):
    """Validated command consumed by frontend allowlist interpreter."""

    type: Literal["navigate", "highlight", "walkthrough", "contact"]
    target: NavigationTarget
    label: str = Field(min_length=1, max_length=100)
    auto_execute: bool = False
    requires_confirmation: bool = False
    data: dict[str, Any] = Field(default_factory=dict)


class ToolTrace(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    status: Literal["completed", "skipped", "failed"] = "completed"
    summary: str = Field(default="", max_length=160)
