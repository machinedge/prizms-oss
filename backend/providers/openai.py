"""OpenAI GPT LLM provider implementation.

Handles OpenAI's GPT models via the langchain-openai package.
Unlike local providers (Ollama, vLLM, LM Studio), OpenAI requires
a valid API key for authentication.
"""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI GPT models.

    OpenAI models use the standard ChatOpenAI client with OpenAI's
    default API endpoint. Unlike local providers, this requires a valid API key.

    Available models:
        - gpt-4o (latest multimodal, recommended)
        - gpt-4o-mini (faster, more economical)
        - gpt-4-turbo (previous generation)
        - gpt-3.5-turbo (fastest, most economical)
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for OpenAI.

        Args:
            config: Model configuration with OpenAI API details
            instance: Ignored. OpenAI handles concurrent requests internally.

        Returns:
            A configured ChatOpenAI client

        Raises:
            ValueError: If api_key is not provided
        """
        if not config.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set it in your config.yaml or via OPENAI_API_KEY environment variable."
            )

        return ChatOpenAI(
            model=config.model_id,
            api_key=config.api_key,
        )
