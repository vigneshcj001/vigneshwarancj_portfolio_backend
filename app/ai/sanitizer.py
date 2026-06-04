import re

_FORBIDDEN = ["**", "*", "|", "#", "__", "~~", "`"]


def clean_output(text: str) -> str:
    for token in _FORBIDDEN:
        text = text.replace(token, "")
    # Remove leading dash/bullet used as list markers (keep mid-sentence hyphens)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
