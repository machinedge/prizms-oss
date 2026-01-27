"""Base classes and models for LLM providers."""

from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Configuration for a model, parsed from model_list entry.

    Attributes:
        model_name: Friendly alias (e.g., "ollama-llama3")
        provider_type: Extracted from model prefix (e.g., "ollama")
        model_id: Model identifier (e.g., "llama3")
        api_base: Base URL for the API endpoint
        api_key: API key (empty string for local servers)
    """

    model_config = {"frozen": True}

    model_name: str
    provider_type: str
    model_id: str
    api_base: str = ""
    api_key: str = ""


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers (Ollama, vLLM, LM Studio) implement this interface.
    Since they all support OpenAI-compatible APIs, implementations are
    thin wrappers around ChatOpenAI with provider-specific defaults.
    """

    @abstractmethod
    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a configured LLM client for the given model.

        Args:
            config: Model configuration with provider details
            instance: Optional instance number for providers that require
                     separate instances for parallel execution (e.g., LM Studio).
                     If None or 0, no suffix is added.

        Returns:
            A configured ChatOpenAI client
        """
        pass
