"""Tests for the OpenAI GPT provider."""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.openai import OpenAIProvider
from providers.base import ModelConfig


# Environment variable for integration tests
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


class TestOpenAIProvider:
    """Test suite for OpenAIProvider."""

    def test_provider_instantiation(self):
        """Provider should instantiate without errors."""
        provider = OpenAIProvider()
        assert provider is not None

    def test_api_key_required(self):
        """Should raise ValueError if no API key provided."""
        provider = OpenAIProvider()
        config = ModelConfig(
            model_name="gpt-4o",
            provider_type="openai",
            model_id="gpt-4o",
            api_base="",
            api_key="",  # Empty API key
        )

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            provider.get_llm(config)

    def test_api_key_error_mentions_env_var(self):
        """Error message should mention OPENAI_API_KEY environment variable."""
        provider = OpenAIProvider()
        config = ModelConfig(
            model_name="gpt-4o",
            provider_type="openai",
            model_id="gpt-4o",
            api_base="",
            api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            provider.get_llm(config)

        assert "OPENAI_API_KEY" in str(exc_info.value)

    @patch("providers.openai.ChatOpenAI")
    def test_get_llm_returns_chat_openai(self, mock_chat_openai):
        """Should return a ChatOpenAI instance when configured properly."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        provider = OpenAIProvider()
        config = ModelConfig(
            model_name="gpt-4o",
            provider_type="openai",
            model_id="gpt-4o",
            api_base="",
            api_key="sk-test-key-12345",
        )

        result = provider.get_llm(config)

        assert result == mock_instance
        mock_chat_openai.assert_called_once_with(
            model="gpt-4o",
            api_key="sk-test-key-12345",
        )

    @patch("providers.openai.ChatOpenAI")
    def test_get_llm_ignores_instance_parameter(self, mock_chat_openai):
        """Instance parameter should be ignored (OpenAI handles concurrency)."""
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        provider = OpenAIProvider()
        config = ModelConfig(
            model_name="gpt-4o",
            provider_type="openai",
            model_id="gpt-4o",
            api_base="",
            api_key="sk-test-key-12345",
        )

        # Call with instance parameter
        result1 = provider.get_llm(config, instance=None)
        result2 = provider.get_llm(config, instance=0)
        result3 = provider.get_llm(config, instance=5)

        # All should work the same way
        assert result1 == mock_instance
        assert result2 == mock_instance
        assert result3 == mock_instance

    @patch("providers.openai.ChatOpenAI")
    def test_different_models(self, mock_chat_openai):
        """Should correctly pass different model IDs."""
        mock_chat_openai.return_value = MagicMock()
        provider = OpenAIProvider()

        models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

        for model_id in models:
            config = ModelConfig(
                model_name="test-model",
                provider_type="openai",
                model_id=model_id,
                api_base="",
                api_key="sk-test-key",
            )
            provider.get_llm(config)

            # Verify the model was passed correctly
            call_args = mock_chat_openai.call_args
            assert call_args.kwargs["model"] == model_id


class TestOpenAIProviderFactory:
    """Test that OpenAIProvider is correctly registered in the factory."""

    def test_provider_in_factory(self):
        """OpenAI provider should be available via get_providers."""
        from providers.factory import get_providers

        providers = get_providers()
        assert "openai" in providers
        assert isinstance(providers["openai"], OpenAIProvider)


@pytest.mark.skipif(
    not OPENAI_API_KEY,
    reason="OPENAI_API_KEY environment variable not set"
)
class TestOpenAIIntegration:
    """Integration tests requiring a real OpenAI API key.
    
    These tests are skipped by default. To run them:
        OPENAI_API_KEY=sk-... uv run pytest tests/providers/test_openai.py -v
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the API."""
        provider = OpenAIProvider()
        config = ModelConfig(
            model_name="gpt-4o-mini",
            provider_type="openai",
            model_id="gpt-4o-mini",  # Fastest/cheapest model
            api_base="",
            api_key=OPENAI_API_KEY,
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
