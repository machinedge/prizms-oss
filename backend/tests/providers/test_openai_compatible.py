"""Tests for the unified OpenAI-compatible provider.

This module tests the OpenAICompatibleProvider which handles:
- Cloud providers: openai, grok, openrouter (require API keys)
- Local providers: ollama, vllm, lm_studio (no API key required)
"""

import os

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from providers.openai_compatible import (
    OpenAICompatibleProvider,
    PROVIDER_CONFIGS,
    ProviderConfig,
)
from providers.base import ModelConfig


# Environment variables for integration tests
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")


# =============================================================================
# Unit Tests - Parameterized across all provider types
# =============================================================================


class TestOpenAICompatibleProviderInstantiation:
    """Test provider instantiation for all types."""

    @pytest.mark.parametrize("provider_type", list(PROVIDER_CONFIGS.keys()))
    def test_provider_instantiation(self, provider_type):
        """All provider types should instantiate without errors."""
        provider = OpenAICompatibleProvider(provider_type)
        assert provider is not None
        assert provider.provider_type == provider_type
        assert provider.provider_config == PROVIDER_CONFIGS[provider_type]

    def test_unknown_provider_raises_error(self):
        """Should raise KeyError for unknown provider type."""
        with pytest.raises(KeyError, match="Unknown provider type"):
            OpenAICompatibleProvider("unknown_provider")


class TestAPIKeyValidation:
    """Test API key validation for providers that require it."""

    @pytest.mark.parametrize(
        "provider_type,env_var",
        [
            ("openai", "OPENAI_API_KEY"),
            ("grok", "XAI_API_KEY"),
            ("openrouter", "OPENROUTER_API_KEY"),
        ],
    )
    def test_api_key_required(self, provider_type, env_var):
        """Cloud providers should raise ValueError if no API key provided."""
        provider = OpenAICompatibleProvider(provider_type)
        config = ModelConfig(
            model_name="test-model",
            provider_type=provider_type,
            model_id="test-model-id",
            api_base="",
            api_key="",  # Empty API key
        )

        with pytest.raises(ValueError, match="API key is required"):
            provider.get_llm(config)

    @pytest.mark.parametrize(
        "provider_type,env_var",
        [
            ("openai", "OPENAI_API_KEY"),
            ("grok", "XAI_API_KEY"),
            ("openrouter", "OPENROUTER_API_KEY"),
        ],
    )
    def test_api_key_error_mentions_env_var(self, provider_type, env_var):
        """Error message should mention the correct environment variable."""
        provider = OpenAICompatibleProvider(provider_type)
        config = ModelConfig(
            model_name="test-model",
            provider_type=provider_type,
            model_id="test-model-id",
            api_base="",
            api_key="",
        )

        with pytest.raises(ValueError) as exc_info:
            provider.get_llm(config)

        assert env_var in str(exc_info.value)

    @pytest.mark.parametrize("provider_type", ["ollama", "vllm", "lm_studio"])
    def test_local_providers_no_api_key_required(self, provider_type):
        """Local providers should work without API key."""
        provider = OpenAICompatibleProvider(provider_type)
        config = ModelConfig(
            model_name="test-model",
            provider_type=provider_type,
            model_id="test-model-id",
            api_base="http://localhost:8000/v1",
            api_key="",  # Empty API key - should work for local providers
        )

        # Should not raise - just verify it works
        with patch(
            "providers.openai_compatible.ChatOpenAI"
        ) as mock_chat:
            mock_chat.return_value = MagicMock()
            llm = provider.get_llm(config)
            assert llm is not None


