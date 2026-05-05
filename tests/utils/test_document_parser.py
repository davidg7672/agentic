import io
import pytest
from unittest.mock import MagicMock, patch
from utils.document_parser import (
    parse_text,
    parse_url,
    parse_uploaded_file,
    _clean,
    _parse_pdf,
    _parse_docx,
    _decode_text,
    MAX_FILE_BYTES,
)


# ---------------------------------------------------------------------------
# _clean
# ---------------------------------------------------------------------------

def test_clean_collapses_blank_lines():
    text = "line1\n\n\n\nline2"
    assert _clean(text) == "line1\n\nline2"


def test_clean_collapses_spaces():
    text = "word1   word2"
    assert _clean(text) == "word1 word2"


def test_clean_strips_edges():
    assert _clean("  hello  ") == "hello"


# ---------------------------------------------------------------------------
# parse_text
# ---------------------------------------------------------------------------

def test_parse_text_strips_whitespace():
    assert parse_text("  hello world  ") == "hello world"


def test_parse_text_empty_string():
    assert parse_text("") == ""


# ---------------------------------------------------------------------------
# _decode_text
# ---------------------------------------------------------------------------

def test_decode_text_utf8():
    raw = "Hello UTF-8 résumé".encode("utf-8")
    assert "résumé" in _decode_text(raw)


def test_decode_text_latin1_fallback():
    raw = "caf\xe9".encode("latin-1")
    result = _decode_text(raw)
    assert "caf" in result


# ---------------------------------------------------------------------------
# _parse_pdf
# ---------------------------------------------------------------------------

def test_parse_pdf_returns_text():
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Page one text\n"
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.close = MagicMock()

    with patch("utils.document_parser.fitz.open", return_value=mock_doc):
        result = _parse_pdf(b"fake-pdf-bytes")

    assert result == "Page one text"


def test_parse_pdf_multipage():
    pages = [MagicMock(), MagicMock()]
    pages[0].get_text.return_value = "Page 1\n"
    pages[1].get_text.return_value = "Page 2\n"
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter(pages))
    mock_doc.close = MagicMock()

    with patch("utils.document_parser.fitz.open", return_value=mock_doc):
        result = _parse_pdf(b"fake")

    assert "Page 1" in result and "Page 2" in result


# ---------------------------------------------------------------------------
# _parse_docx
# ---------------------------------------------------------------------------

def test_parse_docx_returns_paragraphs():
    mock_p1 = MagicMock()
    mock_p1.text = "First paragraph"
    mock_p2 = MagicMock()
    mock_p2.text = ""  # empty — should be skipped
    mock_p3 = MagicMock()
    mock_p3.text = "Third paragraph"

    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_p1, mock_p2, mock_p3]

    with patch("utils.document_parser.Document", return_value=mock_doc):
        result = _parse_docx(b"fake-docx")

    assert result == "First paragraph\nThird paragraph"


# ---------------------------------------------------------------------------
# parse_url
# ---------------------------------------------------------------------------

def test_parse_url_raises_for_linkedin():
    with pytest.raises(ValueError, match="LinkedIn"):
        parse_url("https://www.linkedin.com/jobs/view/12345")


def test_parse_url_raises_on_timeout():
    import requests
    with patch("utils.document_parser.requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(ValueError, match="too long"):
            parse_url("https://example.com/job")


def test_parse_url_raises_on_403():
    import requests
    mock_response = MagicMock()
    mock_response.status_code = 403
    err = requests.exceptions.HTTPError(response=mock_response)
    with patch("utils.document_parser.requests.get", side_effect=err):
        with pytest.raises(ValueError, match="Access denied"):
            parse_url("https://example.com/job")


def test_parse_url_raises_on_generic_http_error():
    import requests
    mock_response = MagicMock()
    mock_response.status_code = 500
    err = requests.exceptions.HTTPError(response=mock_response)
    with patch("utils.document_parser.requests.get", side_effect=err):
        with pytest.raises(ValueError, match="HTTP 500"):
            parse_url("https://example.com/job")


def test_parse_url_raises_on_connection_error():
    import requests
    with patch("utils.document_parser.requests.get",
               side_effect=requests.exceptions.ConnectionError("refused")):
        with pytest.raises(ValueError, match="Could not reach"):
            parse_url("https://example.com/job")


def test_parse_url_extracts_text_via_selector():
    html = """
    <html><body>
      <div id="jobDescriptionText">
        This is the job description with enough text to pass the 200 char threshold.
        We are looking for a Python developer with 5 years of experience in Django and FastAPI.
        Experience with PostgreSQL and Redis is required. Docker and Kubernetes are a plus.
      </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.document_parser.requests.get", return_value=mock_resp):
        result = parse_url("https://indeed.com/job/12345")
    assert "Python developer" in result


def test_parse_url_falls_back_to_body():
    html = """<html><body>
    """ + "This is a very long job description text. " * 10 + """
    </body></html>"""
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.document_parser.requests.get", return_value=mock_resp):
        result = parse_url("https://example.com/job")
    assert len(result) > 100


def test_parse_url_raises_when_no_content_extracted():
    html = "<html><body><p>Hi</p></body></html>"
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.document_parser.requests.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="Could not extract"):
            parse_url("https://example.com/job")


# ---------------------------------------------------------------------------
# parse_uploaded_file
# ---------------------------------------------------------------------------

def _make_uploaded_file(name: str, content: bytes) -> MagicMock:
    f = MagicMock()
    f.name = name
    f.size = len(content)
    f.read.return_value = content
    return f


def test_parse_uploaded_file_too_large_raises():
    f = _make_uploaded_file("resume.pdf", b"x")
    f.size = MAX_FILE_BYTES + 1
    with pytest.raises(ValueError, match="5 MB"):
        parse_uploaded_file(f)


def test_parse_uploaded_file_pdf():
    raw = b"fake-pdf"
    f = _make_uploaded_file("resume.pdf", raw)
    with patch("utils.document_parser._parse_pdf", return_value="PDF text") as mock_pdf:
        result = parse_uploaded_file(f)
    mock_pdf.assert_called_once_with(raw)
    assert result == "PDF text"


def test_parse_uploaded_file_docx():
    raw = b"fake-docx"
    f = _make_uploaded_file("resume.docx", raw)
    with patch("utils.document_parser._parse_docx", return_value="DOCX text") as mock_docx:
        result = parse_uploaded_file(f)
    mock_docx.assert_called_once_with(raw)
    assert result == "DOCX text"


def test_parse_uploaded_file_txt():
    raw = "Plain text resume".encode("utf-8")
    f = _make_uploaded_file("resume.txt", raw)
    result = parse_uploaded_file(f)
    assert result == "Plain text resume"
