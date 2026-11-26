"""Output guardrail: block contact details and links the sources never mentioned.

A language model can produce plausible-looking URLs, emails, or phone numbers.
On a public portfolio those are the most harmful hallucinations, because a
visitor may act on them. This check keeps only identifiers that appear in the
retrieved context or in the owner's published contact details.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.content import load_portfolio

# The bare-domain branch must not start inside an email address ("@gmail.com").
URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s<>()\"']+"
    r"|(?<![@\w.-])[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|io|ai|dev|app|org|net|edu)\b(?:/[^\s<>()\"']*)?",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE_RE = re.compile(r"(?<![\w.])\+?\d[\d\s-]{8,}\d\b")
REPLACEMENT = "the contact page"


@dataclass(frozen=True)
class GuardResult:
    text: str
    removed: tuple[str, ...]


def _key(value: str) -> str:
    """Normalise identifiers so formatting differences do not matter."""
    value = value.casefold().rstrip(".,;:!?)")
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    return re.sub(r"[\s-]", "", value).rstrip("/")


@lru_cache(maxsize=1)
def _published() -> frozenset[str]:
    personal = load_portfolio().get("personal", {})
    values = [str(value) for value in personal.values() if isinstance(value, str)]
    keys = {_key(value) for value in values if value}
    # Public site routes are always safe to mention.
    keys.add(_key("vigneshwarancj-portfolio-website.vercel.app"))
    return frozenset(keys)


def _allowed(identifier: str, context_keys: str) -> bool:
    key = _key(identifier)
    if not key:
        return True
    if key in context_keys:
        return True
    return any(key == known or key.startswith(known + "/") or known.startswith(key) and len(key) > 8 for known in _published())


def guard_identifiers(text: str, context: str) -> GuardResult:
    """Replace URLs, emails, and phone numbers that are not grounded."""
    context_keys = _key(context)
    removed: list[str] = []

    def check(match: re.Match[str]) -> str:
        value = match.group(0)
        # Trailing sentence punctuation belongs to the prose, not the identifier.
        trailing = ""
        while value and value[-1] in ".,;:!?)":
            trailing = value[-1] + trailing
            value = value[:-1]
        if _allowed(value, context_keys):
            return match.group(0)
        removed.append(value)
        return REPLACEMENT + trailing

    guarded = EMAIL_RE.sub(check, text)
    guarded = URL_RE.sub(check, guarded)
    guarded = PHONE_RE.sub(check, guarded)
    return GuardResult(guarded, tuple(removed))
