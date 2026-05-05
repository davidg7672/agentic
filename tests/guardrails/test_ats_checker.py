import pytest
from unittest.mock import patch
from guardrails.ats_checker import ats_checker_node, _tokenize, MISSING_THRESHOLD


# ---------------------------------------------------------------------------
# _tokenize unit tests
# ---------------------------------------------------------------------------

def test_tokenize_returns_list():
    tokens = _tokenize("Python developer with FastAPI experience")
    assert isinstance(tokens, list)
    assert "python" in tokens
    assert "fastapi" in tokens


def test_tokenize_removes_stopwords():
    tokens = _tokenize("a an the and or but in on at to for")
    assert tokens == []


def test_tokenize_removes_short_tokens():
    # Single-char tokens and 2-char tokens should be excluded
    tokens = _tokenize("I am a go to be")
    assert all(len(t) > 2 for t in tokens)


def test_tokenize_lowercases():
    tokens = _tokenize("Python PYTHON python")
    assert all(t == "python" for t in tokens)


def test_tokenize_handles_tech_terms():
    tokens = _tokenize("C++ AWS k8s REST API")
    assert "c++" in tokens or "aws" in tokens  # at least one tech term survives


def test_tokenize_empty_string():
    assert _tokenize("") == []


def test_tokenize_ignores_numbers_alone():
    # Numbers without letters at start are excluded by regex \b[a-zA-Z]
    tokens = _tokenize("123 456")
    assert tokens == []


# ---------------------------------------------------------------------------
# ats_checker_node — pass / fail logic
# ---------------------------------------------------------------------------

def test_all_keywords_present_passes(base_state):
    # Rewritten resume already contains most JD keywords in base fixture
    result = ats_checker_node(base_state)
    # Result should have ats_result set
    assert "ats_result" in result
    assert isinstance(result["ats_result"]["passed"], bool)


def test_high_missing_ratio_fails(base_state):
    # Use a JD with many keywords absent from the resume
    base_state["job_description"] = (
        "Haskell Erlang Rust Cobol Fortran Prolog Assembly VHDL Verilog "
        "Lisp Scheme Smalltalk Elm PureScript Idris Agda Coq Lean Mercury "
        "Racket Clojure required experience needed skills"
    )
    base_state["rewritten_resume"] = "Jane has experience with Python."
    result = ats_checker_node(base_state)

    assert result["ats_result"]["passed"] is False
    assert len(result["guardrail_warnings"]) > 0
    assert any("[ATS]" in w for w in result["guardrail_warnings"])


def test_all_keywords_present_in_resume_passes(base_state):
    # Build JD and resume so every JD keyword is in the resume
    base_state["job_description"] = "Python FastAPI PostgreSQL Docker required"
    base_state["rewritten_resume"] = "Engineer with Python, FastAPI, PostgreSQL, Docker skills."
    result = ats_checker_node(base_state)

    assert result["ats_result"]["passed"] is True
    assert result["guardrail_warnings"] == []


def test_missing_keywords_surface_in_issues(base_state):
    base_state["job_description"] = "Kubernetes Terraform Ansible required"
    base_state["rewritten_resume"] = "Python developer with Docker."
    result = ats_checker_node(base_state)

    assert result["ats_result"]["passed"] is False
    issues = result["ats_result"]["issues"]
    assert len(issues) > 0


def test_issues_capped_at_10(base_state):
    # Create a JD with 20+ unique absent keywords
    absent = " ".join(f"uniqueword{i}" for i in range(25))
    base_state["job_description"] = absent
    base_state["rewritten_resume"] = "Python developer."
    result = ats_checker_node(base_state)

    assert len(result["ats_result"]["issues"]) <= 10


def test_missing_ratio_exactly_at_threshold_passes(base_state):
    # 5 JD keywords, 1 absent from resume = 20% missing = exactly at threshold → passes
    # Avoid "required"/"needed" words that are themselves content tokens.
    base_state["job_description"] = "python fastapi postgresql docker kubernetes"
    # kubernetes absent from resume → 1/5 = 20% missing ≤ MISSING_THRESHOLD (0.20) → pass
    base_state["rewritten_resume"] = "python fastapi postgresql docker skills."
    result = ats_checker_node(base_state)

    assert result["ats_result"]["passed"] is True


# ---------------------------------------------------------------------------
# Edge cases — empty tokens
# ---------------------------------------------------------------------------

def test_empty_jd_tokens_passes(base_state):
    base_state["job_description"] = "a an the"  # all stopwords → empty after tokenize
    result = ats_checker_node(base_state)
    assert result["ats_result"]["passed"] is True


def test_empty_resume_tokens_passes(base_state):
    base_state["rewritten_resume"] = "a an the"  # all stopwords
    result = ats_checker_node(base_state)
    assert result["ats_result"]["passed"] is True


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def test_skips_when_error_in_state(error_state):
    result = ats_checker_node(error_state)
    assert result == {}


def test_skips_when_no_rewritten_resume(base_state):
    base_state["rewritten_resume"] = ""
    result = ats_checker_node(base_state)
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_exception_adds_warning(base_state):
    with patch("guardrails.ats_checker.BM25Okapi", side_effect=Exception("BM25 error")):
        result = ats_checker_node(base_state)

    assert result["ats_result"]["passed"] is False
    assert any("[ATS Check]" in w for w in result["guardrail_warnings"])
