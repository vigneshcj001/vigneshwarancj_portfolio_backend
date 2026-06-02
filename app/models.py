from pydantic import BaseModel, Field, field_validator

from app.config import MAX_MESSAGE_LENGTH


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return v.strip()


class AssistantResponse(BaseModel):
    reply: str
