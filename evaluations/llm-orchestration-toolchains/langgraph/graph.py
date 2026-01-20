"""LangGraph state and graph definition for multi-round debate."""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph


class DebateState(TypedDict):
    """State managed across the debate graph execution."""

    question: str
    personalities: list[str]  # Dynamic list of N personalities
    personalities_dir: str  # Path to personality prompts
    max_rounds: int  # Safety limit
    current_round: int  # Counter
    rounds: Annotated[list[dict[str, str]], operator.add]  # Append-only history
    consensus_reached: bool
    consensus_reasoning: str  # Explanation from consensus check
    consensus_prompt: str  # Name of the consensus check prompt file
    synthesizer_prompt: str  # Name of the synthesizer prompt file
    final_synthesis: str | None


def should_continue(state: DebateState) -> str:
    """Determine whether to continue debating or synthesize.

    Returns:
        "synthesize" if consensus reached or max rounds hit
        "debate_round" to continue debating
    """
    if state["consensus_reached"]:
        return "synthesize"
    if state["current_round"] >= state["max_rounds"]:
        return "synthesize"  # Force synthesis at limit
    return "debate_round"


def build_graph() -> StateGraph:
    """Build and return the compiled debate graph.

    Graph structure:
        debate_round -> check_consensus -> [synthesize | debate_round]
        synthesize -> END
    """
    from nodes import check_consensus, debate_round, synthesize

    graph = StateGraph(DebateState)

    # Add nodes
    graph.add_node("debate_round", debate_round)
    graph.add_node("check_consensus", check_consensus)
    graph.add_node("synthesize", synthesize)

    # Set entry point
    graph.set_entry_point("debate_round")

    # Add edges
    graph.add_edge("debate_round", "check_consensus")
    graph.add_conditional_edges(
        "check_consensus",
        should_continue,
        {
            "synthesize": "synthesize",
            "debate_round": "debate_round",
        },
    )
    graph.add_edge("synthesize", END)

    return graph.compile()
