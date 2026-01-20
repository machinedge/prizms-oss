"""Node functions for the debate graph."""

import asyncio
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from rich.layout import Layout
from rich.live import Live

from display import console, create_round_layout, update_panel
from llm import get_llm


def load_prompt(personalities_dir: str, name: str) -> str:
    """Load a personality prompt from the personalities directory."""
    return (Path(personalities_dir) / f"{name}.txt").read_text()


def format_previous_round(previous_round: dict[str, str] | None) -> str:
    """Format the previous round's responses for inclusion in the prompt.

    Args:
        previous_round: Dict mapping personality names to their responses,
                       or None if this is the first round.

    Returns:
        Formatted string to append to the user message.
    """
    if not previous_round:
        return ""

    lines = ["\n\n## Previous Round Responses\n"]
    for personality, response in previous_round.items():
        display_name = personality.replace("_", " ").title()
        # Truncate very long responses to keep context manageable
        truncated = response[:2000] + "..." if len(response) > 2000 else response
        lines.append(f"**{display_name}**: {truncated}\n")
    lines.append("\n---\n\nNow provide your response, considering the above perspectives.")
    return "".join(lines)


async def stream_personality(
    instance: int,
    personality: str,
    question: str,
    previous_round: dict[str, str] | None,
    personalities_dir: str,
    buffers: dict[str, str],
    layout: Layout,
    live: Live,
) -> tuple[str, str]:
    """Stream LLM response for a personality and update the display.

    Args:
        instance: LLM instance number for multi-instance setups
        personality: Name of the personality
        question: The original question
        previous_round: Previous round responses (None for first round)
        personalities_dir: Path to personality prompt files
        buffers: Shared dict for accumulating streamed content
        layout: Rich Layout for display
        live: Rich Live context for refreshing

    Returns:
        Tuple of (personality_name, full_response)
    """
    llm = get_llm(instance)
    system_prompt = load_prompt(personalities_dir, personality)

    # Build user message with optional previous round context
    user_content = question + format_previous_round(previous_round)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    buffers[personality] = ""

    async for chunk in llm.astream(messages):
        if chunk.content:
            buffers[personality] += chunk.content
            update_panel(layout, personality, buffers[personality])
            live.refresh()

    return (personality, buffers[personality])


def debate_round(state: dict) -> dict:
    """Execute one round of debate with all personalities responding in parallel.

    This node runs all personalities concurrently, streaming their responses
    to a multi-column Rich display.

    Args:
        state: Current debate state

    Returns:
        Updated state with new round appended and current_round incremented
    """
    personalities = state["personalities"]
    question = state["question"]
    personalities_dir = state["personalities_dir"]
    current_round = state.get("current_round", 0)

    # Get previous round if exists
    rounds = state.get("rounds", [])
    previous_round = rounds[-1] if rounds else None

    round_num = current_round + 1
    console.print(f"\n[bold cyan]Round {round_num}[/bold cyan]")

    layout = create_round_layout(personalities, round_num)
    buffers: dict[str, str] = {}

    # Initialize panels
    for personality in personalities:
        update_panel(layout, personality, "Waiting for response...")

    async def run_all():
        with Live(layout, console=console, refresh_per_second=10) as live:
            tasks = [
                stream_personality(
                    i,
                    p,
                    question,
                    previous_round,
                    personalities_dir,
                    buffers,
                    layout,
                    live,
                )
                for i, p in enumerate(personalities)
            ]
            results = await asyncio.gather(*tasks)
        return dict(results)

    responses = asyncio.run(run_all())

    return {
        "rounds": [responses],  # Will be appended via operator.add
        "current_round": round_num,
    }


