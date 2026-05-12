from typing import TypedDict, Optional, List


class GuardrailResult(TypedDict):
    passed: bool
    issues: List[str]
    severity: str  # "warning" | "error"


class FitScore(TypedDict):
    overall: int
    tier: str
    breakdown: dict
    apply_recommendation: str
    confidence: str  # "high" | "medium" | "low"


class AppState(TypedDict):
    # Inputs
    job_description: str
    original_resume: str

    # Node 1 output
    gap_analysis: str

    # Node 1b output
    fit_score: Optional[FitScore]

    # Node 2 output
    rewritten_resume: str

    # Node 2b output (LaTeX source for PDF export)
    latex_source: str

    # Guardrail outputs (run after Node 2)
    fabrication_result: Optional[GuardrailResult]
    tone_result: Optional[GuardrailResult]
    ats_result: Optional[GuardrailResult]

    # Node 3 output
    cover_letter: str

    # Node 4 output
    interview_questions: str

    # Control flow
    guardrail_warnings: List[str]
    current_step: str
    error: Optional[str]


def initial_state(job_description: str, original_resume: str) -> AppState:
    return AppState(
        job_description=job_description,
        original_resume=original_resume,
        gap_analysis="",
        fit_score=None,
        rewritten_resume="",
        latex_source="",
        fabrication_result=None,
        tone_result=None,
        ats_result=None,
        cover_letter="",
        interview_questions="",
        guardrail_warnings=[],
        current_step="start",
        error=None,
    )