class TestChatOpenAIConfiguration:
    """Test that ChatOpenAI is configured correctly for each provider."""

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_openai_configuration(self, mock_chat_openai):
        """OpenAI should be configured without base_url (uses default)."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("openai")
        config = ModelConfig(
            model_name="gpt-4o",
            provider_type="openai",
            model_id="gpt-4o",
            api_base="",
            api_key="sk-test-key",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["api_key"] == "sk-test-key"
        assert "base_url" not in call_kwargs  # OpenAI uses default

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_grok_uses_xai_base_url(self, mock_chat_openai):
        """Grok should use xAI API base URL."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("grok")
        config = ModelConfig(
            model_name="grok-3",
            provider_type="grok",
            model_id="grok-3",
            api_base="",  # Empty, should use default
            api_key="xai-test-key",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://api.x.ai/v1"

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_openrouter_uses_openrouter_base_url(self, mock_chat_openai):
        """OpenRouter should use OpenRouter API base URL."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("openrouter")
        config = ModelConfig(
            model_name="or-claude",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="sk-or-test-key",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_openrouter_sets_custom_headers(self, mock_chat_openai):
        """OpenRouter should set HTTP-Referer and X-Title headers."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("openrouter")
        config = ModelConfig(
            model_name="or-claude",
            provider_type="openrouter",
            model_id="anthropic/claude-3-opus",
            api_base="",
            api_key="sk-or-test-key",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert "default_headers" in call_kwargs
        headers = call_kwargs["default_headers"]
        assert headers.get("HTTP-Referer") == "https://prizms.app"
        assert headers.get("X-Title") == "Prizms"

    @pytest.mark.parametrize("provider_type", ["ollama", "vllm", "lm_studio"])
    @patch("providers.openai_compatible.ChatOpenAI")
    def test_local_providers_use_not_needed_api_key(
        self, mock_chat_openai, provider_type
    ):
        """Local providers should use 'not-needed' as API key placeholder."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider(provider_type)
        config = ModelConfig(
            model_name="test-model",
            provider_type=provider_type,
            model_id="test-model-id",
            api_base="http://localhost:8000/v1",
            api_key="",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["api_key"] == "not-needed"

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_custom_base_url_overrides_default(self, mock_chat_openai):
        """Custom api_base in config should override provider default."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("grok")
        config = ModelConfig(
            model_name="grok-3",
            provider_type="grok",
            model_id="grok-3",
            api_base="https://custom.api.com/v1",  # Custom URL
            api_key="xai-test-key",
        )

        provider.get_llm(config)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://custom.api.com/v1"


class TestLMStudioInstanceSuffix:
    """Test LM Studio's instance suffix handling for parallel execution."""

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_lm_studio_no_suffix_for_none_instance(self, mock_chat_openai):
        """LM Studio should not add suffix for instance=None."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("lm_studio")
        config = ModelConfig(
            model_name="test-model",
            provider_type="lm_studio",
            model_id="qwen/qwen3-4b",
            api_base="http://localhost:1234/v1",
            api_key="",
        )

        provider.get_llm(config, instance=None)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "qwen/qwen3-4b"

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_lm_studio_no_suffix_for_zero_instance(self, mock_chat_openai):
        """LM Studio should not add suffix for instance=0."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("lm_studio")
        config = ModelConfig(
            model_name="test-model",
            provider_type="lm_studio",
            model_id="qwen/qwen3-4b",
            api_base="http://localhost:1234/v1",
            api_key="",
        )

        provider.get_llm(config, instance=0)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "qwen/qwen3-4b"

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_lm_studio_adds_suffix_for_nonzero_instance(self, mock_chat_openai):
        """LM Studio should add :N suffix for instance > 0."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("lm_studio")
        config = ModelConfig(
            model_name="test-model",
            provider_type="lm_studio",
            model_id="qwen/qwen3-4b",
            api_base="http://localhost:1234/v1",
            api_key="",
        )

        provider.get_llm(config, instance=1)

        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "qwen/qwen3-4b:2"  # instance + 1

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_lm_studio_suffix_increments_correctly(self, mock_chat_openai):
        """LM Studio instance suffix should be instance + 1."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider("lm_studio")
        config = ModelConfig(
            model_name="test-model",
            provider_type="lm_studio",
            model_id="model",
            api_base="http://localhost:1234/v1",
            api_key="",
        )

        for instance in [1, 2, 5, 10]:
            provider.get_llm(config, instance=instance)
            call_kwargs = mock_chat_openai.call_args.kwargs
            expected = f"model:{instance + 1}"
            assert call_kwargs["model"] == expected

    @pytest.mark.parametrize("provider_type", ["openai", "grok", "openrouter", "ollama", "vllm"])
    @patch("providers.openai_compatible.ChatOpenAI")
    def test_other_providers_ignore_instance(self, mock_chat_openai, provider_type):
        """Non-LM Studio providers should ignore instance parameter."""
        mock_chat_openai.return_value = MagicMock()

        provider = OpenAICompatibleProvider(provider_type)
        
        # Set up config based on provider requirements
        api_key = "test-key" if PROVIDER_CONFIGS[provider_type].api_key_required else ""
        api_base = "http://localhost:8000/v1" if provider_type in ["ollama", "vllm"] else ""
        
        config = ModelConfig(
            model_name="test-model",
            provider_type=provider_type,
            model_id="test-model-id",
            api_base=api_base,
            api_key=api_key,
        )

        provider.get_llm(config, instance=5)

        call_kwargs = mock_chat_openai.call_args.kwargs
        # Model should NOT have instance suffix
        assert call_kwargs["model"] == "test-model-id"


class TestFactoryRegistration:
    """Test that all providers are correctly registered in the factory."""

    def test_all_providers_in_factory(self):
        """All OpenAI-compatible providers should be available via get_providers."""
        from providers.factory import get_providers

        providers = get_providers()

        for provider_type in PROVIDER_CONFIGS.keys():
            assert provider_type in providers
            assert isinstance(providers[provider_type], OpenAICompatibleProvider)
            assert providers[provider_type].provider_type == provider_type


class TestDifferentModels:
    """Test that different model IDs are passed correctly."""

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_openai_models(self, mock_chat_openai):
        """OpenAI should pass various model IDs correctly."""
        mock_chat_openai.return_value = MagicMock()
        provider = OpenAICompatibleProvider("openai")

        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

        for model_id in models:
            config = ModelConfig(
                model_name="test",
                provider_type="openai",
                model_id=model_id,
                api_base="",
                api_key="sk-test-key",
            )
            provider.get_llm(config)

            call_kwargs = mock_chat_openai.call_args.kwargs
            assert call_kwargs["model"] == model_id

    @patch("providers.openai_compatible.ChatOpenAI")
    def test_openrouter_models(self, mock_chat_openai):
        """OpenRouter should pass provider/model format correctly."""
        mock_chat_openai.return_value = MagicMock()
        provider = OpenAICompatibleProvider("openrouter")

        models = [
            "anthropic/claude-3-opus",
            "openai/gpt-4-turbo",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large",
        ]

        for model_id in models:
            config = ModelConfig(
                model_name="test",
                provider_type="openrouter",
                model_id=model_id,
                api_base="",
                api_key="sk-or-test-key",
            )
            provider.get_llm(config)

            call_kwargs = mock_chat_openai.call_args.kwargs
            assert call_kwargs["model"] == model_id


# =============================================================================
# Integration Tests - Per-provider, skipped if API key not set
# =============================================================================


@pytest.mark.skipif(
    not OPENAI_API_KEY, reason="OPENAI_API_KEY environment variable not set"
)
class TestOpenAIIntegration:
    """Integration tests requiring a real OpenAI API key.

    These tests are skipped by default. To run them:
        OPENAI_API_KEY=sk-... uv run pytest tests/providers/test_openai_compatible.py -v -k "OpenAIIntegration"
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the OpenAI API."""
        provider = OpenAICompatibleProvider("openai")
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
        assert (
            "hello" in full_response.lower()
        ), f"Expected 'hello' in response: {full_response}"


@pytest.mark.skipif(
    not XAI_API_KEY, reason="XAI_API_KEY environment variable not set"
)
class TestGrokIntegration:
    """Integration tests requiring a real xAI API key.

    These tests are skipped by default. To run them:
        XAI_API_KEY=xai-... uv run pytest tests/providers/test_openai_compatible.py -v -k "GrokIntegration"
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the xAI API."""
        provider = OpenAICompatibleProvider("grok")
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
        assert (
            "hello" in full_response.lower()
        ), f"Expected 'hello' in response: {full_response}"


@pytest.mark.skipif(
    not OPENROUTER_API_KEY, reason="OPENROUTER_API_KEY environment variable not set"
)
class TestOpenRouterIntegration:
    """Integration tests requiring a real OpenRouter API key.

    These tests are skipped by default. To run them:
        OPENROUTER_API_KEY=sk-or-... uv run pytest tests/providers/test_openai_compatible.py -v -k "OpenRouterIntegration"
    """

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Verify streaming chunks arrive from the OpenRouter API."""
        provider = OpenAICompatibleProvider("openrouter")
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
        assert (
            "hello" in full_response.lower()
        ), f"Expected 'hello' in response: {full_response}"
