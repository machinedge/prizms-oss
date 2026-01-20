"""
Prizms - Multi-perspective LLM tool using LangChain.

Sends a question to three different "personality" prompts in parallel
with real-time streaming output in a multi-column terminal display.
Saves each response to separate chain-of-thought and answer markdown files.
"""

import asyncio
import re
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

# Directory paths
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"
OUTPUTS_DIR = SCRIPT_DIR / "outputs"

# Personality configurations
PERSONALITIES = ["judge", "chaos_monkey", "critic"]

# Console for Rich output
console = Console()


def load_prompt(name: str) -> str:
    """Load a personality prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    return prompt_path.read_text()


def get_llm(instance: int | None) -> ChatOpenAI:
    """Create a ChatOpenAI instance configured for LM Studio."""
    if instance is None or instance == 0:
        _inst = ""
    else:
        _inst = f":{instance + 1}"
    return ChatOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed",
        model=f"qwen/qwen3-4b-thinking-2507{_inst}",
    )


def split_cot_and_answer(content: str) -> tuple[str, str]:
    """Split response into chain-of-thought and answer.

    Extracts content within <think>...</think> tags as chain-of-thought,
    and everything else as the answer.
    """
    think_pattern = r"<think>(.*?)</think>"
    match = re.search(think_pattern, content, re.DOTALL)

    if match:
        cot = match.group(1).strip()
        answer = re.sub(think_pattern, "", content, flags=re.DOTALL).strip()
    else:
        cot = ""
        answer = content.strip()

    return cot, answer


def format_personality_name(name: str) -> str:
    """Format personality name for display."""
    return name.replace("_", " ").title()


def create_layout() -> Layout:
    """Create a three-column layout for the personalities."""
    layout = Layout()
    layout.split_row(
        Layout(name="judge", ratio=1),
        Layout(name="chaos_monkey", ratio=1),
        Layout(name="critic", ratio=1),
    )
    return layout


def update_panel(layout: Layout, personality: str, content: str) -> None:
    """Update a personality's panel with new content."""
    # Truncate content to last N lines to keep display manageable
    lines = content.split("\n")
    max_lines = 30
    if len(lines) > max_lines:
        display_content = "...\n" + "\n".join(lines[-max_lines:])
    else:
        display_content = content

    panel = Panel(
        Text(display_content, overflow="fold"),
        title=format_personality_name(personality),
        border_style="blue",
    )
    layout[personality].update(panel)


async def stream_personality(
    instance: int,
    personality: str,
    question: str,
    buffers: dict[str, str],
    layout: Layout,
    live: Live,
) -> tuple[str, str]:
    """Stream LLM response for a personality and update the display."""
    llm = get_llm(instance)
    system_prompt = load_prompt(personality)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    buffers[personality] = ""

    async for chunk in llm.astream(messages):
        if chunk.content:
            buffers[personality] += chunk.content
            update_panel(layout, personality, buffers[personality])
            live.refresh()

    return (personality, buffers[personality])


async def get_perspectives_streaming(question: str) -> dict[str, str]:
    """Get responses from all personalities in parallel with streaming display."""
    layout = create_layout()
    buffers: dict[str, str] = {}

    # Initialize panels
    for personality in PERSONALITIES:
        update_panel(layout, personality, "Waiting for response...")

    with Live(layout, console=console, refresh_per_second=10) as live:
        tasks = [
            stream_personality(i, p, question, buffers, layout, live)
            for i, p in enumerate(PERSONALITIES)
        ]
        results = await asyncio.gather(*tasks)

    return dict(results)


def save_responses(responses: dict[str, str]) -> None:
    """Save each personality response to separate COT and answer markdown files."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    for personality, content in responses.items():
        cot, answer = split_cot_and_answer(content)
        display_name = format_personality_name(personality)

        # Save chain of thought
        cot_path = OUTPUTS_DIR / f"{personality}.cot.md"
        cot_content = f"# {display_name} - Chain of Thought\n\n{cot}" if cot else f"# {display_name} - Chain of Thought\n\n*No chain of thought captured.*"
        cot_path.write_text(cot_content)
        console.print(f"[green]Saved:[/green] {cot_path}")

        # Save answer
        ans_path = OUTPUTS_DIR / f"{personality}.ans.md"
        ans_content = f"# {display_name} - Answer\n\n{answer}"
        ans_path.write_text(ans_content)
        console.print(f"[green]Saved:[/green] {ans_path}")


async def main(question: str) -> None:
    """Main entry point."""
    console.print(f"[bold]Question:[/bold] {question}\n")
    console.print("[dim]Streaming perspectives from all personalities...[/dim]\n")

    responses = await get_perspectives_streaming(question)

    console.print()  # Add spacing after live display
    save_responses(responses)
    console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage:[/red] uv run python main.py \"Your question here\"")
        sys.exit(1)

    question = sys.argv[1]
    asyncio.run(main(question))
