_FORBIDDEN = ["**", "*", "|", "#", "__", "~~"]


def clean_output(text: str) -> str:
    for token in _FORBIDDEN:
        text = text.replace(token, "")
    return text.strip()
