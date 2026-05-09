import re
import unicodedata

# Common prompt injection patterns — case-insensitive
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+(instructions?|prompts?|context|rules?)",
    r"forget\s+(everything|all|previous|your\s+instructions?)",
    r"you\s+are\s+now\s+a\b",
    r"(override|bypass|disregard)\s+(the\s+)?(system|instructions?|rules?|constraints?)",
    r"(reveal|show|print|output|repeat)\s+(the\s+)?(system\s+prompt|instructions?|prompt)",
    r"act\s+as\s+(if\s+you\s+are|a\s+different)",
    r"from\s+now\s+on\s+(you\s+are|ignore|forget|disregard)",
    r"new\s+instructions?\s*:",
    r"<\s*(system|instructions?)\s*>",
    r"\[\s*system\s*\]",
    r"#\s*system\s*prompt",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(question: str) -> str:
    """Clean and validate user input. Raises ValueError on suspected injection."""
    question = _CONTROL_CHARS.sub("", question)
    question = unicodedata.normalize("NFC", question).strip()
    question = re.sub(r" {3,}", "  ", question)

    for pattern in _COMPILED:
        if pattern.search(question):
            raise ValueError("Input contains disallowed content.")

    return question
