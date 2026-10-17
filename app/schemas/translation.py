from typing import Literal

from pydantic import BaseModel, Field, field_validator

SupportedLanguage = Literal["ta", "fr", "zh-CN", "hi", "es", "ar"]


class TranslationRequest(BaseModel):
    language: SupportedLanguage
    texts: list[str] = Field(min_length=1, max_length=80)

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, texts: list[str]):
        if sum(len(text) for text in texts) > 14_000:
            raise ValueError("translation request is too large")
        if any(not text.strip() or len(text) > 1_000 for text in texts):
            raise ValueError("each translation text must contain 1 to 1000 characters")
        return texts


class TranslationResponse(BaseModel):
    translations: list[str]
