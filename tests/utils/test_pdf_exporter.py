import os
import shutil
from unittest.mock import MagicMock, patch

import pytest

from utils.pdf_exporter import _tectonic_bin, resume_to_pdf

# ---------------------------------------------------------------------------
# Minimal LaTeX documents used across tests
# ---------------------------------------------------------------------------

MINIMAL_LATEX = r"""
\documentclass[10pt,letterpaper]{article}
\begin{document}
Hello, World!
\end{document}
""".strip()

RESUME_LATEX = r"""
\documentclass[10pt,letterpaper]{article}
\usepackage[top=0.50in, bottom=0.50in, left=0.65in, right=0.65in]{geometry}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{titlesec}

\newcommand{\skillrow}[2]{%
  \noindent\hbox{\textbf{#1} #2}\par\vspace{1pt}%
}

\titleformat{\section}{\bfseries\normalsize}{}{0em}{}[\vspace{-4pt}\rule{\linewidth}{0.4pt}\vspace{-4pt}]
\titlespacing*{\section}{0pt}{8pt}{4pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\pagestyle{empty}
\setlist[itemize]{leftmargin=1.5em,topsep=2pt,itemsep=0pt,parsep=0pt,label=\textbullet}

\begin{document}

\begin{center}
{\LARGE\textbf{Jane Doe}}\\[2pt]
\small jane@example.com | \href{https://linkedin.com/in/jane}{linkedin.com/in/jane}
\end{center}

\section*{EDUCATION}
\textbf{State University}\hfill City, State\\
\textit{B.S. Computer Science}\hfill May 2018

\section*{RELEVANT SKILLS}
\skillrow{Programming Languages:}{Python | SQL | JavaScript}

\section*{TECHNICAL EXPERIENCE}
\textbf{StartupXYZ}\hfill Remote\\
\textit{Software Engineer}\hfill 2020 -- Present
\begin{itemize}
  \item Built REST APIs in Python serving 50k daily requests.
  \item Managed PostgreSQL databases with 10M+ records.
\end{itemize}

\end{document}
""".strip()


# ---------------------------------------------------------------------------
# _tectonic_bin
# ---------------------------------------------------------------------------

def test_tectonic_bin_returns_valid_path():
    path = _tectonic_bin()
    assert os.path.isfile(path), f"Expected a file at: {path}"


def test_tectonic_bin_uses_shutil_which_first():
    with patch("utils.pdf_exporter.shutil.which", return_value="/custom/tectonic"):
        assert _tectonic_bin() == "/custom/tectonic"


def test_tectonic_bin_falls_back_to_intel_homebrew():
    with patch("utils.pdf_exporter.shutil.which", return_value=None):
        with patch("utils.pdf_exporter.os.path.isfile", side_effect=lambda p: p == "/usr/local/bin/tectonic"):
            assert _tectonic_bin() == "/usr/local/bin/tectonic"


def test_tectonic_bin_falls_back_to_apple_silicon_homebrew():
    with patch("utils.pdf_exporter.shutil.which", return_value=None):
        with patch("utils.pdf_exporter.os.path.isfile", side_effect=lambda p: p == "/opt/homebrew/bin/tectonic"):
            assert _tectonic_bin() == "/opt/homebrew/bin/tectonic"


def test_tectonic_bin_raises_when_not_found_anywhere():
    with patch("utils.pdf_exporter.shutil.which", return_value=None):
        with patch("utils.pdf_exporter.os.path.isfile", return_value=False):
            with pytest.raises(FileNotFoundError, match="tectonic not found"):
                _tectonic_bin()


# ---------------------------------------------------------------------------
# resume_to_pdf — integration (real tectonic compile)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic not installed")
def test_resume_to_pdf_returns_bytes_starting_with_pdf_header():
    pdf = resume_to_pdf(MINIMAL_LATEX)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF", "Output does not look like a PDF file"


@pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic not installed")
def test_resume_to_pdf_full_resume_template_compiles():
    pdf = resume_to_pdf(RESUME_LATEX)
    assert pdf[:4] == b"%PDF"


@pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic not installed")
def test_skillrow_compiles_with_overflow_length_skills():
    """\\skillrow must compile without errors even when skill lists would normally wrap."""
    latex = r"""
\documentclass[10pt,letterpaper]{article}
\usepackage[top=0.50in,bottom=0.50in,left=0.65in,right=0.65in]{geometry}
\setlength{\parindent}{0pt}
\pagestyle{empty}
\newcommand{\skillrow}[2]{%
  \noindent\hbox{\textbf{#1} #2}\par\vspace{1pt}%
}
\begin{document}
\skillrow{Programming Languages:}{Python | Java | JavaScript | C/C++ | SQL | Linux | Git | Excel | Bash | TypeScript | Go | Rust | Scala | Kotlin}
\skillrow{Frameworks/Technologies:}{PostgreSQL | LangChain | LangGraph | LlamaIndex | Azure | Docker | Kubernetes | FastAPI | Django | Redis | Celery}
\skillrow{Technical Experience:}{Claude | Cursor | RAG Development | Multiagent Development | AnthropicAPI | OpenAI | Pinecone | Weaviate | HuggingFace}
\end{document}
""".strip()
    pdf = resume_to_pdf(latex)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000, "PDF seems suspiciously small"


# ---------------------------------------------------------------------------
# resume_to_pdf — unit (subprocess mocked)
# ---------------------------------------------------------------------------

def _make_run_success(fake_pdf: bytes = b"%PDF-1.4 fake"):
    """Return a mock that writes fake_pdf to the expected output path."""
    def run_side_effect(cmd, **kwargs):
        # Locate the --outdir argument and write the fake PDF there
        outdir = cmd[cmd.index("--outdir") + 1]
        pdf_path = os.path.join(outdir, "resume.pdf")
        with open(pdf_path, "wb") as fh:
            fh.write(fake_pdf)
        return MagicMock(returncode=0, stderr="", stdout="")
    return run_side_effect


def test_resume_to_pdf_raises_runtime_error_on_compile_failure():
    with patch("utils.pdf_exporter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="! Undefined control sequence.", stdout=""
        )
        with pytest.raises(RuntimeError, match="tectonic compilation failed"):
            resume_to_pdf(MINIMAL_LATEX)


def test_resume_to_pdf_error_message_includes_stderr():
    with patch("utils.pdf_exporter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Specific error detail", stdout=""
        )
        with pytest.raises(RuntimeError, match="Specific error detail"):
            resume_to_pdf(MINIMAL_LATEX)


def test_resume_to_pdf_passes_outdir_flag_to_tectonic():
    with patch("utils.pdf_exporter.subprocess.run", side_effect=_make_run_success()) as mock_run:
        resume_to_pdf(MINIMAL_LATEX)

    cmd = mock_run.call_args[0][0]
    assert "--outdir" in cmd


def test_resume_to_pdf_tex_file_written_before_tectonic_called():
    written_content = {}

    def run_side_effect(cmd, **kwargs):
        outdir = cmd[cmd.index("--outdir") + 1]
        tex_path = os.path.join(outdir, "resume.tex")
        # Capture what was written to the tex file
        with open(tex_path, "r") as fh:
            written_content["tex"] = fh.read()
        # Write fake PDF output
        with open(os.path.join(outdir, "resume.pdf"), "wb") as fh:
            fh.write(b"%PDF-fake")
        return MagicMock(returncode=0, stderr="", stdout="")

    with patch("utils.pdf_exporter.subprocess.run", side_effect=run_side_effect):
        resume_to_pdf(MINIMAL_LATEX)

    assert written_content["tex"] == MINIMAL_LATEX


def test_resume_to_pdf_returns_exact_pdf_bytes():
    expected = b"%PDF-1.4 this-is-the-fake-pdf"

    with patch("utils.pdf_exporter.subprocess.run", side_effect=_make_run_success(expected)):
        result = resume_to_pdf(MINIMAL_LATEX)

    assert result == expected


def test_resume_to_pdf_temp_dir_is_cleaned_up():
    created_dirs = []

    original_tmp = __import__("tempfile").TemporaryDirectory

    class TrackingTmpDir:
        def __init__(self):
            self._real = original_tmp()
            created_dirs.append(self._real.name)

        def __enter__(self):
            return self._real.__enter__()

        def __exit__(self, *args):
            return self._real.__exit__(*args)

    with patch("utils.pdf_exporter.subprocess.run", side_effect=_make_run_success()):
        with patch("utils.pdf_exporter.tempfile.TemporaryDirectory", TrackingTmpDir):
            resume_to_pdf(MINIMAL_LATEX)

    assert created_dirs, "No temp directory was created"
    assert not os.path.exists(created_dirs[0]), "Temp directory was not cleaned up"
