"""
State builder for converting API Debate models to LangGraph DebateState.

This module handles the bridging between the API's Debate model and the
LangGraph DebateState format expected by core/graph.py.
"""

from pathlib import Path
from dataclasses import dataclass

from core.graph import DebateState
from providers.base import ModelConfig, LLMProvider
from shared.config import get_settings

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


@dataclass
class APIPersonalityConfig:
    """Minimal PersonalityConfig adapter for API-based debates.
    
    Bridges the API's simple personality name to the format
    expected by core/nodes.py.
    """
    name: str
    prompt_path: Path
    model_name: str


@dataclass 
class APIDebateSettings:
    """Minimal DebateSettings adapter for API-based debates."""
    output_dir: Path
    max_rounds: int
    consensus_prompt: str = "consensus_check"
    synthesizer_prompt: str = "synthesizer"


class APIConfigAdapter:
    """
    Adapts an API Debate model to the Config interface expected by core/nodes.py.
    
    This creates a Config-like object that:
    - Maps personality names to prompt file paths
    - Creates a single model config using the debate's provider/model
    - Provides the same interface as core.config.Config
    """
    
    def __init__(self, debate: Debate, providers: dict[str, LLMProvider]):
        self.debate = debate
        self._providers = providers
        self._model_config = self._build_model_config()
        self._personalities = self._build_personalities()
        self._models = {"default": self._model_config}
        self.debate_settings = APIDebateSettings(
            output_dir=Path("/tmp/prizms"),
            max_rounds=debate.max_rounds,
        )
    
    def _build_model_config(self) -> ModelConfig:
        """Build a ModelConfig from debate settings."""
        return ModelConfig(
            model_name="default",
            provider_type=self.debate.provider,
            model_id=self.debate.model,
            api_base="",
            api_key=get_api_key_for_provider(self.debate.provider),
        )
    
    def _build_personalities(self) -> dict[str, APIPersonalityConfig]:
        """Build personality configs from debate settings."""
        personalities = {}
        
        # Add debate personalities
        for name in self.debate.settings.personalities:
            prompt_path = PROMPTS_DIR / f"{name}.txt"
            personalities[name] = APIPersonalityConfig(
                name=name,
                prompt_path=prompt_path,
                model_name="default",
            )
        
        # Add system personalities (consensus_check, synthesizer)
        for sys_name in ["consensus_check", "synthesizer"]:
            prompt_path = PROMPTS_DIR / f"{sys_name}.txt"
            personalities[sys_name] = APIPersonalityConfig(
                name=sys_name,
                prompt_path=prompt_path,
                model_name="default",
            )
        
        return personalities
    
    @property
    def personalities(self) -> dict[str, APIPersonalityConfig]:
        return self._personalities
    
    @property
    def models(self) -> dict[str, ModelConfig]:
        return self._models
    
    @property
    def output_dir(self) -> Path:
        return self.debate_settings.output_dir
    
    @property
    def max_rounds(self) -> int:
        return self.debate_settings.max_rounds
    
    @property
    def consensus_prompt(self) -> str:
        return self.debate_settings.consensus_prompt
    
    @property
    def synthesizer_prompt(self) -> str:
        return self.debate_settings.synthesizer_prompt


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
    
    config_adapter = APIConfigAdapter(debate, providers)
    
    return {
        "question": debate.question,
        "personalities": debate_personalities,
        "config": config_adapter,  # type: ignore - adapter provides same interface
        "providers": providers,
        "max_rounds": debate.max_rounds,
        "current_round": 0,
        "rounds": [],
        "consensus_reached": False,
        "consensus_reasoning": "",
        "final_synthesis": None,
    }
