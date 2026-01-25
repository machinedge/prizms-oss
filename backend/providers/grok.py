"""xAI Grok LLM provider implementation.

Handles xAI's Grok models via the langchain-openai package.
Grok uses an OpenAI-compatible API, so we use ChatOpenAI with xAI's base URL.
Requires a valid API key for authentication.
"""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig

# xAI API endpoint
XAI_API_BASE = "https://api.x.ai/v1"


class GrokProvider(LLMProvider):
    """Provider for xAI Grok models.

    Grok models use an OpenAI-compatible API, so we use ChatOpenAI
    with xAI's base URL. Unlike local providers, this requires a valid API key.

    Available models:
        - grok-3 (latest Grok 3 model, recommended)
        - grok-3-mini (smaller, faster Grok 3 model)
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for xAI Grok.

        Args:
            config: Model configuration with xAI API details
            instance: Ignored. xAI handles concurrent requests internally.

        Returns:
            A configured ChatOpenAI client pointing to xAI's API

        Raises:
            ValueError: If api_key is not provided
        """
        if not config.api_key:
            raise ValueError(
                "xAI API key is required. "
                "Set it in your config.yaml or via XAI_API_KEY environment variable."
            )

        return ChatOpenAI(
            model=config.model_id,
            api_key=config.api_key,
            base_url=config.api_base or XAI_API_BASE,
        )
