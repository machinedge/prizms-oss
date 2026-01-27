"""Tests for state_builder module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

from modules.debates.state_builder import (
    get_api_key_for_provider,
    build_debate_config,
    build_initial_state,
    PROMPTS_DIR,
)
from modules.debates.models import (
    Debate,
    DebateStatus,
    DebateSettings,
)
from shared.debate_config import DebateConfig


def create_mock_debate(
    debate_id: str = "debate-123",
    user_id: str = "user-123",
    question: str = "What is the meaning of life?",
    status: DebateStatus = DebateStatus.PENDING,
    max_rounds: int = 2,
    personalities: list[str] | None = None,
) -> Debate:
    """Helper to create a mock debate for testing."""
    now = datetime.now(timezone.utc)
    return Debate(
        id=debate_id,
        user_id=user_id,
        question=question,
        status=status,
        provider="anthropic",
        model="claude-sonnet-4-5",
        settings=DebateSettings(
            max_rounds=max_rounds,
            personalities=personalities or ["critic", "interpreter"],
            include_synthesis=True,
        ),
        max_rounds=max_rounds,
        current_round=0,
        created_at=now,
        updated_at=now,
    )


class TestGetApiKeyForProvider:
    """Tests for the get_api_key_for_provider helper function."""

    @patch("modules.debates.state_builder.get_settings")
    def test_gets_anthropic_key(self, mock_settings):
        """Should return Anthropic API key."""
        mock_settings.return_value.anthropic_api_key = "test-anthropic-key"
        assert get_api_key_for_provider("anthropic") == "test-anthropic-key"

    @patch("modules.debates.state_builder.get_settings")
    def test_gets_openai_key(self, mock_settings):
        """Should return OpenAI API key."""
        mock_settings.return_value.openai_api_key = "test-openai-key"
        assert get_api_key_for_provider("openai") == "test-openai-key"

    @patch("modules.debates.state_builder.get_settings")
    def test_gets_gemini_key(self, mock_settings):
        """Should return Gemini API key."""
        mock_settings.return_value.google_api_key = "test-gemini-key"
        assert get_api_key_for_provider("gemini") == "test-gemini-key"

    @patch("modules.debates.state_builder.get_settings")
    def test_gets_grok_key(self, mock_settings):
        """Should return Grok API key."""
        mock_settings.return_value.xai_api_key = "test-grok-key"
        assert get_api_key_for_provider("grok") == "test-grok-key"

    @patch("modules.debates.state_builder.get_settings")
    def test_gets_openrouter_key(self, mock_settings):
        """Should return OpenRouter API key."""
        mock_settings.return_value.openrouter_api_key = "test-openrouter-key"
        assert get_api_key_for_provider("openrouter") == "test-openrouter-key"

    def test_returns_empty_for_local_providers(self):
        """Should return empty string for local providers."""
        assert get_api_key_for_provider("ollama") == ""
        assert get_api_key_for_provider("vllm") == ""
        assert get_api_key_for_provider("lm_studio") == ""

    def test_returns_empty_for_unknown_provider(self):
        """Should return empty string for unknown providers."""
        assert get_api_key_for_provider("unknown_provider") == ""


class TestBuildDebateConfig:
    """Tests for the build_debate_config function."""

    def test_builds_model_config(self):
        """Should build a ModelConfig from debate settings."""
        debate = create_mock_debate()
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value="test-key"):
            config = build_debate_config(debate)
        
        assert isinstance(config, DebateConfig)
        assert "default" in config.models
        assert config.models["default"].provider_type == "anthropic"
        assert config.models["default"].model_id == "claude-sonnet-4-5"
        assert config.models["default"].api_key == "test-key"

    def test_builds_personality_configs(self):
        """Should build personality configs for all personalities."""
        debate = create_mock_debate(personalities=["critic", "interpreter"])
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            config = build_debate_config(debate)
        
        # User personalities
        assert "critic" in config.personalities
        assert "interpreter" in config.personalities
        # System personalities should also be present
        assert "consensus_check" in config.personalities
        assert "synthesizer" in config.personalities

    def test_personality_config_has_correct_prompt_path(self):
        """Should set correct prompt path for each personality."""
        debate = create_mock_debate(personalities=["critic"])
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            config = build_debate_config(debate)
        
        critic_config = config.personalities["critic"]
        assert critic_config.prompt_path == PROMPTS_DIR / "critic.txt"
        assert critic_config.model_name == "default"

    def test_provides_config_properties(self):
        """Should provide config-like properties."""
        debate = create_mock_debate(max_rounds=3)
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            config = build_debate_config(debate)
        
        assert config.max_rounds == 3
        assert config.consensus_prompt == "consensus_check"
        assert config.synthesizer_prompt == "synthesizer"
        assert config.output_dir == Path("/tmp/prizms")

    def test_returns_frozen_config(self):
        """Should return an immutable DebateConfig."""
        debate = create_mock_debate()
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            config = build_debate_config(debate)
        
        # DebateConfig is frozen - should raise on mutation
        with pytest.raises(Exception):
            config.models = {}


class TestBuildInitialState:
    """Tests for the build_initial_state function."""

    def test_builds_initial_state(self):
        """Should build initial state from debate."""
        debate = create_mock_debate(
            question="Test question?",
            max_rounds=3,
            personalities=["critic", "interpreter"],
        )
        providers = {"anthropic": MagicMock()}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            state = build_initial_state(debate, providers)
        
        assert state["question"] == "Test question?"
        assert state["max_rounds"] == 3
        assert state["current_round"] == 0
        assert state["rounds"] == []
        assert state["consensus_reached"] is False
        assert state["consensus_reasoning"] == ""
        assert state["final_synthesis"] is None
        assert state["providers"] == providers

    def test_filters_out_system_personalities(self):
        """Should filter out system personalities from debate participants."""
        debate = create_mock_debate(
            personalities=["critic", "consensus_check", "synthesizer"],
        )
        providers = {}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            state = build_initial_state(debate, providers)
        
        # Only non-system personalities should be in the state
        assert "critic" in state["personalities"]
        assert "consensus_check" not in state["personalities"]
        assert "synthesizer" not in state["personalities"]

    def test_creates_debate_config(self):
        """Should create a DebateConfig for the state."""
        debate = create_mock_debate()
        providers = {}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            state = build_initial_state(debate, providers)
        
        config = state["config"]
        assert isinstance(config, DebateConfig)
        # Verify the config has the expected values
        assert config.max_rounds == debate.max_rounds
        assert "critic" in config.personalities
        assert "default" in config.models
