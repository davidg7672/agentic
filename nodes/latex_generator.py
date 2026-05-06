import re
import sys
from state import AppState
from utils.llm_client import call_claude


_SKILLS_SECTION = re.compile(
    r"(\\section\*\{(?:RELEVANT SKILLS|ADDITIONAL SKILLS)[^}]*\}.*?)(?=\\section\*\{|\\end\{document\})",
    re.DOTALL,
)
_MD_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")


def _apply_markdown_bold(latex: str) -> str:
    """Convert **markdown bold** → \\textbf{} except inside skills sections."""
    skills_spans = [(m.start(), m.end()) for m in _SKILLS_SECTION.finditer(latex)]

    def _in_skills(pos: int) -> bool:
        return any(s <= pos < e for s, e in skills_spans)

    parts: list[str] = []
    cursor = 0
    for m in _MD_BOLD.finditer(latex):
        parts.append(latex[cursor:m.start()])
        if _in_skills(m.start()):
            parts.append(m.group(0))  # leave unchanged inside skills
        else:
            parts.append(rf"\textbf{{{m.group(1)}}}")
        cursor = m.end()
    parts.append(latex[cursor:])
    return "".join(parts)


def _trim_skillrows(latex: str) -> str:
    """Drop individual skills that would make a single row absurdly long.

    tabularx wraps multi-skill rows automatically, so trimming is only a
    last-resort guard against a single skill name wider than the whole page.
    Budget: ~86 printable characters across the full text width (7.2 in at
    10 pt) minus the label length so each remaining token fits on one wrapped
    line at minimum.
    """
    PAGE_CHARS = 86

    def _trim(m: re.Match) -> str:
        label, skills = m.group(1), m.group(2)
        budget = PAGE_CHARS - len(label)
        parts = [s.strip() for s in skills.split("|")]
        kept = [p for p in parts if len(p) <= budget]
        if len(kept) == len(parts):
            return m.group(0)
        return rf"\skillrow{{{label}}}{{{' | '.join(kept)}}}"

    return re.sub(r"\\skillrow\{([^}]+)\}\{([^}]+)\}", _trim, latex)

_PREAMBLE = r"""
\documentclass[10pt,letterpaper]{article}
\usepackage[top=0.50in, bottom=0.50in, left=0.65in, right=0.65in]{geometry}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage{tabularx}

% Label takes natural width; skills fill the rest and wrap within the margin
\newcommand{\skillrow}[2]{%
  \noindent\begin{tabularx}{\linewidth}{@{}lX@{}}%
    \textbf{#1} & #2\\%
  \end{tabularx}\vspace{-2pt}%
}

\titleformat{\section}{\bfseries\normalsize}{}{0em}{}[\vspace{-4pt}\rule{\linewidth}{0.4pt}\vspace{-4pt}]
\titlespacing*{\section}{0pt}{8pt}{4pt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\pagestyle{empty}

\setlist[itemize]{
  leftmargin=1.5em,
  topsep=2pt,
  itemsep=0pt,
  parsep=0pt,
  label=\textbullet
}
""".strip()

_EXAMPLE = r"""
\begin{document}

\begin{center}
{\LARGE\textbf{First Last}}\\[2pt]
\small email@example.com | \href{https://linkedin.com/in/handle}{linkedin.com/in/handle} | \href{https://site.com}{site.com}
\end{center}

\section*{EDUCATION}
\textbf{University Name}\hfill City, State\\
\textit{Degree, GPA: X.X}\hfill Graduation: Month Year

\section*{RELEVANT SKILLS}
\skillrow{Category A:}{Skill1 | Skill2 | Skill3}
\skillrow{Category B:}{Skill4 | Skill5}

\section*{TECHNICAL EXPERIENCE}
\textbf{Company Name}\hfill City, State\\
\textit{Job Title}\hfill Month Year -- Month Year
\begin{itemize}
  \item Accomplished X by doing Y, resulting in Z.
  \item Built system using Tech1 and Tech2.
\end{itemize}

\section*{PERSONAL PROJECTS}
\textbf{Project Name -- Organization}
\begin{itemize}
  \item Description of what was built and its impact.
\end{itemize}

\section*{ADDITIONAL SKILLS}
\textbf{Languages:} English | Spanish

\end{document}
""".strip()

SYSTEM = f"""You are a professional LaTeX typesetter. Convert resume content into valid LaTeX that \
produces exactly one letter-size page when compiled.

STRICT RULES:
1. Output ONLY raw LaTeX — no triple-backtick fences, no comments, no explanations.
2. The result MUST fit on exactly 1 page. Cut sections in this order if needed: Hobbies, then \
minor side-projects, then reduce bullets to 2 per role/project. Never cut Education or Skills.
3. Escape these LaTeX special characters in all content text:
     &  →  \\&      %  →  \\%      $  →  \\$      #  →  \\#
     _  →  \\_      {{  →  \\{{    }}  →  \\}}
4. Use \\hfill between left-aligned and right-aligned content on the same line.
5. Use \\href{{url}}{{display text}} for hyperlinks.
6. Use | (plain pipe) as a separator in skill and contact lines — not $|$.
7. Do NOT invent or add any content not present in the resume.
8. Section headers must be uppercase: \\section*{{EDUCATION}}, \\section*{{RELEVANT SKILLS}}, etc.
9. RELEVANT SKILLS section MUST use \\skillrow{{Label:}}{{skills}} for every skill line — never plain \\textbf{{}} with a trailing \\\\. Long skill lists wrap automatically within the right margin; do NOT split one row into two to handle length.
10. The resume text may contain **double-asterisk** wrapped phrases (markdown bold). Convert each \
**phrase** to \\textbf{{phrase}} in LaTeX — but ONLY inside TECHNICAL EXPERIENCE and PERSONAL \
PROJECTS sections. Never apply \\textbf{{}} to anything inside RELEVANT SKILLS or ADDITIONAL SKILLS.

Use exactly this preamble (do not change it):

{_PREAMBLE}

Follow this document structure:

{_EXAMPLE}"""

USER_TEMPLATE = """Convert the following rewritten resume into LaTeX following the rules and \
structure above. Output only the complete LaTeX source starting with \\begin{{document}}.

<rewritten_resume>
{rewritten_resume}
</rewritten_resume>"""


def latex_generator_node(state: AppState) -> dict:
    if state.get("error") or not state.get("rewritten_resume"):
        return {}
    try:
        user_msg = USER_TEMPLATE.format(rewritten_resume=state["rewritten_resume"])
        raw = call_claude(SYSTEM, user_msg, max_tokens=3000)

        # Strip accidental fences Claude might add
        body = raw.strip()
        if body.startswith("```"):
            body = body.split("\n", 1)[1] if "\n" in body else body
        if body.endswith("```"):
            body = body.rsplit("```", 1)[0]
        body = body.strip()

        # Prepend the fixed preamble so the file is always complete
        if not body.startswith(r"\documentclass"):
            latex_source = _PREAMBLE + "\n\n" + body
        else:
            latex_source = body

        latex_source = _trim_skillrows(latex_source)
        latex_source = _apply_markdown_bold(latex_source)
        return {"latex_source": latex_source, "current_step": "latex_generated"}
    except Exception as e:
        print(f"[latex_generator] error: {e}", file=sys.stderr)
        # Non-fatal: PDF just won't be available
        return {"latex_source": ""}
