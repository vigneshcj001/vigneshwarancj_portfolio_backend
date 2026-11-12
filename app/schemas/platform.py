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


class DemoPayload(BaseModel):
    input: str = Field(min_length=1, max_length=160)
