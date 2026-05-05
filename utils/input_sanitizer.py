import sys

MAX_INPUT_CHARS = 50_000

_INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "disregard all previous",
    "forget previous instructions",
    "new instructions:",
    "<|im_start|>",
    "<|im_end|>",
    "[system]",
    "you are now",
    "act as if",
]


def sanitize_input(text: str) -> str:
    text = text.strip()

    if not text:
        raise ValueError("Input cannot be empty.")

    lower = text.lower()
    for phrase in _INJECTION_PHRASES:
        if phrase in lower:
            print(f"[input_sanitizer] rejected input containing phrase: {phrase!r}", file=sys.stderr)
            raise ValueError(
                "Input contains content that cannot be processed. "
                "Please remove any instructional directives and try again."
            )

    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"Input is too long ({len(text):,} characters). "
            f"Please trim it to under {MAX_INPUT_CHARS:,} characters."
        )

    return text
