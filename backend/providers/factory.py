"""Factory functions for creating LLM providers."""

from .base import LLMProvider
from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .vllm import VLLMProvider


def get_providers() -> dict[str, LLMProvider]:
    """Get singleton instances of each provider type.

    Returns:
        Dictionary mapping provider type names to provider instances.
        Keys are: "ollama", "vllm", "lm_studio"
    """
    return {
        "ollama": OllamaProvider(),
        "vllm": VLLMProvider(),
        "lm_studio": LMStudioProvider(),
    }


def parse_model_string(model: str) -> tuple[str, str]:
    """Parse 'provider/model_id' into (provider_type, model_id).

    Args:
        model: Model string in format "provider/model_id"
               e.g., "ollama/llama3", "vllm/mistral-7b"

    Returns:
        Tuple of (provider_type, model_id)

    Raises:
        ValueError: If model string doesn't contain a '/'
    """
    if "/" not in model:
        raise ValueError(
            f"Invalid model string '{model}'. "
            "Expected format: 'provider/model_id' (e.g., 'ollama/llama3')"
        )
    provider_type, model_id = model.split("/", 1)
    return provider_type, model_id
