"""Response parsing and file output."""

import re
from pathlib import Path

from rich.console import Console

from display import format_personality_name

console = Console()


def split_cot_and_answer(content: str) -> tuple[str, str]:
    """Split response into chain-of-thought and answer.

    Extracts content within <think>...</think> tags as chain-of-thought,
    and everything else as the answer.

    Returns:
        A tuple of (chain_of_thought, answer).
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


def save_responses(responses: dict[str, str], output_dir: Path) -> None:
    """Save each personality response to COT and answer files.

    Creates separate files for chain-of-thought (*.cot.md) and
    final answers (*.ans.md) for each personality.
    """
    output_dir.mkdir(exist_ok=True)

    for personality, content in responses.items():
        cot, answer = split_cot_and_answer(content)
        display_name = format_personality_name(personality)

        # Save chain of thought
        cot_path = output_dir / f"{personality}.cot.md"
        if cot:
            cot_content = f"# {display_name} - Chain of Thought\n\n{cot}"
        else:
            cot_content = f"# {display_name} - Chain of Thought\n\n*No chain of thought captured.*"
        cot_path.write_text(cot_content)
        console.print(f"[green]Saved:[/green] {cot_path}")

        # Save answer
        ans_path = output_dir / f"{personality}.ans.md"
        ans_content = f"# {display_name} - Answer\n\n{answer}"
        ans_path.write_text(ans_content)
        console.print(f"[green]Saved:[/green] {ans_path}")
