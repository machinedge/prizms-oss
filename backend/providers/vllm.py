"""vLLM LLM provider implementation."""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


class VLLMProvider(LLMProvider):
    """Provider for vLLM models.

    vLLM exposes an OpenAI-compatible API.
    Default URL: http://localhost:8000/v1
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for vLLM.

        Args:
            config: Model configuration with vLLM server details
            instance: Ignored. vLLM handles concurrent requests internally.

        Returns:
            A configured ChatOpenAI client
        """
        return ChatOpenAI(
            base_url=config.api_base,
            api_key=config.api_key or "not-needed",
            model=config.model_id,
        )
