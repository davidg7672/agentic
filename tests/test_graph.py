import pytest
from unittest.mock import patch, MagicMock
from graph import build_graph


@pytest.fixture
def compiled_graph():
    return build_graph()


def test_graph_compiles_without_error():
    graph = build_graph()
    assert graph is not None


def test_graph_has_all_nodes(compiled_graph):
    node_names = set(compiled_graph.nodes)
    expected = {
        "gap_analyzer",
        "resume_rewriter",
        "cover_letter_drafter",
        "interview_predictor",
        "fabrication_detector",
        "tone_enforcer",
        "ats_checker",
    }
    assert expected.issubset(node_names)


def test_graph_invoke_calls_nodes_in_order():
    """Integration smoke test: verify the graph runs end-to-end with mocked LLM calls."""
    with patch("nodes.gap_analyzer.call_claude", return_value="Gap analysis result"), \
         patch("nodes.resume_rewriter.call_claude", return_value="Rewritten resume"), \
         patch("guardrails.fabrication_detector.call_claude",
               return_value='{"verdict": "clean", "fabrications": []}'), \
         patch("guardrails.tone_enforcer.call_claude", return_value="VERDICT: PASS"), \
         patch("nodes.cover_letter.call_claude", return_value="Cover letter text"), \
         patch("nodes.interview_predictor.call_claude", return_value="Interview questions"):

        graph = build_graph()
        from state import initial_state
        state = initial_state("Software Engineer role", "My resume content")
        result = graph.invoke(state)

    assert result["gap_analysis"] == "Gap analysis result"
    assert result["rewritten_resume"] == "Rewritten resume"
    assert result["cover_letter"] == "Cover letter text"
    assert result["interview_questions"] == "Interview questions"
    assert result["current_step"] == "complete"


def test_graph_guardrails_run_after_rewrite():
    """Guardrail nodes execute and populate their result fields."""
    with patch("nodes.gap_analyzer.call_claude", return_value="gaps"), \
         patch("nodes.resume_rewriter.call_claude", return_value="rewritten"), \
         patch("guardrails.fabrication_detector.call_claude",
               return_value='{"verdict": "flagged", "fabrications": ["Added Kubernetes cert"]}'), \
         patch("guardrails.tone_enforcer.call_claude", return_value="VERDICT: PASS"), \
         patch("nodes.cover_letter.call_claude", return_value="cover letter"), \
         patch("nodes.interview_predictor.call_claude", return_value="questions"):

        graph = build_graph()
        from state import initial_state
        result = graph.invoke(initial_state("JD", "Resume"))

    assert result["fabrication_result"] is not None
    assert result["fabrication_result"]["passed"] is False
    assert any("Kubernetes cert" in w for w in result["guardrail_warnings"])


def test_graph_error_propagates_and_skips_remaining_nodes():
    """If gap_analyzer sets an error, downstream nodes are all skipped."""
    with patch("nodes.gap_analyzer.call_claude", side_effect=Exception("API failure")):
        graph = build_graph()
        from state import initial_state
        result = graph.invoke(initial_state("JD", "Resume"))

    assert result["error"] == "Gap analysis failed. Please try again."
    assert result["rewritten_resume"] == ""
    assert result["cover_letter"] == ""
    assert result["interview_questions"] == ""
