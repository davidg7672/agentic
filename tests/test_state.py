import pytest
from state import initial_state, AppState, GuardrailResult


def test_initial_state_stores_inputs():
    state = initial_state("job desc", "my resume")
    assert state["job_description"] == "job desc"
    assert state["original_resume"] == "my resume"


def test_initial_state_empty_intermediate_fields():
    state = initial_state("jd", "resume")
    assert state["gap_analysis"] == ""
    assert state["rewritten_resume"] == ""
    assert state["cover_letter"] == ""
    assert state["interview_questions"] == ""


def test_initial_state_guardrail_results_are_none():
    state = initial_state("jd", "resume")
    assert state["fabrication_result"] is None
    assert state["tone_result"] is None
    assert state["ats_result"] is None


def test_initial_state_control_flow_defaults():
    state = initial_state("jd", "resume")
    assert state["guardrail_warnings"] == []
    assert state["current_step"] == "start"
    assert state["error"] is None


def test_initial_state_guardrail_warnings_is_new_list():
    s1 = initial_state("jd", "resume")
    s2 = initial_state("jd", "resume")
    s1["guardrail_warnings"].append("something")
    assert s2["guardrail_warnings"] == []


def test_guardrail_result_structure():
    result: GuardrailResult = {"passed": True, "issues": [], "severity": "warning"}
    assert result["passed"] is True
    assert result["issues"] == []
    assert result["severity"] == "warning"


def test_guardrail_result_failed_structure():
    result: GuardrailResult = {
        "passed": False,
        "issues": ["Issue 1", "Issue 2"],
        "severity": "warning",
    }
    assert result["passed"] is False
    assert len(result["issues"]) == 2
