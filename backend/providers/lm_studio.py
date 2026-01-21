"""LM Studio LLM provider implementation."""

from langchain_openai import ChatOpenAI

from .base import LLMProvider, ModelConfig


class LMStudioProvider(LLMProvider):
    """Provider for LM Studio models.

    LM Studio exposes an OpenAI-compatible API.
    Default URL: http://localhost:1234/v1

    LM Studio requires separate model instances for parallel execution.
    When running multiple personalities concurrently, each needs its own
    instance, specified by appending ":N" to the model name (e.g., "model:2").
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatOpenAI:
        """Return a ChatOpenAI client configured for LM Studio.

        Args:
            config: Model configuration with LM Studio server details
            instance: Instance number for parallel execution.
                     If None or 0, no suffix is added.
                     Otherwise, appends ":N" where N = instance + 1.

        Returns:
            A configured ChatOpenAI client
        """
        # Build instance suffix for parallel execution
        if instance is None or instance == 0:
            instance_suffix = ""
        else:
            instance_suffix = f":{instance + 1}"

        return ChatOpenAI(
            base_url=config.api_base,
            api_key=config.api_key or "not-needed",
            model=f"{config.model_id}{instance_suffix}",
        )
