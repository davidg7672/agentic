# nodes/

The five main agent steps. Each is a LangGraph node function: takes `AppState`, returns a `dict` of only the keys it writes.

## Execution order

```
gap_analyzer → resume_rewriter → [guardrails] → latex_generator → cover_letter_drafter → interview_predictor
```

## Files

### `gap_analyzer.py`
Reads `job_description` + `original_resume`. Identifies missing required skills, experience level gaps, missing nice-to-haves, and strengths. Writes `gap_analysis` (structured markdown).

### `resume_rewriter.py`
Reads `job_description` + `original_resume` + `gap_analysis`. Rewrites resume bullets to align with JD language. System prompt has a strict no-fabrication rule — the guardrail in `guardrails/fabrication_detector.py` is the independent second check. Writes `rewritten_resume`.

### `latex_generator.py`
Reads `rewritten_resume`. Converts the markdown resume to a complete LaTeX document that compiles to a clean single-page PDF via tectonic. Uses a fixed preamble with custom `\skillrow{Label:}{skills}` macros that guarantee single-line skill rows. A Python post-processing step truncates any skill row that would overflow the page margin (removes trailing skills until the row fits within ~78 characters). Writes `latex_source`.

### `cover_letter.py`
Reads `job_description` + `rewritten_resume` + `gap_analysis`. Produces a fully formatted professional business letter:
- Header with candidate name and contact info (extracted from the resume)
- Current date
- "Dear Hiring Manager," salutation
- 3 body paragraphs: hook → evidence → close (under 350 words)
- "Sincerely," closing with candidate name

Never starts with "I am writing to apply…" or uses filler phrases. Writes `cover_letter`.

### `interview_predictor.py`
Reads `job_description` + `gap_analysis` + `rewritten_resume`. Generates 10 questions in 4 categories: technical, behavioral (STAR), gap-probing, situational. Each includes a rationale. Writes `interview_questions`.

## Conventions

- Every node checks `if state.get("error"): return {}` at the top — a failed upstream node doesn't cascade
- Return only the keys the node modifies, not the full state
- LLM calls go through `utils/llm_client.call_claude()`
- `current_step` is updated by each node so the Streamlit UI can track progress
