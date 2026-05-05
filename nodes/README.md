# nodes/

The four main agent steps. Each is a LangGraph node function: takes `AppState`, returns a `dict` of only the keys it writes.

## Execution order

```
gap_analyzer → resume_rewriter → [guardrails] → cover_letter → interview_predictor
```

## Files

### `gap_analyzer.py`
Reads `job_description` + `original_resume`. Identifies missing required skills, experience level gaps, missing nice-to-haves, and strengths. Writes `gap_analysis` (structured markdown).

### `resume_rewriter.py`
Reads `job_description` + `original_resume` + `gap_analysis`. Rewrites resume bullets to align with JD language. System prompt has a strict no-fabrication rule — the guardrail in `guardrails/fabrication_detector.py` is the independent second check. Writes `rewritten_resume`.

### `cover_letter.py`
Reads `job_description` + `rewritten_resume` + `gap_analysis`. Writes a 3-paragraph cover letter (under 350 words): hook → evidence → close. Writes `cover_letter`.

### `interview_predictor.py`
Reads `job_description` + `gap_analysis` + `rewritten_resume`. Generates 10 questions in 4 categories: technical, behavioral (STAR), gap-probing, situational. Each includes a rationale. Writes `interview_questions`.

## Conventions

- Every node checks `if state.get("error"): return {}` at the top — a failed upstream node doesn't cascade
- Return only the keys the node modifies, not the full state
- LLM calls go through `utils/llm_client.call_claude()`
- `current_step` is updated by each node so the Streamlit UI can track progress
