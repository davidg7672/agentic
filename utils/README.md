# utils/

Shared utilities used across nodes and guardrails.

## Files

### `llm_client.py`
Anthropic client singleton and a thin `call_claude()` wrapper.

```python
from utils.llm_client import call_claude

text = call_claude(system="...", user="...", max_tokens=1024)
```

The client is initialized once on first call and reused for all subsequent calls. Model is hardcoded to `claude-sonnet-4-6`. All nodes and guardrails go through this — no direct `Anthropic()` instantiation elsewhere.

### `document_parser.py`
Handles all input formats for job descriptions and resumes.

| Function | Input | Use case |
|---|---|---|
| `parse_url(url)` | URL string | Fetch a job posting from the web |
| `parse_uploaded_file(file)` | Streamlit `UploadedFile` | PDF, DOCX, or plain text upload |
| `parse_text(text)` | Plain string | Text pasted directly into the UI |

**URL fetching (`parse_url`):**
- Sends a browser-like User-Agent to pass basic bot checks
- Tries 13 CSS selectors for known job boards (Indeed, Glassdoor, Greenhouse, Lever, Workday) before falling back to `<article>` / `<main>` / full body
- LinkedIn raises a clear `ValueError` immediately — their auth wall blocks all scraping
- HTTP 403, timeouts, and unextractable pages all raise `ValueError` with user-friendly messages
- JS-rendered pages (some Workday, iCIMS) won't work — content requires a real browser

**PDF parsing:** PyMuPDF (`import fitz`) — fast C-backed extraction. Note: installs as `pymupdf` but imports as `fitz`.

**DOCX parsing:** `python-docx` — extracts paragraph text, skips empty paragraphs.

### `pdf_exporter.py`
Compiles LaTeX source to PDF bytes using `tectonic`.

| Function | Input | Output |
|---|---|---|
| `resume_to_pdf(latex_source)` | Complete LaTeX string | PDF bytes |
| `cover_letter_to_pdf(letter_text)` | Plain/markdown text | PDF bytes |

`resume_to_pdf` writes the LaTeX to a temp file, invokes tectonic, and reads back the compiled PDF. Raises `RuntimeError` on compilation failure.

`cover_letter_to_pdf` wraps the letter text in a minimal LaTeX document (1in margins, 10.5pt) and compiles it. Markdown bold/italic markers are stripped before escaping so `**text**` renders as plain text rather than literal asterisks.

Requires `tectonic` on `$PATH` — install with `brew install tectonic` on macOS.

### `docx_exporter.py`
Generates `.docx` files from resume and cover letter text.

| Function | Input | Output |
|---|---|---|
| `resume_to_docx(resume_text)` | Markdown-formatted resume string | DOCX bytes |
| `cover_letter_to_docx(letter_text)` | Plain/markdown text | DOCX bytes |

`resume_to_docx` parses markdown conventions used by the resume rewriter:
- `# Name` → centered 18pt bold name
- `## SECTION` → bold section header with bottom rule
- `- bullet` → indented list item
- `**Company** | Location` style lines → two-column entry with right-aligned tab

`cover_letter_to_docx` splits on double newlines and renders each block as a paragraph with 12pt spacing, parsing inline `**bold**` and `*italic*` markdown.
