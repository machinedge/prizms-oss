"""
State builder for converting API Debate models to LangGraph DebateState.

This module handles the bridging between the API's Debate model and the
LangGraph DebateState format expected by core/graph.py.
"""

from pathlib import Path

from core.graph import DebateState
from providers.base import ModelConfig, LLMProvider
from shared.config import get_settings
from shared.debate_config import DebateConfig, DebateSettings, PersonalityConfig

from .models import Debate, SYSTEM_PERSONALITIES


# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def get_api_key_for_provider(provider: str) -> str:
    """Get the API key for a provider from settings."""
    settings = get_settings()
    api_key_map = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.google_api_key,
        "grok": settings.xai_api_key,
        "openrouter": settings.openrouter_api_key,
        # Local providers don't need API keys
        "ollama": "",
        "vllm": "",
        "lm_studio": "",
    }
    return api_key_map.get(provider, "")


def build_debate_config(debate: Debate) -> DebateConfig:
    """
    Build a DebateConfig from an API Debate model.
    
    This creates the unified config format expected by the core debate engine.
    
    Args:
        debate: The API Debate model
        
    Returns:
        DebateConfig ready for use by core/nodes.py
    """
    # Create the single model config for this debate
    model_config = ModelConfig(
        model_name="default",
        provider_type=debate.provider,
        model_id=debate.model,
        api_base="",
        api_key=get_api_key_for_provider(debate.provider),
    )
    
    # Build personality configs for all personalities
    personalities: dict[str, PersonalityConfig] = {}
    
    # Add debate personalities
    for name in debate.settings.personalities:
        prompt_path = PROMPTS_DIR / f"{name}.txt"
        personalities[name] = PersonalityConfig(
            name=name,
            prompt_path=prompt_path,
            model_name="default",
        )
    
    # Add system personalities (consensus_check, synthesizer)
    for sys_name in ["consensus_check", "synthesizer"]:
        if sys_name not in personalities:
            prompt_path = PROMPTS_DIR / f"{sys_name}.txt"
            personalities[sys_name] = PersonalityConfig(
                name=sys_name,
                prompt_path=prompt_path,
                model_name="default",
            )
    
    # Create debate settings
    debate_settings = DebateSettings(
        output_dir=Path("/tmp/prizms"),
        max_rounds=debate.max_rounds,
    )
    
    return DebateConfig(
        debate_settings=debate_settings,
        models={"default": model_config},
        personalities=personalities,
    )


def build_initial_state(
    debate: Debate,
    providers: dict[str, LLMProvider],
) -> DebateState:
    """
    Convert API Debate model to LangGraph DebateState.
    
    Args:
        debate: The API Debate model
        providers: Dictionary of available LLM providers
        
    Returns:
        DebateState ready for LangGraph execution
    """
    # Filter out system personalities from debate participants
    debate_personalities = [
        p for p in debate.settings.personalities
        if p not in SYSTEM_PERSONALITIES
    ]
    
    config = build_debate_config(debate)
    
    return {
        "question": debate.question,
        "personalities": debate_personalities,
        "config": config,
        "providers": providers,
        "max_rounds": debate.max_rounds,
        "current_round": 0,
        "rounds": [],
        "consensus_reached": False,
        "consensus_reasoning": "",
        "final_synthesis": None,
    }
