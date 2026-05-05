# guardrails/

Three validation nodes that run after the resume rewrite, before the cover letter. All are **warn-and-continue** — they never hard-stop the pipeline. Warnings accumulate in `state["guardrail_warnings"]` and are displayed inline in the UI.

## Execution order

```
resume_rewriter → fabrication_detector → tone_enforcer → ats_checker → cover_letter
```

## Files

### `fabrication_detector.py`
**Method:** LLM-as-judge (single Claude call).

Compares `original_resume` vs `rewritten_resume` side-by-side. Asks Claude to return JSON listing any skills, tools, certs, titles, metrics, or dates present in the rewrite but absent from the original.

JSON parse is wrapped in try/except — if the model returns malformed JSON, it **fails open** (treats as clean) so a parser error never blocks the user.

### `tone_enforcer.py`
**Method:** Single Claude call with structured text output.

Flags: casual language, first-person pronouns (I/me/my), passive complaints, unsupported subjective claims ("passionate about", "hardworking") without a concrete example in the same bullet.

Parses by checking if `"VERDICT: PASS"` appears in the response string.

### `ats_checker.py`
**Method:** BM25 keyword matching — **zero LLM calls**.

Tokenizes both the JD and the rewritten resume. Builds a `BM25Okapi` corpus from resume tokens, then scores each JD keyword. A score of 0 means the word is completely absent. Flags if missing keywords exceed 20% of the JD vocabulary. Uses a hardcoded stopword set (no `nltk` dependency).

## Conventions

- All three follow the same pattern: read `guardrail_warnings` from state, append issues, return updated list
- LangGraph replaces lists (does not merge) — always read then return the full updated list
- Each guardrail fails open on exceptions — a guardrail error should never surface as a blocking failure
