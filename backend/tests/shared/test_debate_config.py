"""Tests for shared/debate_config.py - Unified configuration models."""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from shared.debate_config import (
    PersonalityConfig,
    DebateSettings,
    DebateConfig,
    load_prompt,
    get_debate_personalities,
)
from providers.base import ModelConfig


class TestPersonalityConfig:
    """Tests for the PersonalityConfig Pydantic model."""

    def test_creates_personality_config(self):
        """Should create a personality config with all fields."""
        config = PersonalityConfig(
            name="critic",
            prompt_path=Path("/path/to/prompt.txt"),
            model_name="default",
        )
        assert config.name == "critic"
        assert config.prompt_path == Path("/path/to/prompt.txt")
        assert config.model_name == "default"

    def test_personality_config_is_frozen(self):
        """Should be immutable."""
        config = PersonalityConfig(
            name="critic",
            prompt_path=Path("/path/to/prompt.txt"),
            model_name="default",
        )
        with pytest.raises(Exception):  # Pydantic v2 raises ValidationError
            config.name = "judge"

    def test_personality_config_equality(self):
        """Should compare equal for same values."""
        config1 = PersonalityConfig(
            name="critic",
            prompt_path=Path("/path/to/prompt.txt"),
            model_name="default",
        )
        config2 = PersonalityConfig(
            name="critic",
            prompt_path=Path("/path/to/prompt.txt"),
            model_name="default",
        )
        assert config1 == config2


class TestDebateSettings:
    """Tests for the DebateSettings Pydantic model."""

    def test_creates_debate_settings_with_defaults(self):
        """Should create settings with default values."""
        settings = DebateSettings()
        assert settings.output_dir == Path("outputs")
        assert settings.max_rounds == 3
        assert settings.consensus_prompt == "consensus_check"
        assert settings.synthesizer_prompt == "synthesizer"

    def test_creates_debate_settings_with_custom_values(self):
        """Should accept custom values."""
        settings = DebateSettings(
            output_dir=Path("/custom/output"),
            max_rounds=5,
            consensus_prompt="custom_consensus",
            synthesizer_prompt="custom_synth",
        )
        assert settings.output_dir == Path("/custom/output")
        assert settings.max_rounds == 5
        assert settings.consensus_prompt == "custom_consensus"
        assert settings.synthesizer_prompt == "custom_synth"

    def test_max_rounds_validation(self):
        """Should validate max_rounds range."""
        # Valid range
        settings = DebateSettings(max_rounds=1)
        assert settings.max_rounds == 1

        settings = DebateSettings(max_rounds=10)
        assert settings.max_rounds == 10

        # Invalid: too low
        with pytest.raises(Exception):
            DebateSettings(max_rounds=0)

        # Invalid: too high
        with pytest.raises(Exception):
            DebateSettings(max_rounds=11)

    def test_debate_settings_is_frozen(self):
        """Should be immutable."""
        settings = DebateSettings()
        with pytest.raises(Exception):
            settings.max_rounds = 5


class TestDebateConfig:
    """Tests for the DebateConfig Pydantic model."""

    def create_test_config(self) -> DebateConfig:
        """Helper to create a test DebateConfig."""
        model_config = ModelConfig(
            model_name="default",
            provider_type="anthropic",
            model_id="claude-3-5-sonnet",
            api_key="test-key",
        )
        personality_config = PersonalityConfig(
            name="critic",
            prompt_path=Path("/prompts/critic.txt"),
            model_name="default",
        )
        consensus_config = PersonalityConfig(
            name="consensus_check",
            prompt_path=Path("/prompts/consensus_check.txt"),
            model_name="default",
        )
        synthesizer_config = PersonalityConfig(
            name="synthesizer",
            prompt_path=Path("/prompts/synthesizer.txt"),
            model_name="default",
        )
        return DebateConfig(
            debate_settings=DebateSettings(max_rounds=3),
            models={"default": model_config},
            personalities={
                "critic": personality_config,
                "consensus_check": consensus_config,
                "synthesizer": synthesizer_config,
            },
        )

    def test_creates_debate_config(self):
        """Should create a complete DebateConfig."""
        config = self.create_test_config()
        assert config.debate_settings.max_rounds == 3
        assert "default" in config.models
        assert "critic" in config.personalities

    def test_convenience_properties(self):
        """Should provide convenience accessors for nested settings."""
        config = self.create_test_config()
        assert config.output_dir == Path("outputs")
        assert config.max_rounds == 3
        assert config.consensus_prompt == "consensus_check"
        assert config.synthesizer_prompt == "synthesizer"

    def test_debate_config_is_frozen(self):
        """Should be immutable."""
        config = self.create_test_config()
        with pytest.raises(Exception):
            config.models = {}


