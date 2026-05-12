import json
import sys
from state import AppState, FitScore
from utils.llm_client import call_claude
from utils.json_helpers import extract_json

SYSTEM = """You are a hiring expert that scores how well a candidate's resume matches a job description.
You return ONLY valid JSON with no preamble or explanation outside the JSON."""

USER_TEMPLATE = """Score the candidate's fit for this role based on the gap analysis provided.

<job_description>
{job_description}
</job_description>

<original_resume>
{original_resume}
</original_resume>

<gap_analysis>
{gap_analysis}
</gap_analysis>

Return this exact JSON structure with no other text:
{{
  "overall": <weighted integer 0-100>,
  "tier": "<Exceptional|Strong Match|Viable|Stretch>",
  "breakdown": {{
    "required_skills":  {{ "score": <0-100>, "weight": 0.40 }},
    "experience_level": {{ "score": <0-100>, "weight": 0.25 }},
    "nice_to_haves":    {{ "score": <0-100>, "weight": 0.15 }},
    "domain_alignment": {{ "score": <0-100>, "weight": 0.20 }}
  }},
  "apply_recommendation": "<one sentence recommendation>",
  "confidence": "<high|medium|low>"
}}

Tier thresholds: 90+ = Exceptional, 75-89 = Strong Match, 60-74 = Viable, <60 = Stretch.
Overall = sum of (score * weight) across all four categories, rounded to nearest integer.
"""


def _tier(overall: int) -> str:
    if overall >= 90:
        return "Exceptional"
    if overall >= 75:
        return "Strong Match"
    if overall >= 60:
        return "Viable"
    return "Stretch"


def fit_scorer_node(state: AppState) -> dict:
    if state.get("error") or not state.get("gap_analysis"):
        return {}

    try:
        user_msg = USER_TEMPLATE.format(
            job_description=state["job_description"],
            original_resume=state["original_resume"],
            gap_analysis=state["gap_analysis"],
        )
        raw = call_claude(SYSTEM, user_msg, max_tokens=400)

        try:
            parsed = extract_json(raw)
            overall = int(parsed.get("overall", 0))
            fit_score: FitScore = {
                "overall": overall,
                "tier": parsed.get("tier") or _tier(overall),
                "breakdown": parsed.get("breakdown", {}),
                "apply_recommendation": parsed.get("apply_recommendation", ""),
                "confidence": parsed.get("confidence", "medium"),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"[fit_scorer] JSON parse error: {e}", file=sys.stderr)
            return {"fit_score": None, "current_step": "fit_scored"}

        return {"fit_score": fit_score, "current_step": "fit_scored"}

    except Exception as e:
        print(f"[fit_scorer] error: {e}", file=sys.stderr)
        return {"fit_score": None, "current_step": "fit_scored"}
