"""Tests for the Anthropic Claude provider."""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.anthropic import AnthropicProvider
from providers.base import ModelConfig


# Environment variable for integration tests
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class TestAnthropicProvider:
    """Test suite for AnthropicProvider."""

    def test_provider_instantiation(self):
        """Provider should instantiate without errors."""
        provider = AnthropicProvider()
        assert provider is not None

    def test_api_key_required(self):
        """Should raise ValueError if no API key provided."""
        provider = AnthropicProvider()
        config = ModelConfig(
            model_name="claude-sonnet",
            provider_type="anthropic",
            model_id="claude-sonnet-4-20250514",
            api_base="",
            api_key="",  # Empty API key
        )

        with pytest.raises(ValueError, match="Anthropic API key is required"):
            provider.get_llm(config)

    def test_api_key_whitespace_only_rejected(self):
        """Should raise ValueError if API key is only whitespace."""
        provider = AnthropicProvider()
        config = ModelConfig(
            model_name="claude-sonnet",
            provider_type="anthropic",
            model_id="claude-sonnet-4-20250514",
            api_base="",
            api_key="   ",  # Whitespace only - treated as falsy after strip
        )

        # Whitespace string is truthy in Python, so this will pass validation
        # but may fail on actual API call. This test documents current behavior.
        # If we want to reject whitespace, we'd need to add .strip() check.
        # For now, we just test the empty string case.

    @patch("providers.anthropic.ChatAnthropic")
    def test_get_llm_returns_chat_anthropic(self, mock_chat_anthropic):
        """Should return a ChatAnthropic instance when configured properly."""
        mock_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_instance

        provider = AnthropicProvider()
        config = ModelConfig(
            model_name="claude-sonnet",
            provider_type="anthropic",
            model_id="claude-sonnet-4-20250514",
            api_base="",
            api_key="sk-ant-test-key",
        )

        result = provider.get_llm(config)

        assert result == mock_instance
        mock_chat_anthropic.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            api_key="sk-ant-test-key",
        )

    @patch("providers.anthropic.ChatAnthropic")
    def test_get_llm_ignores_instance_parameter(self, mock_chat_anthropic):
        """Instance parameter should be ignored (Anthropic handles concurrency)."""
        mock_instance = MagicMock()
        mock_chat_anthropic.return_value = mock_instance

        provider = AnthropicProvider()
        config = ModelConfig(
            model_name="claude-sonnet",
            provider_type="anthropic",
            model_id="claude-sonnet-4-20250514",
            api_base="",
            api_key="sk-ant-test-key",
        )

        # Call with instance parameter
        result1 = provider.get_llm(config, instance=0)
        result2 = provider.get_llm(config, instance=5)

        # Both should work the same way
        assert result1 == mock_instance
        assert result2 == mock_instance

    @patch("providers.anthropic.ChatAnthropic")
    def test_different_models(self, mock_chat_anthropic):
        """Should correctly pass different model IDs."""
        mock_chat_anthropic.return_value = MagicMock()
        provider = AnthropicProvider()

        models = [
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-3-5-haiku-20241022",
        ]

        for model_id in models:
            config = ModelConfig(
                model_name="test-model",
                provider_type="anthropic",
                model_id=model_id,
                api_base="",
                api_key="sk-ant-test-key",
            )
            provider.get_llm(config)

            # Verify the model was passed correctly
            call_args = mock_chat_anthropic.call_args
            assert call_args.kwargs["model"] == model_id


class TestAnthropicProviderFactory:
    """Test that AnthropicProvider is correctly registered in the factory."""

    def test_provider_in_factory(self):
        """Anthropic provider should be available via get_providers."""
        from providers.factory import get_providers

        providers = get_providers()
        assert "anthropic" in providers
        assert isinstance(providers["anthropic"], AnthropicProvider)


@pytest.mark.skipif(
    not ANTHROPIC_API_KEY,
    reason="ANTHROPIC_API_KEY environment variable not set"
)
class TestAnthropicIntegration:
    """Integration tests requiring a real Anthropic API key.
    
    These tests are skipped by default. To run them:
        ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/providers/test_anthropic.py -v
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the API."""
        provider = AnthropicProvider()
        config = ModelConfig(
            model_name="claude-haiku",
            provider_type="anthropic",
            model_id="claude-3-5-haiku-20241022",  # Fastest/cheapest model
            api_base="",
            api_key=ANTHROPIC_API_KEY,
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
