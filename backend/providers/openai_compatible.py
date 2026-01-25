"""Unified provider for all OpenAI-compatible APIs.

This module consolidates 6 providers (ollama, vllm, lm_studio, openai, grok, openrouter)
that all use LangChain's ChatOpenAI client with minor configuration differences.

The only providers NOT handled here are:
- Anthropic: Uses ChatAnthropic (different client)
- Gemini: Uses ChatGoogleGenerativeAI (different client)
"""

from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


@dataclass
class ProviderConfig:
    """Configuration for an OpenAI-compatible provider.

    Attributes:
        default_base_url: Default API endpoint URL (None uses OpenAI's default)
        api_key_required: Whether an API key must be provided
        api_key_env_var: Environment variable name for the API key (for error messages)
        default_headers: Custom HTTP headers to include in requests
        supports_instance_suffix: Whether to append instance suffix for parallel execution
    """

    default_base_url: str | None = None
    api_key_required: bool = True
    api_key_env_var: str = ""
    default_headers: dict[str, str] | None = None
    supports_instance_suffix: bool = False


# Provider configurations registry
PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        api_key_required=True,
        api_key_env_var="OPENAI_API_KEY",
    ),
    "grok": ProviderConfig(
        default_base_url="https://api.x.ai/v1",
        api_key_required=True,
        api_key_env_var="XAI_API_KEY",
    ),
    "openrouter": ProviderConfig(
        default_base_url="https://openrouter.ai/api/v1",
        api_key_required=True,
        api_key_env_var="OPENROUTER_API_KEY",
        default_headers={"HTTP-Referer": "https://prizms.app", "X-Title": "Prizms"},
    ),
    "ollama": ProviderConfig(api_key_required=False),
    "vllm": ProviderConfig(api_key_required=False),
    "lm_studio": ProviderConfig(api_key_required=False, supports_instance_suffix=True),
}


class OpenAICompatibleProvider(LLMProvider):
    """Unified provider for all OpenAI-compatible APIs.

    Handles: ollama, vllm, lm_studio, openai, grok, openrouter

    All these providers use LangChain's ChatOpenAI client with different
    configuration options:
    - Local providers (ollama, vllm, lm_studio): No API key required, custom base URL
    - Cloud providers (openai, grok, openrouter): API key required
    - OpenRouter: Custom headers for attribution
    - LM Studio: Instance suffix for parallel execution
    """

    def __init__(self, provider_type: str):
        """Initialize the provider.

        Args:
            provider_type: One of: openai, grok, openrouter, ollama, vllm, lm_studio

        Raises:
            KeyError: If provider_type is not recognized
        """
        if provider_type not in PROVIDER_CONFIGS:
            raise KeyError(
                f"Unknown provider type: {provider_type}. "
                f"Valid types: {list(PROVIDER_CONFIGS.keys())}"
            )
        self.provider_type = provider_type
        self.provider_config = PROVIDER_CONFIGS[provider_type]

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for this provider.

        Args:
            config: Model configuration with provider details
            instance: Instance number for parallel execution (LM Studio only).
                     If None or 0, no suffix is added.
                     Otherwise, appends ":N" where N = instance + 1.

        Returns:
            A configured ChatOpenAI client

        Raises:
            ValueError: If api_key is required but not provided
        """
        # Validate API key if required
        if self.provider_config.api_key_required and not config.api_key:
            raise ValueError(
                f"{self.provider_type.title()} API key is required. "
                f"Set it in your config.yaml or via {self.provider_config.api_key_env_var} environment variable."
            )

        # Build model name with instance suffix if needed (LM Studio)
        model = config.model_id
        if self.provider_config.supports_instance_suffix and instance and instance > 0:
            model = f"{model}:{instance + 1}"

        # Build kwargs for ChatOpenAI
        kwargs: dict = {"model": model}

        # Set base URL (from config or provider default)
        if base_url := (config.api_base or self.provider_config.default_base_url):
            kwargs["base_url"] = base_url

        # Set API key (use "not-needed" placeholder for local providers)
        kwargs["api_key"] = config.api_key or "not-needed"

        # Add custom headers if configured (OpenRouter)
        if self.provider_config.default_headers:
            kwargs["default_headers"] = self.provider_config.default_headers

        return ChatOpenAI(**kwargs)
