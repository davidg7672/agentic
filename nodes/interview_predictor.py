import sys
from state import AppState
from utils.llm_client import call_claude

SYSTEM = """You are an experienced hiring manager and interview coach. You predict the most likely
interview questions a candidate will face based on the job description and their background.
For each question you provide a one-sentence rationale explaining why an interviewer would ask it."""

USER_TEMPLATE = """Predict the 10 most likely interview questions for this candidate applying to this role.

<job_description>
{job_description}
</job_description>

<candidate_resume>
{rewritten_resume}
</candidate_resume>

<identified_gaps>
{gap_analysis}
</identified_gaps>

Generate exactly 10 questions organized under these markdown headers:

### Technical / Skills Questions (3 questions)
Questions testing specific technical knowledge or skills required by the JD.

### Behavioral Questions (3 questions)
STAR-format prompts based on experiences in the candidate's resume.
Format: "Tell me about a time when..." or "Describe a situation where..."

### Gap-Probing Questions (2 questions)
Questions an interviewer would ask to explore the identified skill or experience gaps.

### Situational / Role-Specific Questions (2 questions)
Hypothetical scenario questions tied to the specific responsibilities of this role.

For each question, add: *Why this will be asked: [one sentence rationale]*
"""


def interview_predictor_node(state: AppState) -> dict:
    if state.get("error"):
        return {}
    try:
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            rewritten_resume=state["rewritten_resume"],
            gap_analysis=state["gap_analysis"],
        )
        result = call_claude(SYSTEM, user_msg, max_tokens=1400)
        return {"interview_questions": result, "current_step": "complete"}
    except Exception as e:
        print(f"[interview_predictor] error: {e}", file=sys.stderr)
        return {"error": "Interview question generation failed. Please try again."}
