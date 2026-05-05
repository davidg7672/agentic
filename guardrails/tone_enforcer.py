import sys
from state import AppState, GuardrailResult
from utils.llm_client import call_claude

SYSTEM = """You are a professional writing coach reviewing a resume for tone and professionalism.
Flag any of the following issues:
- Casual language or slang
- First-person pronouns (I, me, my, we, our)
- Passive complaints or negative framing
- Unsupported subjective claims (e.g., "passionate about", "hardworking", "team player", "detail-oriented")
  unless backed by a concrete example in the same bullet

Only flag genuine problems. A strong resume with confident, professional language should PASS."""

USER_TEMPLATE = """Review this resume for tone and professionalism issues.

<resume>
{rewritten_resume}
</resume>

Respond using EXACTLY this format:

VERDICT: PASS

OR:

VERDICT: FAIL
ISSUES:
- [specific issue found, with example text]
- [another issue]
"""


def tone_enforcer_node(state: AppState) -> dict:
    warnings = list(state.get("guardrail_warnings", []))

    if state.get("error") or not state.get("rewritten_resume"):
        return {}

    try:
        user_msg = USER_TEMPLATE.format(rewritten_resume=state["rewritten_resume"])
        raw = call_claude(SYSTEM, user_msg, max_tokens=400)

        passed = "VERDICT: PASS" in raw

        issues = []
        if not passed:
            lines = raw.splitlines()
            in_issues = False
            for line in lines:
                if line.strip() == "ISSUES:":
                    in_issues = True
                    continue
                if in_issues and line.strip().startswith("- "):
                    issues.append(line.strip()[2:])

        result: GuardrailResult = {
            "passed": passed,
            "issues": issues,
            "severity": "warning",
        }

        if not passed:
            for item in issues:
                warnings.append(f"[Tone] {item}")

        return {"tone_result": result, "guardrail_warnings": warnings}

    except Exception as e:
        print(f"[tone_enforcer] error: {e}", file=sys.stderr)
        warnings.append("[Tone Check] Could not complete — treat output with caution.")
        result: GuardrailResult = {
            "passed": False,
            "issues": ["Guardrail check failed — treat output with caution."],
            "severity": "warning",
        }
        return {"tone_result": result, "guardrail_warnings": warnings}
