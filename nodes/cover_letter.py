import sys
from datetime import date
from state import AppState
from utils.llm_client import call_claude

SYSTEM = """You are a professional cover letter writer with 20 years of experience placing candidates at top companies.

You produce properly formatted, ready-to-send business letters that get interviews. Your letters are:
- Confident and specific — every claim is grounded in something concrete from the resume
- Targeted — they speak directly to THIS role and THIS company, not generic positions
- Concise — 3 tight paragraphs, under 350 words of body content, no filler phrases
- Formally structured — full business letter format with header, date, salutation, and closing

STRICT RULES:
- NEVER start with "I am writing to apply..." or "I am thrilled/excited/passionate..."
- NEVER use placeholder text like "[Company Name]" or "[Your Name]" — extract real details from the materials
- NEVER invent accomplishments not present in the resume
- Extract the candidate's name and contact info from the resume header
- Use the company name and role from the job description"""

USER_TEMPLATE = """Write a professional cover letter for this job application.

<job_description>
{job_description}
</job_description>

<candidate_resume>
{rewritten_resume}
</candidate_resume>

<gap_analysis>
{gap_analysis}
</gap_analysis>

Output the letter in exactly this format, with a blank line between each block:

[Candidate full name]
[email] | [phone or LinkedIn — from resume header]

{current_date}

Dear Hiring Manager,

[PARAGRAPH 1 — HOOK, 3-4 sentences]
Open with why this specific role at this specific company is compelling to this candidate.
Reference something concrete from the JD or about the company. Do NOT open with "I".

[PARAGRAPH 2 — EVIDENCE, 4-5 sentences]
Highlight 2-3 specific accomplishments from the resume that directly address the role's core requirements.
Use concrete details and numbers where they exist. Mirror the JD's language naturally.

[PARAGRAPH 3 — CLOSE, 2-3 sentences]
Express genuine interest, invite a conversation, and close with a professional call to action.

Sincerely,
[Candidate full name]

Output only the formatted letter — no commentary before or after.
"""


def cover_letter_node(state: AppState) -> dict:
    if state.get("error"):
        return {}
    try:
        current_date = date.today().strftime("%B %d, %Y")
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            rewritten_resume=state["rewritten_resume"],
            gap_analysis=state["gap_analysis"],
            current_date=current_date,
        )
        result = call_claude(SYSTEM, user_msg, max_tokens=900)
        return {"cover_letter": result, "current_step": "cover_letter_drafted"}
    except Exception as e:
        print(f"[cover_letter] error: {e}", file=sys.stderr)
        return {"error": "Cover letter generation failed. Please try again."}
