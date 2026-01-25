"""Tests for the Google Gemini provider."""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.gemini import GeminiProvider
from providers.base import ModelConfig


# Environment variable for integration tests
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")


class TestGeminiProvider:
    """Test suite for GeminiProvider."""

    def test_provider_instantiation(self):
        """Provider should instantiate without errors."""
        provider = GeminiProvider()
        assert provider is not None

    def test_api_key_required(self):
        """Should raise ValueError if no API key provided."""
        provider = GeminiProvider()
        config = ModelConfig(
            model_name="gemini-2.0-flash",
            provider_type="gemini",
            model_id="gemini-2.0-flash",
            api_base="",
            api_key="",  # Empty API key
        )

        with pytest.raises(ValueError, match="API key is required"):
            provider.get_llm(config)

    def test_api_key_error_mentions_env_var(self):
        """Error message should mention GOOGLE_API_KEY environment variable."""
        provider = GeminiProvider()
        config = ModelConfig(
            model_name="gemini-2.0-flash",
            provider_type="gemini",
            model_id="gemini-2.0-flash",
            api_base="",
            api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            provider.get_llm(config)

        assert "GOOGLE_API_KEY" in str(exc_info.value)

    @patch("providers.gemini.ChatGoogleGenerativeAI")
    def test_get_llm_returns_chat_google_generative_ai(self, mock_chat_google):
        """Should return a ChatGoogleGenerativeAI instance when configured properly."""
        mock_instance = MagicMock()
        mock_chat_google.return_value = mock_instance

        provider = GeminiProvider()
        config = ModelConfig(
            model_name="gemini-2.0-flash",
            provider_type="gemini",
            model_id="gemini-2.0-flash",
            api_base="",
            api_key="test-api-key-12345",
        )

        result = provider.get_llm(config)

        assert result == mock_instance
        mock_chat_google.assert_called_once_with(
            model="gemini-2.0-flash",
            google_api_key="test-api-key-12345",
        )

    @patch("providers.gemini.ChatGoogleGenerativeAI")
    def test_get_llm_ignores_instance_parameter(self, mock_chat_google):
        """Instance parameter should be ignored (Google handles concurrency)."""
        mock_instance = MagicMock()
        mock_chat_google.return_value = mock_instance

        provider = GeminiProvider()
        config = ModelConfig(
            model_name="gemini-2.0-flash",
            provider_type="gemini",
            model_id="gemini-2.0-flash",
            api_base="",
            api_key="test-api-key-12345",
        )

        # Call with instance parameter
        result1 = provider.get_llm(config, instance=None)
        result2 = provider.get_llm(config, instance=0)
        result3 = provider.get_llm(config, instance=5)

        # All should work the same way
        assert result1 == mock_instance
        assert result2 == mock_instance
        assert result3 == mock_instance

    @patch("providers.gemini.ChatGoogleGenerativeAI")
    def test_different_models(self, mock_chat_google):
        """Should correctly pass different model IDs."""
        mock_chat_google.return_value = MagicMock()
        provider = GeminiProvider()

        models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
        ]

        for model_id in models:
            config = ModelConfig(
                model_name="test-model",
                provider_type="gemini",
                model_id=model_id,
                api_base="",
                api_key="test-api-key",
            )
            provider.get_llm(config)

            # Verify the model was passed correctly
            call_args = mock_chat_google.call_args
            assert call_args.kwargs["model"] == model_id


class TestGeminiProviderFactory:
    """Test that GeminiProvider is correctly registered in the factory."""

    def test_provider_in_factory(self):
        """Gemini provider should be available via get_providers."""
        from providers.factory import get_providers

        providers = get_providers()
        assert "gemini" in providers
        assert isinstance(providers["gemini"], GeminiProvider)


@pytest.mark.skipif(
    not GOOGLE_API_KEY,
    reason="GOOGLE_API_KEY environment variable not set"
)
class TestGeminiIntegration:
    """Integration tests requiring a real Google API key.
    
    These tests are skipped by default. To run them:
        GOOGLE_API_KEY=AI... uv run pytest tests/providers/test_gemini.py -v
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the API."""
        provider = GeminiProvider()
        config = ModelConfig(
            model_name="gemini-2.0-flash",
            provider_type="gemini",
            model_id="gemini-2.0-flash",  # Fast and efficient model
            api_base="",
            api_key=GOOGLE_API_KEY,
        )
        
        llm = provider.get_llm(config)
        messages = [HumanMessage(content="Say 'hello' and nothing else.")]
        
        chunks = []
        async for chunk in llm.astream(messages):
            if chunk.content:
                chunks.append(chunk.content)
        
        # Verify we got streaming chunks
        assert len(chunks) > 0, "Expected at least one streaming chunk"
        full_response = "".join(chunks)
        assert "hello" in full_response.lower(), f"Expected 'hello' in response: {full_response}"
