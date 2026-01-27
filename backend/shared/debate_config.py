"""
Unified configuration models for the Prizms debate system.

This module provides Pydantic models for debate configuration that are used
by both the CLI (via YAML loading) and the API (via runtime construction).
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from providers.base import ModelConfig


class PersonalityConfig(BaseModel):
    """Configuration for a debate personality.

    Attributes:
        name: Personality identifier (e.g., "critic", "judge")
        prompt_path: Path to the prompt file
        model_name: References a model_name in the models dict
    """

    model_config = {"frozen": True}

    name: str
    prompt_path: Path
    model_name: str


class DebateSettings(BaseModel):
    """Settings for the debate process.

    Attributes:
        output_dir: Directory for saving output files
        max_rounds: Maximum number of debate rounds
        consensus_prompt: Name of the consensus check personality
        synthesizer_prompt: Name of the synthesizer personality
    """

    model_config = {"frozen": True}

    output_dir: Path = Field(default=Path("outputs"))
    max_rounds: int = Field(default=3, ge=1, le=10)
    consensus_prompt: str = "consensus_check"
    synthesizer_prompt: str = "synthesizer"


class DebateConfig(BaseModel):
    """Complete configuration for a Prizms debate.

    This model unifies CLI YAML config and API runtime config into a single
    representation that the core debate engine can use.

    Attributes:
        debate_settings: Settings for the debate process
        models: Dictionary mapping model_name to ModelConfig
        personalities: Dictionary mapping personality name to PersonalityConfig
    """

    model_config = {"frozen": True}

    debate_settings: DebateSettings
    models: dict[str, ModelConfig]
    personalities: dict[str, PersonalityConfig]

    @property
    def output_dir(self) -> Path:
        """Convenience accessor for output directory."""
        return self.debate_settings.output_dir

    @property
    def max_rounds(self) -> int:
        """Convenience accessor for max rounds."""
        return self.debate_settings.max_rounds

    @property
    def consensus_prompt(self) -> str:
        """Convenience accessor for consensus prompt name."""
        return self.debate_settings.consensus_prompt

    @property
    def synthesizer_prompt(self) -> str:
        """Convenience accessor for synthesizer prompt name."""
        return self.debate_settings.synthesizer_prompt


def load_prompt(prompt_path: Path) -> str:
    """Load a personality prompt from a file.

    Args:
        prompt_path: Path to the prompt file

    Returns:
        Contents of the prompt file
    """
    return prompt_path.read_text()


def get_debate_personalities(config: DebateConfig) -> list[str]:
    """Get list of personality names that participate in debate.

    Excludes system personalities (consensus_check, synthesizer).

    Args:
        config: The debate configuration

    Returns:
        List of personality names for debate participants
    """
    excluded = {config.consensus_prompt, config.synthesizer_prompt}
    return [name for name in config.personalities if name not in excluded]
