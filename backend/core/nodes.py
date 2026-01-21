"""Node functions for the debate graph."""

import asyncio
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from rich.layout import Layout
from rich.live import Live

from providers.base import LLMProvider, ModelConfig

from .config import Config, PersonalityConfig, load_prompt
from .display import (
    console,
    create_round_layout,
    print_answers,
    print_round_summary,
    update_panel,
)


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


def get_llm_for_personality(
    personality_name: str,
    config: Config,
    providers: dict[str, LLMProvider],
    instance: int | None = None,
):
    """Get the LLM client for a specific personality.

    Args:
        personality_name: Name of the personality
        config: Full configuration object
        providers: Dictionary of provider instances by type
        instance: Optional instance number for providers that require
                 separate instances for parallel execution (e.g., LM Studio).

    Returns:
        Configured ChatOpenAI client for this personality
    """
    personality_config = config.personalities[personality_name]
    model_config = config.models[personality_config.model_name]
    provider = providers[model_config.provider_type]
    return provider.get_llm(model_config, instance)


async def stream_personality(
    personality_name: str,
    question: str,
    previous_round: dict[str, str] | None,
    config: Config,
    providers: dict[str, LLMProvider],
    buffers: dict[str, str],
    layout: Layout,
    live: Live,
    instance: int | None = None,
) -> tuple[str, str]:
    """Stream LLM response for a personality and update the display.

    Args:
        personality_name: Name of the personality
        question: The original question
        previous_round: Previous round responses (None for first round)
        config: Full configuration object
        providers: Dictionary of provider instances by type
        buffers: Shared dict for accumulating streamed content
        layout: Rich Layout for display
        live: Rich Live context for refreshing
        instance: Optional instance number for providers that require
                 separate instances for parallel execution (e.g., LM Studio).

    Returns:
        Tuple of (personality_name, full_response)
    """
    # Get the LLM for this personality
    llm = get_llm_for_personality(personality_name, config, providers, instance)

    # Load the prompt for this personality
    personality_config = config.personalities[personality_name]
    system_prompt = load_prompt(personality_config.prompt_path)

    # Build user message with optional previous round context
    user_content = question + format_previous_round(previous_round)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    buffers[personality_name] = ""

    async for chunk in llm.astream(messages):
        if chunk.content:
            buffers[personality_name] += chunk.content
            update_panel(layout, personality_name, buffers[personality_name])
            live.refresh()

    return (personality_name, buffers[personality_name])


