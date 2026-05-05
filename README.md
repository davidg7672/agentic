# Job Application Copilot

An agentic AI app that turns a job description + resume into a full application package. Built with LangGraph, Claude Sonnet, and Streamlit.

## What it does

Paste/upload a job description (or drop a URL) and your resume. The agent runs sequentially:

1. **Gap Analyzer** — finds missing skills and experience mismatches
2. **Resume Rewriter** — tailors your resume bullets to the JD (no fabrication)
3. **Cover Letter Drafter** — writes a targeted 3-paragraph cover letter
4. **Interview Question Predictor** — predicts 10 likely questions with rationale

After the resume rewrite, three guardrails run automatically:
- **Fabrication Detector** — LLM-as-judge that flags any skills/credentials added that weren't in your original resume
- **Tone Enforcer** — flags casual language, first-person pronouns, unsupported claims
- **ATS Checker** — BM25 keyword match to surface JD terms missing from the rewritten resume

Guardrails are warn-and-continue — they never block output, just surface warnings inline.

## Stack

| Layer | Tech |
|---|---|
| Agent framework | LangGraph 1.1 (`StateGraph`) |
| LLM | Anthropic Claude Sonnet 4.6 (direct SDK, no LangChain wrappers) |
| UI | Streamlit (sync `.stream()` — no async/event loop conflicts) |
| ATS check | `rank-bm25` (zero LLM calls) |
| Doc parsing | PyMuPDF, python-docx, requests + BeautifulSoup |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

streamlit run app.py
```

## Project structure

```
app.py          # Streamlit UI entry point
graph.py        # LangGraph StateGraph — wires all nodes and edges
state.py        # AppState TypedDict — shared state flowing through all nodes

nodes/          # The 4 main agent steps
guardrails/     # The 3 validation nodes (run after resume rewrite)
utils/          # LLM client singleton and document parser
```

## Supported job description inputs

- **URL** — Indeed, Glassdoor, Greenhouse, Lever, most company career pages
- **File upload** — PDF, DOCX, TXT
- **Paste** — plain text

LinkedIn URLs are blocked by LinkedIn and won't work — paste the text instead.

## Key design decisions

- **No FastAPI backend** — Streamlit calls `graph.stream()` synchronously. Each section renders as its node completes.
- **Single LLM provider** — Anthropic only. One API key, no version drift between provider wrappers.
- **Guardrails as graph nodes** — not inline validators. They run unconditionally and write warnings to state; the pipeline always continues.
- **Fabrication guardrail is layered** — the resume rewriter prompt itself says "do not invent"; the guardrail is the second independent check.
