import json
import pytest
from unittest.mock import patch
from guardrails.fabrication_detector import fabrication_detector_node


def _make_response(verdict: str, fabrications: list) -> str:
    return json.dumps({"verdict": verdict, "fabrications": fabrications})


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_clean_verdict_passes(base_state):
    with patch("guardrails.fabrication_detector.call_claude",
               return_value=_make_response("clean", [])):
        result = fabrication_detector_node(base_state)

    assert result["fabrication_result"]["passed"] is True
    assert result["fabrication_result"]["issues"] == []
    assert result["fabrication_result"]["severity"] == "warning"
    assert result["guardrail_warnings"] == []


def test_flagged_verdict_adds_warnings(base_state):
    fabrications = ["Added AWS certification not in original", "Claimed 'Kubernetes expert'"]
    with patch("guardrails.fabrication_detector.call_claude",
               return_value=_make_response("flagged", fabrications)):
        result = fabrication_detector_node(base_state)

    assert result["fabrication_result"]["passed"] is False
    assert result["fabrication_result"]["issues"] == fabrications
    warnings = result["guardrail_warnings"]
    assert any("AWS certification" in w for w in warnings)
    assert any("Kubernetes expert" in w for w in warnings)


def test_fabrication_warnings_prefixed(base_state):
    with patch("guardrails.fabrication_detector.call_claude",
               return_value=_make_response("flagged", ["Made-up skill"])):
        result = fabrication_detector_node(base_state)

    assert any(w.startswith("[Fabrication]") for w in result["guardrail_warnings"])


def test_existing_warnings_preserved(base_state):
    base_state["guardrail_warnings"] = ["[Prior Warning] something"]
    with patch("guardrails.fabrication_detector.call_claude",
               return_value=_make_response("flagged", ["New fabrication"])):
        result = fabrication_detector_node(base_state)

    assert any("[Prior Warning]" in w for w in result["guardrail_warnings"])
    assert any("[Fabrication]" in w for w in result["guardrail_warnings"])


# ---------------------------------------------------------------------------
# JSON parse failure
# ---------------------------------------------------------------------------

def test_invalid_json_response_adds_warning(base_state):
    with patch("guardrails.fabrication_detector.call_claude",
               return_value="This is not JSON at all."):
        result = fabrication_detector_node(base_state)

    assert result["fabrication_result"]["passed"] is False
    assert any("unparseable" in w.lower() or "parse" in w.lower()
               for w in result["guardrail_warnings"])


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def test_skips_when_error_in_state(error_state):
    with patch("guardrails.fabrication_detector.call_claude") as mock_llm:
        result = fabrication_detector_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


def test_skips_when_no_rewritten_resume(base_state):
    base_state["rewritten_resume"] = ""
    with patch("guardrails.fabrication_detector.call_claude") as mock_llm:
        result = fabrication_detector_node(base_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_call_claude_exception_adds_warning(base_state):
    with patch("guardrails.fabrication_detector.call_claude",
               side_effect=Exception("API timeout")):
        result = fabrication_detector_node(base_state)

    assert result["fabrication_result"]["passed"] is False
    assert any("caution" in w.lower() for w in result["guardrail_warnings"])
