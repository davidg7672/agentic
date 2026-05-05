import pytest
from unittest.mock import patch
from guardrails.tone_enforcer import tone_enforcer_node


PASS_RESPONSE = "VERDICT: PASS"

FAIL_RESPONSE = """VERDICT: FAIL
ISSUES:
- Uses first-person pronoun: "I managed a team of five engineers"
- Vague subjective claim: "passionate about technology"
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_pass_verdict(base_state):
    with patch("guardrails.tone_enforcer.call_claude", return_value=PASS_RESPONSE):
        result = tone_enforcer_node(base_state)

    assert result["tone_result"]["passed"] is True
    assert result["tone_result"]["issues"] == []
    assert result["guardrail_warnings"] == []


def test_fail_verdict_extracts_issues(base_state):
    with patch("guardrails.tone_enforcer.call_claude", return_value=FAIL_RESPONSE):
        result = tone_enforcer_node(base_state)

    assert result["tone_result"]["passed"] is False
    issues = result["tone_result"]["issues"]
    assert len(issues) == 2
    assert any("first-person" in i for i in issues)
    assert any("passionate" in i for i in issues)


def test_fail_verdict_adds_warnings(base_state):
    with patch("guardrails.tone_enforcer.call_claude", return_value=FAIL_RESPONSE):
        result = tone_enforcer_node(base_state)

    warnings = result["guardrail_warnings"]
    assert all(w.startswith("[Tone]") for w in warnings)
    assert len(warnings) == 2


def test_severity_is_always_warning(base_state):
    with patch("guardrails.tone_enforcer.call_claude", return_value=PASS_RESPONSE):
        result = tone_enforcer_node(base_state)
    assert result["tone_result"]["severity"] == "warning"


def test_existing_warnings_preserved(base_state):
    base_state["guardrail_warnings"] = ["[Fabrication] Something"]
    with patch("guardrails.tone_enforcer.call_claude", return_value=FAIL_RESPONSE):
        result = tone_enforcer_node(base_state)

    warnings = result["guardrail_warnings"]
    assert any("[Fabrication]" in w for w in warnings)
    assert any("[Tone]" in w for w in warnings)


def test_pass_with_extra_text_still_passes(base_state):
    # VERDICT: PASS anywhere in the response should trigger pass
    response = "Some preamble\nVERDICT: PASS\nSome trailing text"
    with patch("guardrails.tone_enforcer.call_claude", return_value=response):
        result = tone_enforcer_node(base_state)
    assert result["tone_result"]["passed"] is True


def test_fail_with_no_issue_lines(base_state):
    response = "VERDICT: FAIL\nISSUES:\n"
    with patch("guardrails.tone_enforcer.call_claude", return_value=response):
        result = tone_enforcer_node(base_state)
    assert result["tone_result"]["passed"] is False
    assert result["tone_result"]["issues"] == []


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def test_skips_when_error_in_state(error_state):
    with patch("guardrails.tone_enforcer.call_claude") as mock_llm:
        result = tone_enforcer_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


def test_skips_when_no_rewritten_resume(base_state):
    base_state["rewritten_resume"] = ""
    with patch("guardrails.tone_enforcer.call_claude") as mock_llm:
        result = tone_enforcer_node(base_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_call_claude_exception_returns_failed_result(base_state):
    with patch("guardrails.tone_enforcer.call_claude",
               side_effect=RuntimeError("connection reset")):
        result = tone_enforcer_node(base_state)

    assert result["tone_result"]["passed"] is False
    assert any("caution" in w.lower() for w in result["guardrail_warnings"])
