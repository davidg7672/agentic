import pytest
from unittest.mock import patch

from nodes.latex_generator import latex_generator_node, _PREAMBLE

# ---------------------------------------------------------------------------
# Sample LLM responses
# ---------------------------------------------------------------------------

_BODY_ONLY = r"""
\begin{document}

\begin{center}
{\LARGE\textbf{Jane Doe}}\\[2pt]
\small jane@example.com | linkedin.com/in/jane
\end{center}

\section*{EDUCATION}
\textbf{State University}\hfill City, State\\
\textit{B.S. Computer Science}\hfill May 2018

\section*{TECHNICAL EXPERIENCE}
\textbf{StartupXYZ}\hfill Remote\\
\textit{Software Engineer}\hfill 2020 -- Present
\begin{itemize}
  \item Built REST APIs in Python serving 50k daily requests.
\end{itemize}

\end{document}
""".strip()

_FULL_DOC = _PREAMBLE + "\n\n" + _BODY_ONLY

_FENCED_RESPONSE = "```latex\n" + _BODY_ONLY + "\n```"
_FENCED_NO_LANG = "```\n" + _BODY_ONLY + "\n```"


# ---------------------------------------------------------------------------
# Happy path — returns latex_source and step
# ---------------------------------------------------------------------------

def test_latex_generator_returns_latex_source(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY):
        result = latex_generator_node(base_state)

    assert "latex_source" in result
    assert len(result["latex_source"]) > 0


def test_latex_generator_sets_current_step(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY):
        result = latex_generator_node(base_state)

    assert result["current_step"] == "latex_generated"


def test_latex_generator_prepends_preamble_when_body_only(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY):
        result = latex_generator_node(base_state)

    src = result["latex_source"]
    assert src.startswith(r"\documentclass"), "Preamble was not prepended"
    assert r"\begin{document}" in src


def test_latex_generator_does_not_double_prepend_when_full_doc_returned(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_FULL_DOC):
        result = latex_generator_node(base_state)

    src = result["latex_source"]
    assert src.count(r"\documentclass") == 1, "Preamble was duplicated"


# ---------------------------------------------------------------------------
# Code-fence stripping
# ---------------------------------------------------------------------------

def test_latex_generator_strips_triple_backtick_latex_fence(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_FENCED_RESPONSE):
        result = latex_generator_node(base_state)

    assert "```" not in result["latex_source"]
    assert r"\begin{document}" in result["latex_source"]


def test_latex_generator_strips_plain_triple_backtick_fence(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_FENCED_NO_LANG):
        result = latex_generator_node(base_state)

    assert "```" not in result["latex_source"]


# ---------------------------------------------------------------------------
# Claude is called with the right inputs
# ---------------------------------------------------------------------------

def test_latex_generator_calls_claude_with_rewritten_resume(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY) as mock_llm:
        latex_generator_node(base_state)

    user_msg = mock_llm.call_args[0][1]
    assert base_state["rewritten_resume"] in user_msg


def test_latex_generator_requests_enough_tokens(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY) as mock_llm:
        latex_generator_node(base_state)

    assert mock_llm.call_args[1]["max_tokens"] >= 2000


def test_latex_generator_preamble_in_system_prompt(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY) as mock_llm:
        latex_generator_node(base_state)

    system_msg = mock_llm.call_args[0][0]
    assert r"\documentclass" in system_msg


# ---------------------------------------------------------------------------
# Skip / no-op conditions
# ---------------------------------------------------------------------------

def test_latex_generator_skips_when_error_set(error_state):
    with patch("nodes.latex_generator.call_claude") as mock_llm:
        result = latex_generator_node(error_state)

    mock_llm.assert_not_called()
    assert result == {}


def test_latex_generator_skips_when_rewritten_resume_is_empty(base_state):
    base_state["rewritten_resume"] = ""
    with patch("nodes.latex_generator.call_claude") as mock_llm:
        result = latex_generator_node(base_state)

    mock_llm.assert_not_called()
    assert result == {}


# ---------------------------------------------------------------------------
# Exception handling — non-fatal
# ---------------------------------------------------------------------------

def test_latex_generator_returns_empty_string_on_llm_exception(base_state):
    with patch("nodes.latex_generator.call_claude", side_effect=RuntimeError("timeout")):
        result = latex_generator_node(base_state)

    assert result == {"latex_source": ""}


def test_latex_generator_does_not_set_error_key_on_exception(base_state):
    with patch("nodes.latex_generator.call_claude", side_effect=RuntimeError("timeout")):
        result = latex_generator_node(base_state)

    assert "error" not in result


def test_latex_generator_does_not_set_current_step_on_exception(base_state):
    with patch("nodes.latex_generator.call_claude", side_effect=RuntimeError("timeout")):
        result = latex_generator_node(base_state)

    assert "current_step" not in result


# ---------------------------------------------------------------------------
# Output structure sanity checks
# ---------------------------------------------------------------------------

def test_latex_generator_output_contains_end_document(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY):
        result = latex_generator_node(base_state)

    assert r"\end{document}" in result["latex_source"]


def test_latex_generator_output_is_string(base_state):
    with patch("nodes.latex_generator.call_claude", return_value=_BODY_ONLY):
        result = latex_generator_node(base_state)

    assert isinstance(result["latex_source"], str)
