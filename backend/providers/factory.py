"""Factory functions for creating LLM providers."""

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .gemini import GeminiProvider
from .openai_compatible import OpenAICompatibleProvider, PROVIDER_CONFIGS


def get_providers() -> dict[str, LLMProvider]:
    """Get singleton instances of each provider type.

    Returns:
        Dictionary mapping provider type names to provider instances.
        Keys are: "ollama", "vllm", "lm_studio", "anthropic", "openai", "gemini", "grok", "openrouter"
    """
    # Create OpenAI-compatible providers from the config registry
    providers: dict[str, LLMProvider] = {
        name: OpenAICompatibleProvider(name) for name in PROVIDER_CONFIGS
    }

    # Add providers with native clients
    providers["anthropic"] = AnthropicProvider()
    providers["gemini"] = GeminiProvider()

    return providers
