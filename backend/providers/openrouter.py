"""OpenRouter LLM provider implementation.

OpenRouter provides unified access to 100+ models from various providers
through an OpenAI-compatible API.
Requires a valid API key for authentication.
"""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig

# OpenRouter API endpoint
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


class OpenRouterProvider(LLMProvider):
    """Provider for OpenRouter (unified model access).

    OpenRouter provides access to models from OpenAI, Anthropic, Google,
    Meta, Mistral, and many others through a single OpenAI-compatible API.

    Model names are in format: provider/model
    Examples:
        - anthropic/claude-3-opus
        - openai/gpt-4-turbo
        - meta-llama/llama-3.1-70b-instruct
        - mistralai/mistral-large
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for OpenRouter.

        Args:
            config: Model configuration with OpenRouter API details.
                    model_id should be in OpenRouter format (provider/model).
            instance: Ignored. OpenRouter handles concurrent requests internally.

        Returns:
            A configured ChatOpenAI client pointing to OpenRouter's API

        Raises:
            ValueError: If api_key is not provided
        """
        if not config.api_key:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set it in your config.yaml or via OPENROUTER_API_KEY environment variable."
            )

        return ChatOpenAI(
            model=config.model_id,
            api_key=config.api_key,
            base_url=config.api_base or OPENROUTER_API_BASE,
            default_headers={
                "HTTP-Referer": "https://prizms.app",  # For OpenRouter rankings
                "X-Title": "Prizms",  # For OpenRouter rankings
            },
        )
