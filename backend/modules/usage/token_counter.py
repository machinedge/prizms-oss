"""
Token counting utilities.

Provides accurate token counting for different LLM providers.
Uses tiktoken (via LangChain's transitive dependency) for tokenization.
"""

from typing import Optional
import tiktoken

# Cache encoders to avoid repeated initialization
_encoders: dict[str, tiktoken.Encoding] = {}


def get_encoder(model: str) -> tiktoken.Encoding:
    """
    Get the appropriate tokenizer for a model.

    Most modern models (GPT-4, Claude, Gemini, Grok) use similar
    tokenization to cl100k_base.

    Args:
        model: Model name (e.g., "gpt-4", "claude-3-5-sonnet")

    Returns:
        tiktoken.Encoding instance
    """
    # Map models to tiktoken encodings
    # cl100k_base is used by GPT-4, GPT-3.5-turbo, and is a good
    # approximation for other modern models like Claude
    if model.startswith("gpt-4") or model.startswith("gpt-3.5"):
        encoding_name = "cl100k_base"
    elif "claude" in model.lower():
        # Claude uses similar tokenization to GPT-4
        encoding_name = "cl100k_base"
    elif "gemini" in model.lower():
        # Gemini uses similar tokenization
        encoding_name = "cl100k_base"
    elif "grok" in model.lower():
        # Grok uses similar tokenization
        encoding_name = "cl100k_base"
    elif "llama" in model.lower():
        # Llama models use similar tokenization
        encoding_name = "cl100k_base"
    else:
        # Default to cl100k_base for most modern models
        encoding_name = "cl100k_base"

    if encoding_name not in _encoders:
        _encoders[encoding_name] = tiktoken.get_encoding(encoding_name)

    return _encoders[encoding_name]


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in a text string.

    Args:
        text: The text to count tokens for
        model: Model name for tokenizer selection

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    encoder = get_encoder(model)
    return len(encoder.encode(text))


def count_message_tokens(
    messages: list[dict],
    model: str = "gpt-4",
) -> int:
    """
    Count tokens in a list of chat messages.

    Includes overhead for message formatting (role markers, etc.).
    Based on OpenAI's token counting methodology.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name for tokenizer selection

    Returns:
        Total token count including formatting overhead
    """
    encoder = get_encoder(model)
    total = 0

    for message in messages:
        # Add tokens for message structure overhead
        # Every message follows <|start|>{role}<|message|>{content}<|end|>
        total += 4  # Approximate overhead per message

        for key, value in message.items():
            if isinstance(value, str):
                total += len(encoder.encode(value))

    # Every reply is primed with <|start|>assistant<|message|>
    total += 2

    return total


def estimate_output_tokens(content: str, model: str = "gpt-4") -> int:
    """
    Estimate tokens in generated output.

    This is a simple wrapper around count_tokens for semantic clarity.

    Args:
        content: Generated content
        model: Model name

    Returns:
        Estimated token count
    """
    return count_tokens(content, model)


def estimate_input_tokens(
    question: str,
    system_prompt: str = "",
    prior_context: str = "",
    model: str = "gpt-4",
    default_system_overhead: int = 200,
) -> int:
    """
    Estimate input tokens for an LLM call.

    Used as a fallback when actual usage metadata is not available from
    the LLM API response. Estimates tokens based on the content that would
    be sent to the model.

    Args:
        question: The user question or content
        system_prompt: The system prompt (if empty, uses default overhead)
        prior_context: Any prior context included in the prompt
        model: Model name for tokenizer selection
        default_system_overhead: Default tokens to assume for system prompt
                                if not provided

    Returns:
        Estimated input token count
    """
    total = 0

    # Count question tokens
    total += count_tokens(question, model)

    # Count system prompt tokens or use default overhead
    if system_prompt:
        total += count_tokens(system_prompt, model)
    else:
        total += default_system_overhead

    # Count prior context tokens
    if prior_context:
        total += count_tokens(prior_context, model)

    # Add message formatting overhead (system + user message structure)
    # Each message has ~4 tokens overhead, plus 2 for assistant priming
    total += 10

    return total


def reset_encoder_cache() -> None:
    """Reset the encoder cache (for testing)."""
    global _encoders
    _encoders = {}
