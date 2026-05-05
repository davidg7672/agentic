import pytest
from unittest.mock import patch
from nodes.interview_predictor import interview_predictor_node

LLM_RESPONSE = """### Technical / Skills Questions (3 questions)
1. Describe your experience with FastAPI vs Flask.
*Why this will be asked: Role requires FastAPI; candidate has Flask experience.*

2. How do you optimize PostgreSQL queries at scale?
*Why this will be asked: Core skill in JD.*

3. Walk me through containerizing a service with Docker.
*Why this will be asked: Demonstrated Docker experience in resume.*

### Behavioral Questions (3 questions)
4. Tell me about a time when you improved API performance.
*Why this will be asked: Candidate mentions 50k daily requests.*

5. Describe a situation where you had to debug a production issue.
*Why this will be asked: Reliability is key for senior roles.*

6. Tell me about a project where you worked under tight deadlines.
*Why this will be asked: Startup background suggests fast-paced delivery.*

### Gap-Probing Questions (2 questions)
7. Have you used Redis in a production environment?
*Why this will be asked: Redis is required but absent from resume.*

8. Describe your Kubernetes experience.
*Why this will be asked: Kubernetes listed as required, not on resume.*

### Situational / Role-Specific Questions (2 questions)
9. If our API latency doubled overnight, how would you investigate?
*Why this will be asked: Senior engineers own incident response.*

10. How would you approach migrating a monolith to microservices?
*Why this will be asked: Likely direction for this role.*
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_interview_predictor_returns_questions(base_state):
    with patch("nodes.interview_predictor.call_claude", return_value=LLM_RESPONSE):
        result = interview_predictor_node(base_state)

    assert result["interview_questions"] == LLM_RESPONSE
    assert result["current_step"] == "complete"


def test_interview_predictor_calls_claude_with_all_inputs(base_state):
    with patch("nodes.interview_predictor.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        interview_predictor_node(base_state)

    user_msg = mock_llm.call_args[0][1]
    assert base_state["job_description"] in user_msg
    assert base_state["rewritten_resume"] in user_msg
    assert base_state["gap_analysis"] in user_msg


def test_interview_predictor_uses_correct_max_tokens(base_state):
    with patch("nodes.interview_predictor.call_claude", return_value=LLM_RESPONSE) as mock_llm:
        interview_predictor_node(base_state)

    assert mock_llm.call_args[1]["max_tokens"] == 1400


# ---------------------------------------------------------------------------
# Skip on error state
# ---------------------------------------------------------------------------

def test_interview_predictor_skips_when_error_set(error_state):
    with patch("nodes.interview_predictor.call_claude") as mock_llm:
        result = interview_predictor_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_interview_predictor_returns_error_on_exception(base_state):
    with patch("nodes.interview_predictor.call_claude", side_effect=Exception("timeout")):
        result = interview_predictor_node(base_state)

    assert result["error"] == "Interview question generation failed. Please try again."
    assert "interview_questions" not in result
