# Job Application Copilot — Claude Code Context

## What this project is

A LangGraph agentic pipeline that takes a job description + resume and produces a tailored resume, cover letter, and interview prep. Built with LangGraph 1.1, Anthropic Claude Sonnet 4.6, and Streamlit.

Run it: `streamlit run app.py`

## Project layout

```
app.py          # Streamlit UI — calls build_graph() and streams results
graph.py        # LangGraph StateGraph — all nodes and edges wired here
state.py        # AppState TypedDict — single shared state object for all nodes

nodes/          # 6 main pipeline steps (gap_analyzer, fit_scorer, resume_rewriter,
                #   latex_generator, cover_letter, interview_predictor)
guardrails/     # 3 validation nodes (fabrication_detector, tone_enforcer, ats_checker)
utils/          # llm_client, document_parser, pdf_exporter, docx_exporter, etc.
tests/          # pytest — mirrors the source tree structure
```

## Pipeline order (from graph.py)

```
START → gap_analyzer → fit_scorer → resume_rewriter
      → fabrication_detector → tone_enforcer → ats_checker
      → latex_generator → cover_letter_drafter → interview_predictor → END
```

Guardrails always run after `resume_rewriter` and are unconditional — they never block, only append to `guardrail_warnings` in state.

## Key design decisions

- **No FastAPI backend** — Streamlit calls `graph.stream()` synchronously with `stream_mode="values"`. Each section renders as its node completes.
- **Direct Anthropic SDK** — `utils/llm_client.py` wraps `anthropic.Anthropic` directly. No LangChain LLM wrappers. One function: `call_claude(system, user, max_tokens)`.
- **LLM model** — `claude-sonnet-4-6` set as constant in `utils/llm_client.py`.
- **Guardrails are graph nodes**, not inline validators. They run as separate nodes and write results to `state.fabrication_result`, `state.tone_result`, `state.ats_result`.
- **ATS checker uses BM25** (`rank-bm25`), not an LLM — zero extra API calls.
- **Fabrication guardrail is layered** — the resume rewriter system prompt already prohibits invention; the guardrail is an independent second check using LLM-as-judge.
- **LaTeX for PDF** — `latex_generator` node produces LaTeX source; `tectonic` compiles it to PDF. DOCX export also reads from the LaTeX source.

## State shape (state.py)

`AppState` is a `TypedDict`. Every node receives the full state and returns only the keys it updates. Key fields:

- `job_description`, `original_resume` — inputs
- `gap_analysis`, `fit_score`, `rewritten_resume`, `latex_source`, `cover_letter`, `interview_questions` — node outputs
- `fabrication_result`, `tone_result`, `ats_result` — `GuardrailResult` TypedDicts
- `guardrail_warnings` — `List[str]` accumulated across all guardrail nodes
- `current_step` — string updated by each node, used by app.py for progress bar
- `error` — set by any node on failure; all subsequent nodes skip if this is set

## Adding a new node

1. Create `nodes/your_node.py` — define `SYSTEM`, `USER_TEMPLATE`, and a `your_node_node(state: AppState) -> dict` function.
2. Add the node and edge to `graph.py` via `builder.add_node` and `builder.add_edge`.
3. Add any new output fields to `AppState` in `state.py` and initialize them in `initial_state()`.

## Environment

Requires `ANTHROPIC_API_KEY` in `.env` (copy from `.env.example`).
PDF export requires `tectonic` installed (`brew install tectonic` on macOS).

## Tests

```bash
pytest
```

Tests live in `tests/` mirroring the source layout. Use `conftest.py` fixtures for shared setup.

## Stack versions

- `langgraph==1.1.10`
- `streamlit==1.45.0`
- `anthropic>=0.40.0`
- `rank-bm25==0.2.2` (ATS checker)
- `pymupdf==1.25.5`, `python-docx==1.1.2` (doc parsing/export)
