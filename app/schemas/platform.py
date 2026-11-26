from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class EventPayload(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9_]{2,64}$")
    path: str = Field(default="/", max_length=200)
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def limit_properties(cls, value):
        if len(value) > 12:
            raise ValueError("too many properties")
        blocked = {"email", "phone", "message", "name", "content"}
        if blocked.intersection(key.lower() for key in value):
            raise ValueError("personal or message data is not accepted")
        return value


class ContactPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(min_length=10, max_length=2000)
    website: str = Field(default="", max_length=200)


class NewsletterPayload(BaseModel):
    email: EmailStr


class ContentPayload(BaseModel):
    content: dict[str, Any]
    note: str = Field(default="Portfolio content update", max_length=200)


class MatchPayload(BaseModel):
    job_description: str = Field(min_length=80, max_length=8000)
    use_ai: bool = True

    @field_validator("job_description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 80:
            raise ValueError("paste the full job description (at least 80 characters)")
        return value


class MatchSharePayload(BaseModel):
    """A job-match *result* to share. The job description itself is never accepted."""
    summary: str | None = Field(default=None, max_length=800)
    requirements: list[dict[str, str]] = Field(default_factory=list, max_length=12)
    keywords: dict[str, Any]
    sources: list[dict[str, str]] = Field(default_factory=list, max_length=10)
    generated_by: str = Field(pattern=r"^(groq|keywords)$")
    title: str = Field(default="", max_length=120)

    @field_validator("requirements")
    @classmethod
    def bounded_requirements(cls, value):
        allowed = {"requirement", "status", "evidence"}
        for item in value:
            if set(item) - allowed or len(" ".join(item.values())) > 600:
                raise ValueError("unexpected requirement shape")
        return value


class TestimonialPayload(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    role: str = Field(min_length=2, max_length=120)
    relationship: str = Field(min_length=2, max_length=120)
    quote: str = Field(min_length=30, max_length=800)
    consent: bool
    website: str = Field(default="", max_length=200)  # honeypot

    @field_validator("consent")
    @classmethod
    def must_consent(cls, value):
        if not value:
            raise ValueError("permission to publish is required")
        return value


class TestimonialReview(BaseModel):
    status: str = Field(pattern=r"^(approved|rejected|pending)$")


class ClientErrorPayload(BaseModel):
    message: str = Field(min_length=1, max_length=300)
    source: str = Field(default="", max_length=200)
    line: int | None = Field(default=None, ge=0, le=10_000_000)
    kind: str = Field(default="error", pattern=r"^(error|unhandledrejection|boundary)$")
    path: str = Field(default="/", max_length=200)

    @field_validator("source", "path")
    @classmethod
    def strip_query(cls, value):
        # Query strings can carry drafts or identifiers; keep only the path.
        return value.split("?", 1)[0].split("#", 1)[0]


class NewsletterSendPayload(BaseModel):
    subject: str = Field(min_length=3, max_length=150)
    text: str = Field(min_length=20, max_length=20000)
    dry_run: bool = True


class DemoPayload(BaseModel):
    input: str = Field(min_length=1, max_length=160)
