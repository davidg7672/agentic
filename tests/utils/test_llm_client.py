import os
import pytest
from unittest.mock import MagicMock, patch
import utils.llm_client as llm_module
from utils.llm_client import call_claude, get_client, MODEL


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the module-level singleton between tests."""
    original = llm_module._client
    llm_module._client = None
    yield
    llm_module._client = original


def test_get_client_raises_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            get_client()


def test_get_client_returns_client_with_api_key():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("utils.llm_client.Anthropic") as mock_anthropic:
            mock_instance = MagicMock()
            mock_anthropic.return_value = mock_instance
            client = get_client()
            assert client is mock_instance
            mock_anthropic.assert_called_once_with(api_key="test-key", timeout=60.0)


def test_get_client_is_singleton():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("utils.llm_client.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            c1 = get_client()
            c2 = get_client()
            assert c1 is c2
            mock_anthropic.assert_called_once()


def test_call_claude_returns_text():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Generated text response")]
    mock_client.messages.create.return_value = mock_response

    with patch("utils.llm_client.get_client", return_value=mock_client):
        result = call_claude("system prompt", "user prompt", max_tokens=512)

    assert result == "Generated text response"


def test_call_claude_uses_correct_model_and_params():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]
    mock_client.messages.create.return_value = mock_response

    with patch("utils.llm_client.get_client", return_value=mock_client):
        call_claude("sys", "usr", max_tokens=999)

    mock_client.messages.create.assert_called_once_with(
        model=MODEL,
        max_tokens=999,
        system="sys",
        messages=[{"role": "user", "content": "usr"}],
    )
