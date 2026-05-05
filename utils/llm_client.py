import os
from anthropic import Anthropic

_client: Anthropic | None = None

MODEL = "claude-sonnet-4-6"


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Copy .env.example to .env and add your key."
            )
        _client = Anthropic(api_key=api_key, timeout=60.0)
    return _client


def call_claude(system: str, user: str, max_tokens: int = 1024) -> str:
    response = get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text