def check_consensus(state: dict) -> dict:
    """Check if personalities have reached consensus.

    Uses a neutral LLM call to analyze the latest round of responses
    and determine if substantial agreement has been reached.

    Args:
        state: Current debate state

    Returns:
        Updated state with consensus_reached and consensus_reasoning
    """
    rounds = state.get("rounds", [])
    if not rounds:
        return {"consensus_reached": False, "consensus_reasoning": "No responses yet"}

    current_round = rounds[-1]
    current_round_num = state.get("current_round", 1)

    # Skip consensus check on first round - always do at least 2 rounds
    if current_round_num < 2:
        console.print("[dim]Skipping consensus check on first round...[/dim]")
        return {"consensus_reached": False, "consensus_reasoning": "First round - continuing debate"}

    # Load consensus check prompt using configured name
    personalities_dir = state["personalities_dir"]
    consensus_prompt_name = state.get("consensus_prompt", "consensus_check")
    try:
        consensus_prompt_text = load_prompt(personalities_dir, consensus_prompt_name)
    except FileNotFoundError:
        # Fallback if prompt file doesn't exist
        consensus_prompt_text = """You are analyzing a multi-perspective debate. Review the responses below 
and determine if the participants have reached substantial agreement on 
the core points, even if they differ in emphasis or framing.

Respond with JSON only: {"consensus": true/false, "reasoning": "brief explanation"}"""

    # Format responses for analysis
    response_text = "\n\n".join(
        f"**{p.replace('_', ' ').title()}**: {r}"
        for p, r in current_round.items()
    )

    llm = get_llm()
    messages = [
        SystemMessage(content=consensus_prompt_text),
        HumanMessage(content=f"Analyze these responses for consensus:\n\n{response_text}"),
    ]

    console.print("[dim]Checking for consensus...[/dim]")

    # Synchronous call for consensus check (no need to stream)
    response = asyncio.run(llm.ainvoke(messages))
    content = response.content

    # Parse JSON response
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            result = json.loads(json_match.group())
            consensus = result.get("consensus", False)
            reasoning = result.get("reasoning", "No reasoning provided")
        else:
            consensus = False
            reasoning = f"Could not parse response: {content[:200]}"
    except json.JSONDecodeError:
        consensus = False
        reasoning = f"Invalid JSON in response: {content[:200]}"

    if consensus:
        console.print(f"[green]Consensus reached:[/green] {reasoning}")
    else:
        console.print(f"[yellow]No consensus:[/yellow] {reasoning}")

    return {
        "consensus_reached": consensus,
        "consensus_reasoning": reasoning,
    }


def synthesize(state: dict) -> dict:
    """Produce final synthesized output from the designated synthesizer personality.

    The synthesizer reviews all rounds of debate and produces a final
    integrated perspective.

    Args:
        state: Current debate state

    Returns:
        Updated state with final_synthesis
    """
    synthesizer = state["synthesizer"]
    personalities_dir = state["personalities_dir"]
    question = state["question"]
    rounds = state.get("rounds", [])
    consensus_reasoning = state.get("consensus_reasoning", "")

    console.print(f"\n[bold magenta]Synthesis by {synthesizer.replace('_', ' ').title()}[/bold magenta]")

    # Load synthesizer's personality prompt
    try:
        base_prompt = load_prompt(personalities_dir, synthesizer)
    except FileNotFoundError:
        base_prompt = "You are a thoughtful synthesizer of multiple perspectives."

    # Build context from all rounds
    context_parts = [f"Original Question: {question}\n"]

    for i, round_responses in enumerate(rounds, 1):
        context_parts.append(f"\n## Round {i} Responses\n")
        for personality, response in round_responses.items():
            display_name = personality.replace("_", " ").title()
            # Truncate for context window
            truncated = response[:1500] + "..." if len(response) > 1500 else response
            context_parts.append(f"**{display_name}**: {truncated}\n")

    context_parts.append(f"\n## Debate Status\n{consensus_reasoning}\n")
    context_parts.append(
        "\n---\n\nAs the synthesizer, provide a final integrated perspective "
        "that captures the key insights from all viewpoints and rounds of debate."
    )

    synthesis_prompt = base_prompt + "\n\nYou are now acting as the final synthesizer for this debate."

    llm = get_llm()
    messages = [
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content="".join(context_parts)),
    ]

    # Stream the synthesis
    full_response = ""

    async def stream_synthesis():
        nonlocal full_response
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                console.print(chunk.content, end="")

    asyncio.run(stream_synthesis())
    console.print()  # Newline after streaming

    return {"final_synthesis": full_response}
