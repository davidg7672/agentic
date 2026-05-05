import pytest
from unittest.mock import patch
from nodes.resume_rewriter import resume_rewriter_node

LLM_RESPONSE = "Jane Doe\n\nSoftware Engineer with Python, FastAPI, PostgreSQL, Docker skills."


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_resume_rewriter_returns_rewritten_resume(base_state):
    with patch("nodes.resume_rewriter.call_claude", return_value=LLM_RESPONSE):
        result = resume_rewriter_node(base_state)

    assert result["rewritten_resume"] == LLM_RESPONSE
    assert result["current_step"] == "resume_rewritten"


def test_resume_rewriter_calls_claude_with_all_inputs(base_state):
    with patch("nodes.resume_rewriter.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        resume_rewriter_node(base_state)

    user_msg = mock_llm.call_args[0][1]
    assert base_state["job_description"] in user_msg
    assert base_state["gap_analysis"] in user_msg
    assert base_state["original_resume"] in user_msg


def test_resume_rewriter_uses_correct_max_tokens(base_state):
    with patch("nodes.resume_rewriter.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        resume_rewriter_node(base_state)

    assert mock_llm.call_args[1]["max_tokens"] == 2000


# ---------------------------------------------------------------------------
# Skip on error state
# ---------------------------------------------------------------------------

def test_resume_rewriter_skips_when_error_set(error_state):
    with patch("nodes.resume_rewriter.call_claude") as mock_llm:
        result = resume_rewriter_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_resume_rewriter_returns_error_on_exception(base_state):
    with patch("nodes.resume_rewriter.call_claude", side_effect=RuntimeError("timeout")):
        result = resume_rewriter_node(base_state)

    assert result["error"] == "Resume rewrite failed. Please try again."
    assert "rewritten_resume" not in result
