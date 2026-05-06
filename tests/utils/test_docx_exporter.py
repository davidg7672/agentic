import io
import pytest
from docx import Document
from docx.shared import Pt

from utils.docx_exporter import (
    resume_to_docx,
    cover_letter_to_docx,
    _delatex,
    _BODY_PT,
    _FONT,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

RESUME_LATEX = r"""
\documentclass[10pt,letterpaper]{article}
\usepackage{tabularx}
\newcommand{\skillrow}[2]{\noindent\begin{tabularx}{\linewidth}{@{}lX@{}}\textbf{#1} & #2\\\end{tabularx}}
\begin{document}

\begin{center}
{\LARGE\textbf{Jane Doe}}\\[2pt]
\small jane@example.com | \href{https://linkedin.com/in/jane}{linkedin.com/in/jane}
\end{center}

\section*{EDUCATION}
\textbf{State University}\hfill City, State\\
\textit{B.S. Computer Science, GPA: 3.8}\hfill May 2018

\section*{RELEVANT SKILLS}
\skillrow{Languages:}{Python | SQL | JavaScript}
\skillrow{Frameworks:}{FastAPI | Django | React}

\section*{TECHNICAL EXPERIENCE}
\textbf{StartupXYZ}\hfill Remote\\
\textit{Software Engineer}\hfill 2020 -- Present
\begin{itemize}
  \item Built \textbf{RESTful API} endpoints in Python serving 50k daily requests.
  \item Managed PostgreSQL databases with 10M+ records.
\end{itemize}

\textbf{WebAgency}\hfill New York, NY\\
\textit{Junior Developer}\hfill 2018 -- 2020
\begin{itemize}
  \item Developed Python-based internal tooling.
\end{itemize}

\section*{PERSONAL PROJECTS}
\textbf{ML Pipeline -- Personal}
\begin{itemize}
  \item Built end-to-end \textbf{machine learning} pipeline with scikit-learn.
\end{itemize}

\end{document}
""".strip()


def _load(docx_bytes: bytes) -> Document:
    return Document(io.BytesIO(docx_bytes))


def _all_text(doc: Document) -> str:
    return "\n".join(p.text for p in doc.paragraphs)


# ---------------------------------------------------------------------------
# resume_to_docx — output type and validity
# ---------------------------------------------------------------------------

def test_resume_to_docx_returns_bytes():
    result = resume_to_docx(RESUME_LATEX)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_resume_to_docx_is_valid_zip_docx():
    result = resume_to_docx(RESUME_LATEX)
    assert result[:2] == b"PK", "DOCX must be a ZIP file (PK header)"


def test_resume_to_docx_is_openable_by_python_docx():
    result = resume_to_docx(RESUME_LATEX)
    doc = _load(result)
    assert len(doc.paragraphs) > 0


# ---------------------------------------------------------------------------
# resume_to_docx — content presence
# ---------------------------------------------------------------------------

def test_resume_contains_candidate_name():
    doc = _load(resume_to_docx(RESUME_LATEX))
    assert "Jane Doe" in _all_text(doc)


def test_resume_contains_section_headers():
    doc = _load(resume_to_docx(RESUME_LATEX))
    text = _all_text(doc)
    assert "EDUCATION" in text
    assert "RELEVANT SKILLS" in text
    assert "TECHNICAL EXPERIENCE" in text
    assert "PERSONAL PROJECTS" in text


def test_resume_contains_experience_entries():
    doc = _load(resume_to_docx(RESUME_LATEX))
    text = _all_text(doc)
    assert "StartupXYZ" in text
    assert "WebAgency" in text


def test_resume_contains_skill_rows():
    doc = _load(resume_to_docx(RESUME_LATEX))
    text = _all_text(doc)
    assert "Python" in text
    assert "FastAPI" in text


# ---------------------------------------------------------------------------
# resume_to_docx — formatting: bullets
# ---------------------------------------------------------------------------

def test_bullets_use_plain_paragraph_not_list_bullet_style():
    doc = _load(resume_to_docx(RESUME_LATEX))
    bullet_paras = [p for p in doc.paragraphs if p.text.startswith("•")]
    assert len(bullet_paras) >= 3, "Expected at least 3 bullet paragraphs"
    for p in bullet_paras:
        assert p.style.name != "List Bullet", (
            "Bullet paragraphs must not use 'List Bullet' style — it overrides indentation"
        )


def test_bullets_have_unicode_bullet_character():
    doc = _load(resume_to_docx(RESUME_LATEX))
    bullet_texts = [p.text for p in doc.paragraphs if "•" in p.text]
    assert len(bullet_texts) >= 3


def test_bullets_contain_expected_content():
    doc = _load(resume_to_docx(RESUME_LATEX))
    full = _all_text(doc)
    assert "50k daily requests" in full
    assert "PostgreSQL" in full
    assert "scikit-learn" in full


# ---------------------------------------------------------------------------
# resume_to_docx — formatting: bold keywords in bullets
# ---------------------------------------------------------------------------

def test_textbf_in_bullet_renders_as_bold_run():
    doc = _load(resume_to_docx(RESUME_LATEX))
    # Find the paragraph containing "RESTful API"
    target = next(
        (p for p in doc.paragraphs if "RESTful API" in p.text), None
    )
    assert target is not None, "Bullet with 'RESTful API' not found"
    bold_runs = [r for r in target.runs if r.bold and "RESTful API" in r.text]
    assert bold_runs, "Expected 'RESTful API' to be rendered as a bold run"


def test_textbf_in_project_bullet_renders_as_bold_run():
    doc = _load(resume_to_docx(RESUME_LATEX))
    target = next(
        (p for p in doc.paragraphs if "machine learning" in p.text), None
    )
    assert target is not None, "Bullet with 'machine learning' not found"
    bold_runs = [r for r in target.runs if r.bold and "machine learning" in r.text]
    assert bold_runs, "Expected 'machine learning' to be a bold run"


# ---------------------------------------------------------------------------
# resume_to_docx — formatting: section spacing
# ---------------------------------------------------------------------------

def test_section_headers_have_correct_space_before():
    doc = _load(resume_to_docx(RESUME_LATEX))
    section_paras = [p for p in doc.paragraphs if p.text in
                     ("EDUCATION", "RELEVANT SKILLS", "TECHNICAL EXPERIENCE", "PERSONAL PROJECTS")]
    assert len(section_paras) >= 4
    for p in section_paras:
        assert p.paragraph_format.space_before == Pt(8), (
            f"Section '{p.text}' space_before should be 8pt"
        )


def test_section_headers_have_correct_space_after():
    doc = _load(resume_to_docx(RESUME_LATEX))
    section_paras = [p for p in doc.paragraphs if p.text in
                     ("EDUCATION", "RELEVANT SKILLS", "TECHNICAL EXPERIENCE", "PERSONAL PROJECTS")]
    for p in section_paras:
        assert p.paragraph_format.space_after == Pt(4), (
            f"Section '{p.text}' space_after should be 4pt"
        )


# ---------------------------------------------------------------------------
# resume_to_docx — formatting: default font and page margins
# ---------------------------------------------------------------------------

def test_default_font_is_calibri():
    doc = _load(resume_to_docx(RESUME_LATEX))
    assert doc.styles["Normal"].font.name == _FONT


def test_page_margins_match_latex():
    from docx.shared import Inches as _Inches
    doc = _load(resume_to_docx(RESUME_LATEX))
    sec = doc.sections[0]
    assert abs(sec.left_margin - _Inches(0.65)) < 100   # within ~1pt tolerance
    assert abs(sec.top_margin - _Inches(0.50)) < 100


# ---------------------------------------------------------------------------
# resume_to_docx — edge cases
# ---------------------------------------------------------------------------

def test_empty_latex_returns_valid_docx():
    result = resume_to_docx("")
    assert result[:2] == b"PK"


def test_latex_without_document_tags_still_parses():
    bare = r"\section*{SKILLS}" + "\n" + r"\skillrow{Languages:}{Python | Go}"
    result = resume_to_docx(bare)
    doc = _load(result)
    assert "SKILLS" in _all_text(doc)


# ---------------------------------------------------------------------------
# _delatex — unit tests
# ---------------------------------------------------------------------------

def test_delatex_strips_textbf():
    assert _delatex(r"\textbf{hello}") == "hello"


def test_delatex_strips_textit():
    assert _delatex(r"\textit{world}") == "world"


def test_delatex_strips_href():
    assert _delatex(r"\href{https://example.com}{Example}") == "Example"


def test_delatex_unescapes_special_chars():
    assert _delatex(r"AT\&T") == "AT&T"
    assert _delatex(r"100\%") == "100%"
    assert _delatex(r"item\_key") == "item_key"


def test_delatex_strips_hfill():
    assert "hfill" not in _delatex(r"left\hfill right")


def test_delatex_strips_trailing_backslash():
    assert _delatex(r"Remote\\") == "Remote"


def test_delatex_converts_dashes():
    assert "–" in _delatex(r"2020 -- Present")
    assert "—" in _delatex(r"em---dash")


# ---------------------------------------------------------------------------
# cover_letter_to_docx
# ---------------------------------------------------------------------------

COVER_LETTER = (
    "Jane Doe\njane@example.com\n\n"
    "Dear Hiring Manager,\n\n"
    "Opening paragraph with **bold term** here.\n\n"
    "Closing paragraph.\n\n"
    "Sincerely,\nJane Doe"
)


def test_cover_letter_returns_bytes():
    result = cover_letter_to_docx(COVER_LETTER)
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_cover_letter_contains_content():
    doc = _load(cover_letter_to_docx(COVER_LETTER))
    text = _all_text(doc)
    assert "Dear Hiring Manager" in text
    assert "Sincerely" in text


def test_cover_letter_strips_markdown_bold():
    doc = _load(cover_letter_to_docx(COVER_LETTER))
    text = _all_text(doc)
    assert "**" not in text
    assert "bold term" in text
