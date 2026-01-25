"""Factory functions for creating LLM providers."""

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .vllm import VLLMProvider


def get_providers() -> dict[str, LLMProvider]:
    """Get singleton instances of each provider type.

    Returns:
        Dictionary mapping provider type names to provider instances.
        Keys are: "ollama", "vllm", "lm_studio", "anthropic"
    """
    return {
        "ollama": OllamaProvider(),
        "vllm": VLLMProvider(),
        "lm_studio": LMStudioProvider(),
        "anthropic": AnthropicProvider(),
    }
