"""LM Studio LLM provider implementation."""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


class LMStudioProvider(LLMProvider):
    """Provider for LM Studio models.

    LM Studio exposes an OpenAI-compatible API.
    Default URL: http://localhost:1234/v1

    Note: Unlike the original implementation, this provider does not use
    instance suffixes. All concurrent requests go to the same endpoint
    and the server handles batching internally.
    """

    def get_llm(self, config: ModelConfig) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for LM Studio.

        Args:
            config: Model configuration with LM Studio server details

        Returns:
            A configured ChatOpenAI client
        """
        return ChatOpenAI(
            base_url=config.api_base,
            api_key=config.api_key or "not-needed",
            model=config.model_id,
        )
