import asyncio
import json

from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY

LANGUAGE_NAMES = {
    "ta": "Tamil",
    "fr": "French",
    "zh-CN": "Mandarin Chinese (Simplified)",
    "hi": "Hindi",
    "es": "Spanish",
    "ar": "Arabic",
}

_cache: dict[tuple[str, str], str] = {}
_llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="openai/gpt-oss-120b",
    temperature=0,
    max_tokens=7_000,
)


def normalize_translations(raw: str, expected: int) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    payload = json.loads(text)
    translations = payload.get("translations") if isinstance(payload, dict) else None
    if not isinstance(translations, list) or len(translations) != expected:
        raise ValueError("translation response count does not match request")
    if any(not isinstance(item, str) or not item.strip() for item in translations):
        raise ValueError("translation response contains invalid text")
    return translations


async def translate_texts(language: str, texts: list[str]) -> list[str]:
    result: list[str | None] = [None] * len(texts)
    missing: list[str] = []
    missing_positions: dict[str, list[int]] = {}

    for index, text in enumerate(texts):
        cached = _cache.get((language, text))
        if cached:
            result[index] = cached
        else:
            if text not in missing_positions:
                missing.append(text)
                missing_positions[text] = []
            missing_positions[text].append(index)

    if missing:
        target = LANGUAGE_NAMES[language]
        prompt = (
            f"Translate each JSON array item from English into {target}. "
            "Preserve names, URLs, code, technology names, numbers, symbols, and placeholders. "
            "Use natural professional portfolio language. Return valid JSON only with this exact shape: "
            '{"translations":["..."]}. Keep identical item count and order.\n\n'
            f"INPUT={json.dumps(missing, ensure_ascii=False)}"
        )
        raw = await asyncio.wait_for(_llm.ainvoke(prompt), timeout=35)
        translated = normalize_translations(str(raw.content), len(missing))
        for source, value in zip(missing, translated, strict=True):
            if len(_cache) >= 4_000:
                _cache.pop(next(iter(_cache)))
            _cache[(language, source)] = value
            for position in missing_positions[source]:
                result[position] = value

    return [value or texts[index] for index, value in enumerate(result)]
