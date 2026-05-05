import sys
from state import AppState
from utils.llm_client import call_claude

SYSTEM = """You are a professional cover letter writer. You craft concise, targeted cover letters
that get candidates interviews. You write in a confident, professional tone — never sycophantic,
never desperate. You highlight specific evidence from the resume rather than vague claims."""

USER_TEMPLATE = """Write a cover letter for this job application.

<job_description>
{job_description}
</job_description>

<candidate_resume>
{rewritten_resume}
</candidate_resume>

<gap_analysis>
{gap_analysis}
</gap_analysis>

Write exactly 3 paragraphs, under 350 words total:

**Paragraph 1 — Hook:** Open with why this specific role at this specific company is compelling.
Reference something concrete from the JD. Do NOT start with "I am writing to apply..."

**Paragraph 2 — Evidence:** Highlight 2-3 specific accomplishments from the resume that directly
address the job's core requirements. Use concrete details and numbers where they exist.

**Paragraph 3 — Close:** Express genuine interest, note availability, and include a professional
call to action. Keep it brief.

Use JD terminology naturally — do not force keyword stuffing.
Output only the cover letter text. No subject line, no "[Your Name]" placeholders.
"""


def cover_letter_node(state: AppState) -> dict:
    if state.get("error"):
        return {}
    try:
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            rewritten_resume=state["rewritten_resume"],
            gap_analysis=state["gap_analysis"],
        )
        result = call_claude(SYSTEM, user_msg, max_tokens=700)
        return {"cover_letter": result, "current_step": "cover_letter_drafted"}
    except Exception as e:
        print(f"[cover_letter] error: {e}", file=sys.stderr)
        return {"error": "Cover letter generation failed. Please try again."}
