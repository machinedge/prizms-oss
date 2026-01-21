"""Ollama LLM provider implementation."""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


class OllamaProvider(LLMProvider):
    """Provider for Ollama models.

    Ollama exposes an OpenAI-compatible API at /v1 endpoint.
    Default URL: http://localhost:11434/v1
    """

    def get_llm(self, config: ModelConfig) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for Ollama.

        Args:
            config: Model configuration with Ollama server details

        Returns:
            A configured ChatOpenAI client
        """
        return ChatOpenAI(
            base_url=config.api_base,
            api_key=config.api_key or "not-needed",
            model=config.model_id,
        )
