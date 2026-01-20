"""
Prizms - Multi-round debate LLM tool using LangGraph.

Sends a question to multiple "personality" prompts for multi-round debate
with real-time streaming output in a multi-column terminal display.
Personalities can respond to each other across rounds until consensus
is reached or max rounds is hit. A designated synthesizer produces
the final integrated perspective.
"""

import argparse
import sys
from pathlib import Path

from config import Config, discover_personalities, load_config
from display import console
from graph import build_graph
from output import save_responses


def run_debate(
    question: str,
    config: Config,
    personalities: list[str],
    max_rounds: int,
) -> dict:
    """Run the multi-round debate graph.

    Args:
        question: The question to debate
        config: Configuration object
        personalities: List of personality names
        max_rounds: Maximum number of debate rounds

    Returns:
        Final state from the graph execution
    """
    # Build and compile the graph
    graph = build_graph()

    # Initialize state
    initial_state = {
        "question": question,
        "personalities": personalities,
        "personalities_dir": str(config.personalities_dir),
        "max_rounds": max_rounds,
        "current_round": 0,
        "rounds": [],
        "consensus_reached": False,
        "consensus_reasoning": "",
        "consensus_prompt": config.consensus_prompt,
        "synthesizer_prompt": config.synthesizer_prompt,
        "final_synthesis": None,
    }

    # Run the graph
    final_state = graph.invoke(initial_state)

    return final_state


def main(
    question: str,
    config: Config,
    max_rounds_override: int | None = None,
) -> None:
    """Main entry point.

    Args:
        question: The question to debate
        config: Configuration object
        max_rounds_override: CLI override for max rounds
    """
    # Exclude system prompts (consensus_check, synthesizer) from debate personalities
    excluded = {config.consensus_prompt, config.synthesizer_prompt}
    personalities = discover_personalities(config.personalities_dir, exclude=excluded)

    if not personalities:
        console.print(
            f"[red]Error:[/red] No personality files (*.txt) found in {config.personalities_dir}"
        )
        return

    # Determine max rounds
    max_rounds = max_rounds_override if max_rounds_override else config.max_rounds

    console.print(f"[bold]Question:[/bold] {question}")
    console.print(f"[dim]Personalities: {', '.join(personalities)}[/dim]")
    console.print(f"[dim]Synthesizer: {config.synthesizer_prompt}[/dim]")
    console.print(f"[dim]Max rounds: {max_rounds}[/dim]\n")

    # Run the debate
    final_state = run_debate(question, config, personalities, max_rounds)

    # Collect all responses from all rounds for saving
    all_responses: dict[str, str] = {}
    rounds = final_state.get("rounds", [])

    # Use the last round's responses as the primary output
    if rounds:
        all_responses = rounds[-1].copy()

    # Add synthesis as a special entry (will be handled separately for COT/answer split)
    if final_state.get("final_synthesis"):
        all_responses["synthesizer"] = final_state["final_synthesis"]

    console.print()  # Add spacing
    save_responses(all_responses, config.output_dir)

    # Summary
    console.print(f"\n[dim]Completed in {len(rounds)} round(s)[/dim]")
    if final_state.get("consensus_reached"):
        console.print("[green]Consensus was reached[/green]")
    else:
        console.print("[yellow]Max rounds reached without consensus[/yellow]")

    console.print("\n[bold green]Done![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-round debate LLM tool using LangGraph"
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
    parser.add_argument(
        "--max-rounds", "-r",
        type=int,
        help="Maximum number of debate rounds (default: 3 or config value)",
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
    main(question, config, args.max_rounds)
