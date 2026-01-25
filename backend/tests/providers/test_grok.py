"""Tests for the Grok provider."""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.grok import GrokProvider, XAI_API_BASE
from providers.base import ModelConfig


# Environment variable for integration tests
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")


class TestGrokProvider:
    """Tests for GrokProvider class."""

    @pytest.fixture
    def provider(self):
        """Create a GrokProvider instance."""
        return GrokProvider()

    @pytest.fixture
    def valid_config(self):
        """Create a valid ModelConfig for Grok."""
        return ModelConfig(
            model_name="grok-2",
            provider_type="grok",
            model_id="grok-2-1212",
            api_base="",  # Will use default XAI_API_BASE
            api_key="xai-test-key-12345",
        )

    @pytest.fixture
    def config_without_key(self):
        """Create a ModelConfig without API key."""
        return ModelConfig(
            model_name="grok-2",
            provider_type="grok",
            model_id="grok-2-1212",
            api_base="",
            api_key="",
        )

    def test_get_llm_returns_chat_openai(self, provider, valid_config):
        """Should return a ChatOpenAI instance with correct configuration."""
        llm = provider.get_llm(valid_config)

        assert llm is not None
        assert llm.model_name == "grok-2-1212"

    def test_get_llm_uses_xai_base_url(self, provider, valid_config):
        """Should use xAI API base URL by default."""
        llm = provider.get_llm(valid_config)

        assert str(llm.openai_api_base).rstrip("/") == XAI_API_BASE

    def test_get_llm_accepts_custom_base_url(self, provider):
        """Should accept custom API base URL."""
        config = ModelConfig(
            model_name="grok-2",
            provider_type="grok",
            model_id="grok-2-1212",
            api_base="https://custom.api.com/v1",
            api_key="xai-test-key",
        )
        llm = provider.get_llm(config)

        assert "custom.api.com" in str(llm.openai_api_base)

    def test_get_llm_requires_api_key(self, provider, config_without_key):
        """Should raise ValueError when API key is missing."""
        with pytest.raises(ValueError) as exc_info:
            provider.get_llm(config_without_key)

        assert "API key is required" in str(exc_info.value)
        assert "XAI_API_KEY" in str(exc_info.value)

    def test_get_llm_ignores_instance_parameter(self, provider, valid_config):
        """Instance parameter should be ignored (xAI handles concurrency)."""
        llm1 = provider.get_llm(valid_config, instance=None)
        llm2 = provider.get_llm(valid_config, instance=1)
        llm3 = provider.get_llm(valid_config, instance=5)

        # All should work without errors
        assert llm1 is not None
        assert llm2 is not None
        assert llm3 is not None

    def test_get_llm_with_different_models(self, provider):
        """Should work with various Grok models."""
        models = ["grok-3", "grok-3-mini"]

        for model in models:
            config = ModelConfig(
                model_name=model,
                provider_type="grok",
                model_id=model,
                api_base="",
                api_key="xai-test-key",
            )
            llm = provider.get_llm(config)
            assert llm.model_name == model

    def test_provider_registered_in_factory(self):
        """Grok provider should be registered in the factory."""
        from providers.factory import get_providers

        providers = get_providers()
        assert "grok" in providers
        assert isinstance(providers["grok"], GrokProvider)


@pytest.mark.skipif(
    not XAI_API_KEY,
    reason="XAI_API_KEY environment variable not set"
)
class TestGrokIntegration:
    """Integration tests requiring a real xAI API key.
    
    These tests are skipped by default. To run them:
        XAI_API_KEY=xai-... uv run pytest tests/providers/test_grok.py -v
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the API."""
        provider = GrokProvider()
        config = ModelConfig(
            model_name="grok-3",
            provider_type="grok",
            model_id="grok-3",  # Current recommended model
            api_base="",
            api_key=XAI_API_KEY,
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
