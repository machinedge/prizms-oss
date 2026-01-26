"""Google Gemini LLM provider implementation.

Handles Google's Gemini models via the langchain-google-genai package.
Requires a valid API key for authentication.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from .base import LLMProvider, ModelConfig


class GeminiProvider(LLMProvider):
    """Provider for Google Gemini models.

    Gemini models use the ChatGoogleGenerativeAI client from langchain-google-genai.
    Unlike local providers, this requires a valid API key.

    Available models:
        - gemini-2.0-flash (fast and efficient, recommended)
        - gemini-2.0-flash-lite (fastest, most economical)
        - gemini-1.5-pro (previous generation, most capable)
    """

    def get_llm(self, config: ModelConfig, instance: int | None = None) -> ChatGoogleGenerativeAI:
        """Return a ChatGoogleGenerativeAI client configured for Gemini.

        Args:
            config: Model configuration with Google AI API details
            instance: Ignored. Google handles concurrent requests internally.

        Returns:
            A configured ChatGoogleGenerativeAI client

        Raises:
            ValueError: If api_key is not provided
        """
        if not config.api_key:
            raise ValueError(
                "Google AI API key is required. "
                "Set it in your config.yaml or via GOOGLE_API_KEY environment variable."
            )

        return ChatGoogleGenerativeAI(
            model=config.model_id,
            google_api_key=config.api_key,
        )
