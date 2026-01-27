"""Node functions for the debate graph.

These nodes use LangGraph's streaming system:
- LLM tokens stream automatically via stream_mode="messages"
- Custom events (round_started, personality_completed, etc.) via get_stream_writer()

Usage tracking is handled via LangChain callbacks that capture actual token
counts from LLM API responses when available.
"""

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.config import get_stream_writer

from modules.usage.callback import StreamingUsageTracker, UsageTrackingCallback
from providers.base import LLMProvider, ModelConfig
from shared.debate_config import DebateConfig, PersonalityConfig, load_prompt

from .models import ConsensusResult

logger = logging.getLogger(__name__)

# Type alias for backward compatibility
Config = DebateConfig


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
    usage_results: dict[str, dict[str, int]],
    instance: int | None = None,
) -> tuple[str, str]:
    """Stream LLM response for a personality.

    LLM tokens are automatically streamed via LangGraph's stream_mode="messages".
    This function accumulates the full response for state updates and captures
    usage metadata via callbacks.

    Args:
        personality_name: Name of the personality
        question: The original question
        previous_round: Previous round responses (None for first round)
        config: Full configuration object
        providers: Dictionary of provider instances by type
        buffers: Shared dict for accumulating streamed content
        usage_results: Shared dict for storing usage metadata per personality
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
    
    # Create usage tracker for this LLM call
    usage_tracker = StreamingUsageTracker()

    # Stream via LangChain with callback for usage tracking
    config_dict = {"callbacks": [usage_tracker.callback]}
    async for chunk in llm.astream(messages, config=config_dict):
        if chunk.content:
            buffers[personality_name] += chunk.content
        # Process chunk for usage metadata (typically on final chunk)
        usage_tracker.process_chunk(chunk)

    # Store usage metadata for this personality
    input_tokens, output_tokens = usage_tracker.get_usage()
    if input_tokens > 0 or output_tokens > 0:
        usage_results[personality_name] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        logger.debug(
            f"Captured usage for {personality_name}: "
            f"input={input_tokens}, output={output_tokens}"
        )
    else:
        # No usage metadata from API - will fall back to estimation
        usage_results[personality_name] = {}

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


async def debate_round(state: dict) -> dict:
    """Execute one round of debate with all personalities responding in parallel.

    This node runs all personalities concurrently. LLM tokens are automatically
    streamed via LangGraph's stream_mode="messages". Custom events are emitted
    via get_stream_writer() for SSE streaming.

    Usage metadata from LLM API responses is captured and included in
    personality_completed events.

    Args:
        state: Current debate state

    Returns:
        Updated state with new round appended and current_round incremented
    """
    writer = get_stream_writer()
    
    personalities = state["personalities"]
    question = state["question"]
    config: Config = state["config"]
    providers: dict[str, LLMProvider] = state["providers"]
    current_round = state.get("current_round", 0)

    # Get previous round if exists
    rounds = state.get("rounds", [])
    previous_round = rounds[-1] if rounds else None

    round_num = current_round + 1
    
    # Emit round_started custom event for SSE
    writer({
        "type": "round_started",
        "round_number": round_num,
        "personalities": personalities,
    })

    buffers: dict[str, str] = {}
    usage_results: dict[str, dict[str, int]] = {}

    # Compute per-provider instance numbers for LM Studio parallel execution
    instance_map = _compute_provider_instances(personalities, config)

    # Emit personality_started events and run all concurrently
    for personality in personalities:
        writer({
            "type": "personality_started",
            "round_number": round_num,
            "personality": personality,
        })

    # Run all personalities in parallel
    tasks = [
        stream_personality(
            p,
            question,
            previous_round,
            config,
            providers,
            buffers,
            usage_results,
            instance=instance_map[p],
        )
        for p in personalities
    ]
    results = await asyncio.gather(*tasks)
    responses = dict(results)

    # Emit personality_completed events with usage metadata
    for personality, response in responses.items():
        event_data = {
            "type": "personality_completed",
            "round_number": round_num,
            "personality": personality,
            "response_length": len(response),
        }
        # Include usage metadata if captured from LLM API
        if personality in usage_results and usage_results[personality]:
            event_data["usage_metadata"] = usage_results[personality]
        writer(event_data)

    # Emit round_completed custom event
    writer({
        "type": "round_completed",
        "round_number": round_num,
        "response_count": len(responses),
    })

    return {
        "rounds": [responses],  # Will be appended via operator.add
        "current_round": round_num,
    }


async def check_consensus(state: dict) -> dict:
    """Check if personalities have reached consensus.

    Uses a neutral LLM call to analyze the latest round of responses
    and determine if substantial agreement has been reached.

    Args:
        state: Current debate state

    Returns:
        Updated state with consensus_reached and consensus_reasoning
    """
    writer = get_stream_writer()
    
    rounds = state.get("rounds", [])
    if not rounds:
        return {"consensus_reached": False, "consensus_reasoning": "No responses yet"}

    current_round = rounds[-1]
    current_round_num = state.get("current_round", 1)

    # Skip consensus check on first round - always do at least 2 rounds
    if current_round_num < 2:
        writer({
            "type": "consensus_check",
            "round_number": current_round_num,
            "skipped": True,
            "reason": "First round - continuing debate",
        })
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

    # Create parser for structured output
    parser = JsonOutputParser(pydantic_object=ConsensusResult)
    format_instructions = parser.get_format_instructions()

    # Format responses for analysis
    response_text = "\n\n".join(
        f"**{p.replace('_', ' ').title()}**: {r}"
        for p, r in current_round.items()
    )

    # Build message with format instructions appended
    user_content = (
        f"Analyze these responses for consensus:\n\n{response_text}\n\n"
        f"{format_instructions}"
    )

    messages = [
        SystemMessage(content=consensus_prompt_text),
        HumanMessage(content=user_content),
    ]

    writer({
        "type": "consensus_check",
        "round_number": current_round_num,
        "checking": True,
    })

    # Async invoke for consensus check with usage tracking callback
    usage_callback = UsageTrackingCallback()
    config_dict = {"callbacks": [usage_callback]}
    response = await llm.ainvoke(messages, config=config_dict)
    content = response.content
    
    # Capture usage metadata from callback
    input_tokens, output_tokens = usage_callback.get_usage()
    usage_metadata = None
    if input_tokens > 0 or output_tokens > 0:
        usage_metadata = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        logger.debug(
            f"Captured consensus check usage: "
            f"input={input_tokens}, output={output_tokens}"
        )

    # Parse JSON response using LangChain's JsonOutputParser
    # Raises OutputParserException on parse failure, which propagates to stream adapter
    parsed_dict = parser.parse(content)
    
    # Validate with Pydantic model to ensure proper types
    # Raises ValidationError if fields are missing or wrong type
    validated_result = ConsensusResult(**parsed_dict)
    consensus = validated_result.consensus
    reasoning = validated_result.reasoning

    consensus_result_event = {
        "type": "consensus_result",
        "round_number": current_round_num,
        "consensus_reached": consensus,
        "reasoning": reasoning,
    }
    if usage_metadata:
        consensus_result_event["usage_metadata"] = usage_metadata
    writer(consensus_result_event)

    return {
        "consensus_reached": consensus,
        "consensus_reasoning": reasoning,
    }


async def synthesize(state: dict) -> dict:
    """Produce final synthesized output from the dedicated synthesizer prompt.

    The synthesizer reviews all rounds of debate and produces a final
    integrated, dispassionate perspective. LLM tokens are automatically
    streamed via stream_mode="messages".

    Args:
        state: Current debate state

    Returns:
        Updated state with final_synthesis
    """
    writer = get_stream_writer()
    
    config: Config = state["config"]
    providers: dict[str, LLMProvider] = state["providers"]
    question = state["question"]
    rounds = state.get("rounds", [])
    consensus_reasoning = state.get("consensus_reasoning", "")

    synthesizer_prompt_name = config.synthesizer_prompt
    
    writer({
        "type": "synthesis_started",
        "synthesizer": synthesizer_prompt_name,
        "total_rounds": len(rounds),
    })

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

    # Stream the synthesis with usage tracking
    usage_tracker = StreamingUsageTracker()
    config_dict = {"callbacks": [usage_tracker.callback]}
    
    full_response = ""
    async for chunk in llm.astream(messages, config=config_dict):
        if chunk.content:
            full_response += chunk.content
        usage_tracker.process_chunk(chunk)

    # Capture usage metadata
    input_tokens, output_tokens = usage_tracker.get_usage()
    usage_metadata = None
    if input_tokens > 0 or output_tokens > 0:
        usage_metadata = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        logger.debug(
            f"Captured synthesis usage: "
            f"input={input_tokens}, output={output_tokens}"
        )

    synthesis_event = {
        "type": "synthesis_completed",
        "content_length": len(full_response),
    }
    if usage_metadata:
        synthesis_event["usage_metadata"] = usage_metadata
    writer(synthesis_event)

    return {"final_synthesis": full_response}
