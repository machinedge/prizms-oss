"""Tests for the OpenRouter provider."""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.openrouter import OpenRouterProvider, OPENROUTER_API_BASE
from providers.base import ModelConfig


# Environment variable for integration tests
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")


class TestOpenRouterProvider:
    """Test suite for OpenRouterProvider."""

    def test_provider_instantiation(self):
        """Provider should instantiate without errors."""
        provider = OpenRouterProvider()
        assert provider is not None

    def test_api_key_required(self):
        """Should raise ValueError if no API key provided."""
        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="",  # Empty API key
        )

        with pytest.raises(ValueError, match="API key is required"):
            provider.get_llm(config)

    def test_api_key_error_mentions_env_var(self):
        """Error message should mention OPENROUTER_API_KEY environment variable."""
        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            provider.get_llm(config)

        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    @patch("providers.openrouter.ChatOpenAI")
    def test_get_llm_returns_chat_openai(self, mock_chat_openai):
        """Should return a ChatOpenAI instance when configured properly."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="sk-or-test-key-12345",
        )

        result = provider.get_llm(config)

        assert result == mock_instance
        mock_chat_openai.assert_called_once()
        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "anthropic/claude-3-opus"
        assert call_kwargs["api_key"] == "sk-or-test-key-12345"

    @patch("providers.openrouter.ChatOpenAI")
    def test_get_llm_uses_openrouter_base_url(self, mock_chat_openai):
        """Should use OpenRouter API base URL by default."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",  # Empty, should use default
            api_key="sk-or-test-key-12345",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["base_url"] == OPENROUTER_API_BASE

    @patch("providers.openrouter.ChatOpenAI")
    def test_get_llm_sets_custom_headers(self, mock_chat_openai):
        """Should set HTTP-Referer and X-Title headers for OpenRouter rankings."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="sk-or-test-key-12345",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert "default_headers" in call_kwargs
        headers = call_kwargs["default_headers"]
        assert headers.get("HTTP-Referer") == "https://prizms.app"
        assert headers.get("X-Title") == "Prizms"

    @patch("providers.openrouter.ChatOpenAI")
    def test_get_llm_ignores_instance_parameter(self, mock_chat_openai):
        """Instance parameter should be ignored (OpenRouter handles concurrency)."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-opus",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="sk-or-test-key-12345",
        )

        # Call with instance parameter
        result1 = provider.get_llm(config, instance=None)
        result2 = provider.get_llm(config, instance=0)
        result3 = provider.get_llm(config, instance=5)

        # All should work the same way
        assert result1 == mock_instance
        assert result2 == mock_instance
        assert result3 == mock_instance

    @patch("providers.openrouter.ChatOpenAI")
    def test_different_models(self, mock_chat_openai):
        """Should correctly pass different model IDs in OpenRouter format."""
        mock_chat_openai.return_value = MagicMock()
        provider = OpenRouterProvider()

        models = [
            "anthropic/claude-3-opus",
            "openai/gpt-4-turbo",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large",
            "google/gemini-pro-1.5",
        ]

        for model_id in models:
            config = ModelConfig(
                model_name=f"or-{model_id.split('/')[-1]}",
                provider_type="openrouter",
                model_id=model_id,
                api_base="",
                api_key="sk-or-test-key",
            )
            provider.get_llm(config)

            # Verify the model was passed correctly
            call_kwargs = mock_chat_openai.call_args.kwargs
            assert call_kwargs["model"] == model_id


class TestOpenRouterProviderFactory:
    """Test that OpenRouterProvider is correctly registered in the factory."""

    def test_provider_in_factory(self):
        """OpenRouter provider should be available via get_providers."""
        from providers.factory import get_providers

        providers = get_providers()
        assert "openrouter" in providers
        assert isinstance(providers["openrouter"], OpenRouterProvider)


@pytest.mark.skipif(
    not OPENROUTER_API_KEY,
    reason="OPENROUTER_API_KEY environment variable not set"
)
class TestOpenRouterIntegration:
    """Integration tests requiring a real OpenRouter API key.
    
    These tests are skipped by default. To run them:
        OPENROUTER_API_KEY=sk-or-... uv run pytest tests/providers/test_openrouter.py -v
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the API."""
        provider = OpenRouterProvider()
        config = ModelConfig(
            model_name="or-claude-sonnet",
            provider_type="openrouter",
            model_id="anthropic/claude-3.5-sonnet",  # Fast and economical via OpenRouter
            api_base="",
            api_key=OPENROUTER_API_KEY,
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
