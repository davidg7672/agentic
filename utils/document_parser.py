import io
import re
import fitz  # PyMuPDF — installed as pymupdf, imported as fitz
import requests
from bs4 import BeautifulSoup
from docx import Document

MAX_FILE_BYTES = 5 * 1_048_576  # 5 MB

# Realistic browser UA to avoid trivial bot blocks
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Ordered list of CSS selectors to try for known job boards
_JOB_SELECTORS = [
    # Indeed
    "#jobDescriptionText",
    "[data-testid='jobsearch-JobComponent-description']",
    # LinkedIn (rarely succeeds without auth)
    ".description__text",
    ".show-more-less-html__markup",
    # Glassdoor
    "[data-test='job-description']",
    ".jobDescriptionContent",
    # Greenhouse
    "#content",
    ".job__description",
    # Lever
    ".posting-description",
    # Workday
    ".wd-text",
    # Generic fallbacks
    "article",
    "main",
    "[role='main']",
]

# Tags whose content should always be stripped
_STRIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form", "button"}


def parse_url(url: str) -> str:
    """
    Fetch a job posting URL and return its plain-text job description.
    Raises ValueError with a user-friendly message on failure.
    """
    if "linkedin.com" in url:
        raise ValueError(
            "LinkedIn requires you to be logged in — scraping is blocked. "
            "Please copy and paste the job description text instead."
        )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise ValueError("The page took too long to respond. Try again or paste the text manually.")
    except requests.exceptions.TooManyRedirects:
        raise ValueError("Too many redirects — the URL may be invalid or the site is misconfigured.")
    except requests.exceptions.SSLError:
        raise ValueError("SSL/TLS error — could not establish a secure connection to this URL.")
    except requests.exceptions.ConnectionError:
        raise ValueError(
            "Could not connect to the URL — the site may be blocking automated access. "
            "Please copy and paste the job description text instead."
        )
    except requests.exceptions.HTTPError as e:
        if e.response is None:
            raise ValueError(
                "The connection was interrupted before a response was received. "
                "The site may be blocking automated access — please paste the text manually."
            )
        status = e.response.status_code
        if status == 403:
            raise ValueError(
                "Access denied (403) — this site blocks automated access. "
                "Please copy and paste the job description text instead."
            )
        if status == 429:
            raise ValueError("Rate limited (429) — too many requests. Wait a moment and try again, or paste the text manually.")
        raise ValueError(f"Failed to fetch the URL (HTTP {status}).")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Could not reach the URL: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise tags in-place
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Try known job board selectors first
    for selector in _JOB_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator="\n")
            cleaned = _clean(text)
            if len(cleaned) > 200:
                return cleaned

    # Last resort: full page body text
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n")
        cleaned = _clean(text)
        if len(cleaned) > 200:
            return cleaned

    raise ValueError(
        "Could not extract job description text from this page. "
        "Please copy and paste the text manually."
    )


def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def parse_uploaded_file(uploaded_file) -> str:
    """
    Accept a Streamlit UploadedFile and return plain text.
    Supports .pdf, .docx, and plain text files.
    """
    if uploaded_file.size > MAX_FILE_BYTES:
        raise ValueError(
            f"File '{uploaded_file.name}' exceeds the 5 MB limit "
            f"({uploaded_file.size / 1_048_576:.1f} MB). Please upload a smaller file."
        )

    name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if name.endswith(".pdf"):
        return _parse_pdf(raw_bytes)
    elif name.endswith(".docx"):
        return _parse_docx(raw_bytes)
    else:
        return _decode_text(raw_bytes)


def parse_text(text: str) -> str:
    return text.strip()


def _parse_pdf(raw_bytes: bytes) -> str:
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages).strip()


def _parse_docx(raw_bytes: bytes) -> str:
    doc = Document(io.BytesIO(raw_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def _decode_text(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1").strip()
