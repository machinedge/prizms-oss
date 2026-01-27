"""Configuration loading and parsing for LiteLLM-style YAML configs.

DEPRECATION NOTICE:
    This module is maintained for CLI backward compatibility.
    New code should import from shared.debate_config directly.

    The dataclass-based models have been replaced with Pydantic models
    in shared/debate_config.py. This module re-exports those models
    and provides YAML loading functionality.
"""

from pathlib import Path

import yaml

from providers.base import ModelConfig

# Re-export unified Pydantic models for backward compatibility
# New code should import directly from shared.debate_config
from shared.debate_config import (
    DebateConfig,
    DebateSettings,
    PersonalityConfig,
    get_debate_personalities,
    load_prompt,
)

# Alias for CLI backward compatibility
# The CLI uses `Config` as the type name
Config = DebateConfig


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


def load_config(config_path: Path) -> DebateConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Parsed DebateConfig object (aliased as Config for backward compatibility)

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

    return DebateConfig(
        debate_settings=debate_settings,
        models=models,
        personalities=personalities,
    )
