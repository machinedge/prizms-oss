"""Factory functions for creating LLM providers."""

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .gemini import GeminiProvider
from .grok import GrokProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .vllm import VLLMProvider


def get_providers() -> dict[str, LLMProvider]:
    """Get singleton instances of each provider type.

    Returns:
        Dictionary mapping provider type names to provider instances.
        Keys are: "ollama", "vllm", "lm_studio", "anthropic", "openai", "gemini", "grok"
    """
    return {
        "ollama": OllamaProvider(),
        "vllm": VLLMProvider(),
        "lm_studio": LMStudioProvider(),
        "anthropic": AnthropicProvider(),
        "openai": OpenAIProvider(),
        "gemini": GeminiProvider(),
        "grok": GrokProvider(),
    }
