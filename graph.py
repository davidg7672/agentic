from langgraph.graph import StateGraph, START, END

from state import AppState
from nodes.gap_analyzer import gap_analyzer_node
from nodes.fit_scorer import fit_scorer_node
from nodes.resume_rewriter import resume_rewriter_node
from nodes.latex_generator import latex_generator_node
from nodes.cover_letter import cover_letter_node
from nodes.interview_predictor import interview_predictor_node
from guardrails.fabrication_detector import fabrication_detector_node
from guardrails.tone_enforcer import tone_enforcer_node
from guardrails.ats_checker import ats_checker_node


def build_graph():
    builder = StateGraph(AppState)

    # Main agent nodes
    builder.add_node("gap_analyzer", gap_analyzer_node)
    builder.add_node("fit_scorer", fit_scorer_node)
    builder.add_node("resume_rewriter", resume_rewriter_node)
    builder.add_node("cover_letter_drafter", cover_letter_node)
    builder.add_node("interview_predictor", interview_predictor_node)
    builder.add_node("latex_generator", latex_generator_node)

    # Guardrail nodes (warn-and-continue — all edges unconditional)
    builder.add_node("fabrication_detector", fabrication_detector_node)
    builder.add_node("tone_enforcer", tone_enforcer_node)
    builder.add_node("ats_checker", ats_checker_node)

    # Pipeline:
    # gap → rewrite → [fabrication → tone → ats] → latex → cover letter → interview
    builder.add_edge(START, "gap_analyzer")
    builder.add_edge("gap_analyzer", "fit_scorer")
    builder.add_edge("fit_scorer", "resume_rewriter")
    builder.add_edge("resume_rewriter", "fabrication_detector")
    builder.add_edge("fabrication_detector", "tone_enforcer")
    builder.add_edge("tone_enforcer", "ats_checker")
    builder.add_edge("ats_checker", "latex_generator")
    builder.add_edge("latex_generator", "cover_letter_drafter")
    builder.add_edge("cover_letter_drafter", "interview_predictor")
    builder.add_edge("interview_predictor", END)

    return builder.compile()