class TestLoadPrompt:
    """Tests for the load_prompt helper function."""

    def test_loads_prompt_from_file(self, tmp_path):
        """Should read prompt content from file."""
        prompt_file = tmp_path / "test_prompt.txt"
        prompt_file.write_text("You are a helpful assistant.")

        content = load_prompt(prompt_file)
        assert content == "You are a helpful assistant."

    def test_raises_on_missing_file(self, tmp_path):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_prompt(tmp_path / "nonexistent.txt")


class TestGetDebatePersonalities:
    """Tests for the get_debate_personalities helper function."""

    def create_config_with_personalities(
        self, personality_names: list[str]
    ) -> DebateConfig:
        """Helper to create a config with specified personalities."""
        model_config = ModelConfig(
            model_name="default",
            provider_type="anthropic",
            model_id="claude-3-5-sonnet",
        )
        personalities = {}
        for name in personality_names:
            personalities[name] = PersonalityConfig(
                name=name,
                prompt_path=Path(f"/prompts/{name}.txt"),
                model_name="default",
            )
        return DebateConfig(
            debate_settings=DebateSettings(),
            models={"default": model_config},
            personalities=personalities,
        )

    def test_excludes_system_personalities(self):
        """Should exclude consensus_check and synthesizer."""
        config = self.create_config_with_personalities(
            ["critic", "judge", "consensus_check", "synthesizer"]
        )
        debate_personalities = get_debate_personalities(config)
        
        assert "critic" in debate_personalities
        assert "judge" in debate_personalities
        assert "consensus_check" not in debate_personalities
        assert "synthesizer" not in debate_personalities

    def test_returns_all_non_system_personalities(self):
        """Should return all debate personalities."""
        config = self.create_config_with_personalities(
            ["critic", "judge", "interpreter", "consensus_check", "synthesizer"]
        )
        debate_personalities = get_debate_personalities(config)
        
        assert len(debate_personalities) == 3
        assert set(debate_personalities) == {"critic", "judge", "interpreter"}

    def test_empty_when_only_system_personalities(self):
        """Should return empty list if only system personalities exist."""
        config = self.create_config_with_personalities(
            ["consensus_check", "synthesizer"]
        )
        debate_personalities = get_debate_personalities(config)
        
        assert debate_personalities == []

    def test_handles_custom_system_prompts(self):
        """Should respect custom consensus/synthesizer prompt names."""
        model_config = ModelConfig(
            model_name="default",
            provider_type="anthropic",
            model_id="claude-3-5-sonnet",
        )
        personalities = {
            "critic": PersonalityConfig(
                name="critic",
                prompt_path=Path("/prompts/critic.txt"),
                model_name="default",
            ),
            "custom_consensus": PersonalityConfig(
                name="custom_consensus",
                prompt_path=Path("/prompts/custom_consensus.txt"),
                model_name="default",
            ),
            "custom_synth": PersonalityConfig(
                name="custom_synth",
                prompt_path=Path("/prompts/custom_synth.txt"),
                model_name="default",
            ),
        }
        config = DebateConfig(
            debate_settings=DebateSettings(
                consensus_prompt="custom_consensus",
                synthesizer_prompt="custom_synth",
            ),
            models={"default": model_config},
            personalities=personalities,
        )
        
        debate_personalities = get_debate_personalities(config)
        assert debate_personalities == ["critic"]
