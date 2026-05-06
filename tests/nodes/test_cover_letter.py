import pytest
from unittest.mock import patch
from nodes.cover_letter import cover_letter_node

LLM_RESPONSE = (
    "Acme Corp's mission to redefine cloud infrastructure aligns with my background "
    "in distributed systems.\n\n"
    "At StartupXYZ, I built REST APIs serving 50,000 daily requests and managed "
    "PostgreSQL databases at scale.\n\n"
    "I'd welcome the opportunity to discuss how my experience maps to your team's goals."
)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_cover_letter_returns_letter(base_state):
    with patch("nodes.cover_letter.call_claude", return_value=LLM_RESPONSE):
        result = cover_letter_node(base_state)

    assert result["cover_letter"] == LLM_RESPONSE
    assert result["current_step"] == "cover_letter_drafted"


def test_cover_letter_calls_claude_with_all_inputs(base_state):
    with patch("nodes.cover_letter.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        cover_letter_node(base_state)

    user_msg = mock_llm.call_args[0][1]
    assert base_state["job_description"] in user_msg
    assert base_state["rewritten_resume"] in user_msg
    assert base_state["gap_analysis"] in user_msg


def test_cover_letter_uses_correct_max_tokens(base_state):
    with patch("nodes.cover_letter.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        cover_letter_node(base_state)

    assert mock_llm.call_args[1]["max_tokens"] == 900


# ---------------------------------------------------------------------------
# Skip on error state
# ---------------------------------------------------------------------------

def test_cover_letter_skips_when_error_set(error_state):
    with patch("nodes.cover_letter.call_claude") as mock_llm:
        result = cover_letter_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_cover_letter_returns_error_on_exception(base_state):
    with patch("nodes.cover_letter.call_claude", side_effect=Exception("API error")):
        result = cover_letter_node(base_state)

    assert result["error"] == "Cover letter generation failed. Please try again."
    assert "cover_letter" not in result
