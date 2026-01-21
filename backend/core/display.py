"""Rich terminal UI components for streaming display."""

import re

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

console = Console()


def format_personality_name(name: str) -> str:
    """Format personality name for display.

    Converts underscores to spaces and title-cases the result.
    Example: "chaos_monkey" -> "Chaos Monkey"
    """
    return name.replace("_", " ").title()


def create_layout(personalities: list[str]) -> Layout:
    """Create dynamic N-column layout for personalities.

    Creates a horizontal split with one column per personality,
    each with equal ratio.
    """
    layout = Layout()
    layout.split_row(*[Layout(name=p, ratio=1) for p in personalities])
    return layout


def create_round_layout(personalities: list[str], round_num: int) -> Layout:
    """Create dynamic N-column layout for personalities with round context.

    Creates a horizontal split with one column per personality,
    each with equal ratio. The round number is stored for use in panel titles.

    Args:
        personalities: List of personality names
        round_num: Current round number (1-indexed)

    Returns:
        Layout configured for the round
    """
    layout = Layout()
    layout.split_row(*[Layout(name=p, ratio=1) for p in personalities])
    # Store round number as layout attribute for panel updates
    layout._round_num = round_num  # type: ignore[attr-defined]
    return layout


def update_panel(layout: Layout, personality: str, content: str) -> None:
    """Update a personality's panel with new content.

    Truncates content to the last 30 lines to keep the display manageable.
    """
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


def extract_answer(content: str) -> str:
    """Extract the answer portion from content (everything after </think> tags).

    Args:
        content: Full response including potential <think>...</think> tags

    Returns:
        The answer portion, or the full content if no think tags found
    """
    think_pattern = r"<think>.*?</think>"
    answer = re.sub(think_pattern, "", content, flags=re.DOTALL).strip()
    return answer if answer else content.strip()


def print_round_summary(round_num: int, responses: dict[str, str]) -> None:
    """Print a compact summary line after a round completes.

    Shows personality names with character counts.

    Args:
        round_num: The round number that just completed
        responses: Dict mapping personality names to their full responses
    """
    parts = []
    for personality, content in responses.items():
        display_name = format_personality_name(personality)
        char_count = len(content)
        parts.append(f"{display_name} ({char_count:,} chars)")

    summary = " | ".join(parts)
    console.print(f"[dim]Round {round_num} complete: {summary}[/dim]")


def print_answers(round_num: int, responses: dict[str, str]) -> None:
    """Print the answers from a round prominently.

    Extracts content after </think> tags and displays in a clean format.

    Args:
        round_num: The round number
        responses: Dict mapping personality names to their full responses
    """
    console.print(f"\n[bold]Round {round_num} Answers[/bold]")
    console.print("─" * 60)

    for personality, content in responses.items():
        display_name = format_personality_name(personality)
        answer = extract_answer(content)

        # Truncate very long answers for display
        if len(answer) > 500:
            display_answer = answer[:500] + "..."
        else:
            display_answer = answer

        console.print(f"\n[bold cyan]{display_name}:[/bold cyan]")
        console.print(display_answer)

    console.print("─" * 60)
