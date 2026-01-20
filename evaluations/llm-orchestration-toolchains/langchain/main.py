"""
Prizms - Multi-perspective LLM tool using LangChain.

Sends a question to multiple "personality" prompts in parallel
with real-time streaming output in a multi-column terminal display.
Saves each response to separate chain-of-thought and answer markdown files.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from rich.layout import Layout
from rich.live import Live

from config import Config, discover_personalities, load_config, load_prompt
from display import console, create_layout, update_panel
from llm import get_llm
from output import save_responses


async def stream_personality(
    instance: int,
    personality: str,
    question: str,
    personalities_dir: Path,
    buffers: dict[str, str],
    layout: Layout,
    live: Live,
) -> tuple[str, str]:
    """Stream LLM response for a personality and update the display."""
    llm = get_llm(instance)
    system_prompt = load_prompt(personalities_dir, personality)
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


async def get_perspectives_streaming(
    question: str,
    config: Config,
    personalities: list[str],
) -> dict[str, str]:
    """Get responses from all personalities in parallel with streaming display."""
    layout = create_layout(personalities)
    buffers: dict[str, str] = {}

    # Initialize panels
    for personality in personalities:
        update_panel(layout, personality, "Waiting for response...")

    with Live(layout, console=console, refresh_per_second=10) as live:
        tasks = [
            stream_personality(
                i, p, question, config.personalities_dir, buffers, layout, live
            )
            for i, p in enumerate(personalities)
        ]
        results = await asyncio.gather(*tasks)

    return dict(results)


async def main(question: str, config: Config) -> None:
    """Main entry point."""
    personalities = discover_personalities(config.personalities_dir)

    if not personalities:
        console.print(
            f"[red]Error:[/red] No personality files (*.txt) found in {config.personalities_dir}"
        )
        return

    console.print(f"[bold]Question:[/bold] {question}")
    console.print(f"[dim]Personalities: {', '.join(personalities)}[/dim]\n")

    responses = await get_perspectives_streaming(question, config, personalities)

    console.print()  # Add spacing after live display
    save_responses(responses, config.output_dir)
    console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-perspective LLM tool using LangChain"
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Question to ask the personalities",
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="Path to a .txt or .md file containing the question",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to TOML config file (default: use prompts/ and outputs/ in script directory)",
    )
    args = parser.parse_args()

    # Resolve question from file or argument
    if args.file:
        if not args.file.exists():
            console.print(f"[red]Error:[/red] File not found: {args.file}")
            sys.exit(1)
        if args.file.suffix.lower() not in (".txt", ".md"):
            console.print(f"[red]Error:[/red] File must be .txt or .md: {args.file}")
            sys.exit(1)
        question = args.file.read_text().strip()
    elif args.question:
        question = args.question
    else:
        parser.error("Either a question or --file must be provided")

    config = load_config(args.config)
    asyncio.run(main(question, config))
