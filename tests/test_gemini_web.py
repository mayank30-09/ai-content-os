"""Unit test suite for Gemini Web Provider (Milestone 2 Hardening).

Tests successful response, timeout recovery, exponential retry, popup dismissal,
session expired handling, and response validation rules.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.ai.gemini_web import (
    GeminiWebProvider,
    GenerationTimeoutException,
    ResponseValidationException,
    SessionExpiredException,
)


@pytest.fixture
def provider():
    return GeminiWebProvider()

def test_validate_response_success(provider):
    """Verifies that valid, non-empty text passes response validation."""
    valid_text = "Here is a complete, structured social media post breakdown for your campaign."
    assert provider.validate_response(valid_text) is True

def test_validate_response_empty(provider):
    """Verifies that empty or whitespace-only response raises ResponseValidationException."""
    with pytest.raises(ResponseValidationException, match="completely empty"):
        provider.validate_response("")

    with pytest.raises(ResponseValidationException, match="completely empty"):
        provider.validate_response("   \n\t ")

def test_validate_response_too_short(provider):
    """Verifies that responses shorter than minimum threshold raise ResponseValidationException."""
    with pytest.raises(ResponseValidationException, match="below minimum threshold"):
        provider.validate_response("Short text")

def test_validate_response_error_indicator(provider):
    """Verifies that responses containing error indicators raise ResponseValidationException."""
    with pytest.raises(ResponseValidationException, match="error message indicator"):
        provider.validate_response("Something went wrong on the server. Please try again later.")

@pytest.mark.asyncio
async def test_dismiss_popups(provider):
    """Verifies that visible popup dismiss buttons are detected and clicked."""
    mock_page = MagicMock()
    mock_button = AsyncMock()
    mock_button.count.return_value = 1
    mock_button.is_visible.return_value = True

    mock_locator = MagicMock()
    mock_locator.first = mock_button
    mock_page.locator.return_value = mock_locator

    dismissed = await provider.dismiss_popups(mock_page)
    assert dismissed > 0
    assert mock_button.click.called

@pytest.mark.asyncio
async def test_session_expired_handling(provider):
    """Verifies that SessionExpiredException is raised when prompt textarea is missing."""
    mock_page = AsyncMock()

    with (
        patch("modules.ai.gemini_web.browser_pool.new_page", return_value=mock_page),
        patch("modules.ai.gemini_web.selector_registry.find_element", side_effect=RuntimeError("Element not found")),
        pytest.raises(SessionExpiredException)
    ):
        await provider.generate("Test prompt")

@pytest.mark.asyncio
async def test_retry_on_timeout_recovery(provider):
    """Verifies that transient timeout failure triggers exponential retry and succeeds on subsequent attempt."""
    mock_page = AsyncMock()

    with (
        patch("modules.ai.gemini_web.browser_pool.new_page", return_value=mock_page),
        patch.object(
            provider,
            "_attempt_single_generation",
            side_effect=[
                GenerationTimeoutException("Timed out"),
                "Here is a valid, complete generated output response that exceeds the minimum required length."
            ]
        ),
        patch("asyncio.sleep", new_callable=AsyncMock)
    ):
        result = await provider.generate("Test prompt")
        assert "valid, complete generated output" in result

@pytest.mark.asyncio
async def test_all_retries_exhausted(provider):
    """Verifies that exception is raised after exhausting all MAX_RETRIES."""
    mock_page = AsyncMock()

    with (
        patch("modules.ai.gemini_web.browser_pool.new_page", return_value=mock_page),
        patch.object(
            provider,
            "_attempt_single_generation",
            side_effect=GenerationTimeoutException("Timed out")
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(GenerationTimeoutException)
    ):
        await provider.generate("Test prompt")
