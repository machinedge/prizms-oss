"""Configuration loading and parsing for LiteLLM-style YAML configs."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from providers.base import ModelConfig


@dataclass
class PersonalityConfig:
    """Configuration for a debate personality.

    Attributes:
        name: Personality identifier (e.g., "critic", "judge")
        prompt_path: Path to the prompt file
        model_name: References a model_name in the models dict
    """

    name: str
    prompt_path: Path
    model_name: str


@dataclass
class DebateSettings:
    """Settings for the debate process.

    Attributes:
        output_dir: Directory for saving output files
        max_rounds: Maximum number of debate rounds
        consensus_prompt: Name of the consensus check personality
        synthesizer_prompt: Name of the synthesizer personality
    """

    output_dir: Path
    max_rounds: int
    consensus_prompt: str
    synthesizer_prompt: str


@dataclass
class Config:
    """Complete configuration for the Prizms debate system.

    Attributes:
        debate_settings: Settings for the debate process
        models: Dictionary mapping model_name to ModelConfig
        personalities: Dictionary mapping personality name to PersonalityConfig
    """

    debate_settings: DebateSettings
    models: dict[str, ModelConfig]
    personalities: dict[str, PersonalityConfig]

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


def _parse_model_list(
    model_list: list[dict], config_dir: Path
) -> dict[str, ModelConfig]:
    """Parse model_list from YAML into ModelConfig dict.

    Args:
        model_list: List of model entries from YAML
        config_dir: Directory containing the config file (for relative paths)

    Returns:
        Dictionary mapping model_name to ModelConfig

    Raises:
        ValueError: If a model entry is missing the required 'provider' field
    """
    models = {}
    for entry in model_list:
        model_name = entry["model_name"]
        params = entry.get("litellm_params", {})

        # Provider is now an explicit field (required)
        provider_type = params.get("provider")
        if not provider_type:
            raise ValueError(
                f"Model '{model_name}' is missing required 'provider' field in litellm_params. "
                f"Valid providers: ollama, vllm, lm_studio"
            )

        # Model ID is the full model identifier (e.g., "qwen/qwen3-4B-Thinking-2507")
        model_id = params.get("model", "")

        models[model_name] = ModelConfig(
            model_name=model_name,
            provider_type=provider_type,
            model_id=model_id,
            api_base=params.get("api_base", ""),
            api_key=params.get("api_key", ""),
        )
    return models


def _parse_personalities(
    personalities_list: list[dict], config_dir: Path
) -> dict[str, PersonalityConfig]:
    """Parse personalities from YAML into PersonalityConfig dict.

    Args:
        personalities_list: List of personality entries from YAML
        config_dir: Directory containing the config file (for relative paths)

    Returns:
        Dictionary mapping personality name to PersonalityConfig
    """
    personalities = {}
    for entry in personalities_list:
        name = entry["name"]
        prompt_path = entry.get("prompt", "")

        # Resolve relative paths against config directory
        if prompt_path:
            prompt_path = config_dir / prompt_path
        else:
            prompt_path = config_dir / "prompts" / f"{name}.txt"

        personalities[name] = PersonalityConfig(
            name=name,
            prompt_path=prompt_path,
            model_name=entry.get("model_name", ""),
        )
    return personalities


def load_config(config_path: Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Parsed Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        KeyError: If required config keys are missing
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)

    config_dir = config_path.parent

    # Parse debate settings
    settings_data = data.get("debate_settings", {})
    output_dir = settings_data.get("output_dir", "outputs")
    if not Path(output_dir).is_absolute():
        output_dir = config_dir / output_dir

    debate_settings = DebateSettings(
        output_dir=Path(output_dir),
        max_rounds=settings_data.get("max_rounds", 3),
        consensus_prompt=settings_data.get("consensus_prompt", "consensus_check"),
        synthesizer_prompt=settings_data.get("synthesizer_prompt", "synthesizer"),
    )

    # Parse model_list
    model_list = data.get("model_list", [])
    models = _parse_model_list(model_list, config_dir)

    # Parse personalities
    personalities_list = data.get("personalities", [])
    personalities = _parse_personalities(personalities_list, config_dir)

    return Config(
        debate_settings=debate_settings,
        models=models,
        personalities=personalities,
    )


def load_prompt(prompt_path: Path) -> str:
    """Load a personality prompt from a file.

    Args:
        prompt_path: Path to the prompt file

    Returns:
        Contents of the prompt file
    """
    return prompt_path.read_text()


def get_debate_personalities(config: Config) -> list[str]:
    """Get list of personality names that participate in debate.

    Excludes system personalities (consensus_check, synthesizer).

    Args:
        config: The loaded configuration

    Returns:
        List of personality names for debate participants
    """
    excluded = {config.consensus_prompt, config.synthesizer_prompt}
    return [name for name in config.personalities if name not in excluded]
