"""Compile LaTeX source strings to PDF bytes using tectonic."""
import os
import shutil
import subprocess
import tempfile


def _tectonic_bin() -> str:
    path = shutil.which("tectonic")
    if path:
        return path
    # Homebrew on Intel Mac
    if os.path.isfile("/usr/local/bin/tectonic"):
        return "/usr/local/bin/tectonic"
    # Homebrew on Apple Silicon
    if os.path.isfile("/opt/homebrew/bin/tectonic"):
        return "/opt/homebrew/bin/tectonic"
    raise FileNotFoundError(
        "tectonic not found. Install it with: brew install tectonic"
    )


def resume_to_pdf(latex_source: str) -> bytes:
    """Compile *latex_source* with tectonic and return the PDF bytes."""
    tectonic = _tectonic_bin()

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        pdf_path = os.path.join(tmpdir, "resume.pdf")

        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(latex_source)

        result = subprocess.run(
            [tectonic, "--outdir", tmpdir, tex_path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"tectonic compilation failed:\n{result.stderr or result.stdout}"
            )

        with open(pdf_path, "rb") as fh:
            return fh.read()


def _escape_latex(text: str) -> str:
    """Escape plain text so it is safe to embed in a LaTeX document."""
    placeholder = "\x00BS\x00"
    text = text.replace("\\", placeholder)
    for char, repl in [
        ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
        ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]:
        text = text.replace(char, repl)
    return text.replace(placeholder, r"\textbackslash{}")


def cover_letter_to_pdf(letter_text: str) -> bytes:
    """Render a plain-text cover letter as a clean 1-page PDF."""
    import re as _re
    # Strip markdown bold/italic before LaTeX escaping so ** don't appear literally
    clean = _re.sub(r"\*\*(.+?)\*\*", r"\1", letter_text)
    clean = _re.sub(r"\*([^*]+?)\*", r"\1", clean)
    paragraphs = [_escape_latex(p.strip()) for p in clean.strip().split("\n\n") if p.strip()]
    body = "\n\n".join(paragraphs)

    latex = (
        r"\documentclass[10.5pt,letterpaper]{article}" + "\n"
        r"\usepackage[top=1in,bottom=1in,left=1in,right=1in]{geometry}" + "\n"
        r"\usepackage[T1]{fontenc}" + "\n"
        r"\usepackage[utf8]{inputenc}" + "\n"
        r"\usepackage{microtype}" + "\n"
        r"\setlength{\parindent}{0pt}" + "\n"
        r"\setlength{\parskip}{11pt}" + "\n"
        r"\pagestyle{empty}" + "\n"
        r"\begin{document}" + "\n"
        + body + "\n"
        r"\end{document}"
    )

    return resume_to_pdf(latex)
