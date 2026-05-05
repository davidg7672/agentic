import sys
from state import AppState
from utils.llm_client import call_claude

SYSTEM = """You are a senior technical recruiter with 15 years of experience.
Your task is to identify gaps between what a job requires and what a candidate's resume demonstrates.
Be precise and specific — cite exact skills, technologies, and experience levels.
Do not invent gaps that aren't clearly evidenced. Focus on what is genuinely absent."""

USER_TEMPLATE = """Analyze the following job description and resume. Identify the gaps.

<job_description>
{job_description}
</job_description>

<candidate_resume>
{original_resume}
</candidate_resume>

Output a structured analysis using these exact markdown headers:

### Missing Required Skills
List skills/technologies explicitly required in the JD that do not appear in the resume. One per line with a dash.

### Experience Level Gaps
Identify any mismatches in years of experience or seniority level required vs. demonstrated.

### Missing Nice-to-Haves
List preferred (not required) qualifications from the JD that are absent from the resume.

### Strengths Match
List 3-5 areas where the candidate's background aligns well with the role.

Be concise. If there are no gaps in a category, write "None identified."
"""


def gap_analyzer_node(state: AppState) -> dict:
    if state.get("error"):
        return {}
    try:
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            original_resume=state["original_resume"],
        )
        result = call_claude(SYSTEM, user_msg, max_tokens=700)
        return {"gap_analysis": result, "current_step": "gap_analysis_complete"}
    except Exception as e:
        print(f"[gap_analyzer] error: {e}", file=sys.stderr)
        return {"error": "Gap analysis failed. Please try again."}
