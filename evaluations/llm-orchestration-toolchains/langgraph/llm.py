"""LLM client factory."""

from langchain_openai import ChatOpenAI


def get_llm(instance: int | None = None) -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for LM Studio.

    Args:
        instance: Optional instance number for multi-instance setups.
                  If provided, appends ":N" to the model name.

    Returns:
        A configured ChatOpenAI client.
    """
    if instance is None or instance == 0:
        _inst = ""
    else:
        _inst = f":{instance + 1}"
    return ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        model=f"qwen/qwen3-4b-thinking-2507{_inst}",
    )
