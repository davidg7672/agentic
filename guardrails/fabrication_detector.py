import json
import sys
from state import AppState, GuardrailResult
from utils.llm_client import call_claude

SYSTEM = """You are a strict fact-checker comparing a rewritten resume against the original source resume.
Your job is to identify fabrications: skills, tools, certifications, job titles, companies, dates,
metrics, or achievements that appear in the rewritten resume but have NO basis in the original.

Be conservative — only flag clear additions, not reasonable rewordings of existing content.
Respond ONLY with valid JSON. No preamble, no explanation outside the JSON."""

USER_TEMPLATE = """Compare these two resumes and identify fabrications.

<original_resume>
{original_resume}
</original_resume>

<rewritten_resume>
{rewritten_resume}
</rewritten_resume>

Respond with this exact JSON structure:
{{
  "verdict": "clean",
  "fabrications": []
}}

OR if fabrications are found:
{{
  "verdict": "flagged",
  "fabrications": [
    "Specific item added that was not in original",
    "Another fabricated item"
  ]
}}
"""


def fabrication_detector_node(state: AppState) -> dict:
    warnings = list(state.get("guardrail_warnings", []))

    if state.get("error") or not state.get("rewritten_resume"):
        return {}

    try:
        user_msg = USER_TEMPLATE.format(
            original_resume=state["original_resume"],
            rewritten_resume=state["rewritten_resume"],
        )
        raw = call_claude(SYSTEM, user_msg, max_tokens=500)

        try:
            parsed = json.loads(raw)
            fabrications = parsed.get("fabrications", [])
            verdict = parsed.get("verdict", "clean")
        except json.JSONDecodeError as json_err:
            print(f"[fabrication_detector] JSON parse error: {json_err}", file=sys.stderr)
            warnings.append("[Fabrication Check] Could not parse guardrail response — treat output with caution.")
            result: GuardrailResult = {
                "passed": False,
                "issues": ["Guardrail response was unparseable — treat output with caution."],
                "severity": "warning",
            }
            return {"fabrication_result": result, "guardrail_warnings": warnings}

        passed = verdict == "clean"
        result: GuardrailResult = {
            "passed": passed,
            "issues": fabrications,
            "severity": "warning",
        }

        if not passed:
            for item in fabrications:
                warnings.append(f"[Fabrication] {item}")

        return {"fabrication_result": result, "guardrail_warnings": warnings}

    except Exception as e:
        print(f"[fabrication_detector] error: {e}", file=sys.stderr)
        warnings.append("[Fabrication Check] Could not complete — treat output with caution.")
        result: GuardrailResult = {
            "passed": False,
            "issues": ["Guardrail check failed — treat output with caution."],
            "severity": "warning",
        }
        return {"fabrication_result": result, "guardrail_warnings": warnings}
