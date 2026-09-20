import re


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+(me\s+)?your\s+system\s+prompt",
    r"reveal\s+(your\s+)?instructions",
    r"act\s+as\s+if\s+you\s+are",
    r"bypass\s+(the\s+)?security",
]


def detect_prompt_injection(text: str):

    normalized = text.lower()

    matches = []

    for pattern in INJECTION_PATTERNS:

        if re.search(pattern, normalized):
            matches.append(pattern)

    return {
        "blocked": len(matches) > 0,
        "matches": matches
    }