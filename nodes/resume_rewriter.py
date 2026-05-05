import sys
from state import AppState
from utils.llm_client import call_claude

SYSTEM = """You are an expert resume writer specializing in ATS optimization and targeted applications.

STRICT RULES — these are non-negotiable:
1. You may ONLY use skills, experiences, technologies, and facts that appear in the original resume.
2. Do NOT invent, add, or embellish any experience, skill, certification, or achievement not present in the original.
3. Do NOT change job titles, company names, dates, or educational credentials.
4. You MAY reword existing bullets to better reflect the language used in the job description.
5. You MAY reorder sections or bullets to lead with the most relevant experience.
6. You MAY strengthen action verbs and quantify achievements only if the numbers already exist in the original.

Output the complete rewritten resume, preserving the original structure and sections."""

USER_TEMPLATE = """Rewrite this resume to better target the job description below.

<job_description>
{job_description}
</job_description>

<gap_analysis>
{gap_analysis}
</gap_analysis>

<original_resume>
{original_resume}
</original_resume>

Rewrite the resume now. Output only the rewritten resume text — no preamble, no commentary.
"""


def resume_rewriter_node(state: AppState) -> dict:
    if state.get("error"):
        return {}
    try:
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            gap_analysis=state["gap_analysis"],
            original_resume=state["original_resume"],
        )
        result = call_claude(SYSTEM, user_msg, max_tokens=2000)
        return {"rewritten_resume": result, "current_step": "resume_rewritten"}
    except Exception as e:
        print(f"[resume_rewriter] error: {e}", file=sys.stderr)
        return {"error": "Resume rewrite failed. Please try again."}
