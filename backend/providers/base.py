"""Base classes and dataclasses for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_openai import ChatOpenAI


@dataclass
class ModelConfig:
    """Configuration for a model, parsed from model_list entry.

    Attributes:
        model_name: Friendly alias (e.g., "ollama-llama3")
        provider_type: Extracted from model prefix (e.g., "ollama")
        model_id: Model identifier (e.g., "llama3")
        api_base: Base URL for the API endpoint
        api_key: API key (empty string for local servers)
    """

    model_name: str
    provider_type: str
    model_id: str
    api_base: str
    api_key: str = ""


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers (Ollama, vLLM, LM Studio) implement this interface.
    Since they all support OpenAI-compatible APIs, implementations are
    thin wrappers around ChatOpenAI with provider-specific defaults.
    """

    @abstractmethod
    def get_llm(self, config: ModelConfig) -> ChatOpenAI:
        """Return a configured LLM client for the given model.

        Args:
            config: Model configuration with provider details

        Returns:
            A configured ChatOpenAI client
        """
        pass