def _compute_provider_instances(
    personalities: list[str], config: Config
) -> dict[str, int]:
    """Compute per-provider instance numbers for each personality.

    LM Studio requires separate instances for parallel execution, so we need
    to assign instance numbers within each provider type, not globally.

    Args:
        personalities: List of personality names
        config: Configuration with personality and model mappings

    Returns:
        Dictionary mapping personality name to its provider-specific instance number
    """
    # Count instances per provider type
    provider_counts: dict[str, int] = {}
    instance_map: dict[str, int] = {}

    for personality_name in personalities:
        personality_config = config.personalities[personality_name]
        model_config = config.models[personality_config.model_name]
        provider_type = model_config.provider_type

        # Get current count for this provider (starts at 0)
        instance_num = provider_counts.get(provider_type, 0)
        instance_map[personality_name] = instance_num

        # Increment count for next personality using this provider
        provider_counts[provider_type] = instance_num + 1

    return instance_map


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
    config: Config = state["config"]
    providers: dict[str, LLMProvider] = state["providers"]
    current_round = state.get("current_round", 0)

    # Get previous round if exists
    rounds = state.get("rounds", [])
    previous_round = rounds[-1] if rounds else None

    round_num = current_round + 1
    console.print(f"\n[bold cyan]Round {round_num}[/bold cyan]")

    layout = create_round_layout(personalities, round_num)
    buffers: dict[str, str] = {}

    # Compute per-provider instance numbers for LM Studio parallel execution
    instance_map = _compute_provider_instances(personalities, config)

    # Initialize panels
    for personality in personalities:
        update_panel(layout, personality, "Waiting for response...")

    async def run_all():
        with Live(layout, console=console, refresh_per_second=10) as live:
            tasks = [
                stream_personality(
                    p,
                    question,
                    previous_round,
                    config,
                    providers,
                    buffers,
                    layout,
                    live,
                    instance=instance_map[p],  # Per-provider instance number
                )
                for p in personalities
            ]
            results = await asyncio.gather(*tasks)
        return dict(results)

    responses = asyncio.run(run_all())

    # After streaming completes, print compact summary and answers
    print_round_summary(round_num, responses)
    print_answers(round_num, responses)

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

    config: Config = state["config"]
    providers: dict[str, LLMProvider] = state["providers"]

    # Get the consensus check personality config
    consensus_prompt_name = config.consensus_prompt
    
    try:
        personality_config = config.personalities[consensus_prompt_name]
        consensus_prompt_text = load_prompt(personality_config.prompt_path)
        llm = get_llm_for_personality(consensus_prompt_name, config, providers)
    except (KeyError, FileNotFoundError):
        # Fallback if personality/prompt doesn't exist
        consensus_prompt_text = """You are analyzing a multi-perspective debate. Review the responses below 
and determine if the participants have reached substantial agreement on 
the core points, even if they differ in emphasis or framing.

Respond with JSON only: {"consensus": true/false, "reasoning": "brief explanation"}"""
        # Use the first available model as fallback
        first_model = next(iter(config.models.values()))
        provider = providers[first_model.provider_type]
        llm = provider.get_llm(first_model)

    # Format responses for analysis
    response_text = "\n\n".join(
        f"**{p.replace('_', ' ').title()}**: {r}"
        for p, r in current_round.items()
    )

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
    """Produce final synthesized output from the dedicated synthesizer prompt.

    The synthesizer reviews all rounds of debate and produces a final
    integrated, dispassionate perspective.

    Args:
        state: Current debate state

    Returns:
        Updated state with final_synthesis
    """
    config: Config = state["config"]
    providers: dict[str, LLMProvider] = state["providers"]
    question = state["question"]
    rounds = state.get("rounds", [])
    consensus_reasoning = state.get("consensus_reasoning", "")

    synthesizer_prompt_name = config.synthesizer_prompt
    display_name = synthesizer_prompt_name.replace("_", " ").title()
    console.print(f"\n[bold magenta]Synthesis by {display_name}[/bold magenta]")

    # Get synthesizer personality and LLM
    try:
        personality_config = config.personalities[synthesizer_prompt_name]
        base_prompt = load_prompt(personality_config.prompt_path)
        llm = get_llm_for_personality(synthesizer_prompt_name, config, providers)
    except (KeyError, FileNotFoundError):
        base_prompt = "You are a rational, dispassionate synthesizer of multiple perspectives."
        # Use the first available model as fallback
        first_model = next(iter(config.models.values()))
        provider = providers[first_model.provider_type]
        llm = provider.get_llm(first_model)

    # Build context from all rounds
    context_parts = [f"Original Question: {question}\n"]

    for i, round_responses in enumerate(rounds, 1):
        context_parts.append(f"\n## Round {i} Responses\n")
        for personality, response in round_responses.items():
            personality_display = personality.replace("_", " ").title()
            # Truncate for context window
            truncated = response[:1500] + "..." if len(response) > 1500 else response
            context_parts.append(f"**{personality_display}**: {truncated}\n")

    context_parts.append(f"\n## Debate Status\n{consensus_reasoning}\n")
    context_parts.append(
        "\n---\n\nProvide a final integrated perspective "
        "that captures the key insights from all viewpoints and rounds of debate."
    )

    messages = [
        SystemMessage(content=base_prompt),
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
