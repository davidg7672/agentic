import pytest
from unittest.mock import patch
from nodes.gap_analyzer import gap_analyzer_node

LLM_RESPONSE = """### Missing Required Skills
- FastAPI
- Redis

### Experience Level Gaps
None identified.

### Missing Nice-to-Haves
- GraphQL

### Strengths Match
- Python expertise
- PostgreSQL
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_gap_analyzer_returns_analysis(base_state):
    with patch("nodes.gap_analyzer.call_claude", return_value=LLM_RESPONSE):
        result = gap_analyzer_node(base_state)

    assert result["gap_analysis"] == LLM_RESPONSE
    assert result["current_step"] == "gap_analysis_complete"


def test_gap_analyzer_calls_claude_with_both_inputs(base_state):
    with patch("nodes.gap_analyzer.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        gap_analyzer_node(base_state)

    call_args = mock_llm.call_args
    user_msg = call_args[0][1]
    assert base_state["job_description"] in user_msg
    assert base_state["original_resume"] in user_msg


def test_gap_analyzer_uses_correct_max_tokens(base_state):
    with patch("nodes.gap_analyzer.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        gap_analyzer_node(base_state)

    assert mock_llm.call_args[1]["max_tokens"] == 700


# ---------------------------------------------------------------------------
# Skip on error state
# ---------------------------------------------------------------------------

def test_gap_analyzer_skips_when_error_set(error_state):
    with patch("nodes.gap_analyzer.call_claude") as mock_llm:
        result = gap_analyzer_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_gap_analyzer_returns_error_on_exception(base_state):
    with patch("nodes.gap_analyzer.call_claude", side_effect=Exception("API down")):
        result = gap_analyzer_node(base_state)

    assert "error" in result
    assert result["error"] == "Gap analysis failed. Please try again."
    assert "gap_analysis" not in result
