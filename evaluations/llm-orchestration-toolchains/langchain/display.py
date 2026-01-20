"""Rich terminal UI components for streaming display."""

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
