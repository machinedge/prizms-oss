"""Anthropic Claude LLM provider implementation.

Handles Anthropic's Claude models via the langchain-anthropic package.
Unlike local providers (Ollama, vLLM, LM Studio), Anthropic requires
a valid API key for authentication.
"""

from langchain_anthropic import ChatAnthropic

from .base import LLMProvider, ModelConfig


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models.

    Anthropic models use a different API than OpenAI-compatible providers,
    so we use ChatAnthropic from langchain-anthropic instead of ChatOpenAI.

    Available models:
        - claude-sonnet-4-20250514 (balanced speed and capability)
        - claude-opus-4-20250514 (most capable)
        - claude-3-5-haiku-20241022 (fastest, most economical)
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatAnthropic:
        """Return a ChatAnthropic client configured for Claude.

        Args:
            config: Model configuration with Anthropic API details
            instance: Ignored. Anthropic handles concurrent requests internally.

        Returns:
            A configured ChatAnthropic client

        Raises:
            ValueError: If api_key is not provided
        """
        if not config.api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set it in your config.yaml or via ANTHROPIC_API_KEY environment variable."
            )

        return ChatAnthropic(
            model=config.model_id,
            api_key=config.api_key,
        )
