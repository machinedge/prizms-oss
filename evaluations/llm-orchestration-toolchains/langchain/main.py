"""
Prizms - Multi-perspective LLM tool using LangChain.

Sends a question to three different "personality" prompts in parallel
and saves each response to a markdown file.
"""

import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Directory paths
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"
OUTPUTS_DIR = SCRIPT_DIR / "outputs"

# Personality configurations
PERSONALITIES = ["judge", "chaos_monkey", "critic"]


def load_prompt(name: str) -> str:
    """Load a personality prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    return prompt_path.read_text()


def get_llm(instance : [int|None]) -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for LM Studio."""
    if instance is None or instance == 0:
        _inst  = ""
    else:
        _inst = f":{instance + 1}"
    return ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        model=f"qwen/qwen3-4b-thinking-2507{_inst}",
    )

async def invoke_personality(
    instance: int, personality: str, question: str
) -> tuple[str, str]:
    """Invoke the LLM with a specific personality and return the response."""
    llm = get_llm(instance)
    system_prompt = load_prompt(personality)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]
    response = await llm.ainvoke(messages)
    return (personality, response.content)


async def get_perspectives(question: str) -> dict[str, str]:
    """Get responses from all personalities in parallel."""
    tasks = [
        invoke_personality(i, p, question)
        for i, p in enumerate(PERSONALITIES)
    ]
    results = await asyncio.gather(*tasks)
    return dict(results)


def save_responses(responses: dict[str, str]) -> None:
    """Save each personality response to a markdown file."""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    for personality, content in responses.items():
        output_path = OUTPUTS_DIR / f"{personality}.md"
        output_path.write_text(content)
        print(f"Saved: {output_path}")


async def main(question: str) -> None:
    """Main entry point."""
    print(f"Question: {question}\n")
    print("Getting perspectives from all personalities...")
    responses = await get_perspectives(question)
    save_responses(responses)
    print("\nDone!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python main.py \"Your question here\"")
        sys.exit(1)

    question = sys.argv[1]
    asyncio.run(main(question))
