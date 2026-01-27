"""Tests for DebateStreamAdapter with LangGraph integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from modules.debates.stream_adapter import DebateStreamAdapter
from modules.debates.state_builder import APIConfigAdapter, get_api_key_for_provider
from modules.debates.models import (
    Debate,
    DebateEvent,
    DebateEventType,
    DebateStatus,
    DebateSettings,
    PersonalityResponse,
)


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
        mock_settings.return_value.anthropic_api_key = "test-key"
        assert get_api_key_for_provider("anthropic") == "test-key"

    @patch("modules.debates.state_builder.get_settings")
    def test_returns_empty_for_local_provider(self, mock_settings):
        """Should return empty string for local providers."""
        assert get_api_key_for_provider("ollama") == ""
        assert get_api_key_for_provider("vllm") == ""
        assert get_api_key_for_provider("lm_studio") == ""


class TestAPIConfigAdapter:
    """Tests for the APIConfigAdapter class."""

    def test_builds_model_config(self):
        """Should build a ModelConfig from debate settings."""
        debate = create_mock_debate()
        providers = {}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value="test-key"):
            adapter = APIConfigAdapter(debate, providers)
        
        assert "default" in adapter.models
        assert adapter.models["default"].provider_type == "anthropic"
        assert adapter.models["default"].model_id == "claude-sonnet-4-5"

    def test_builds_personality_configs(self):
        """Should build personality configs for all personalities."""
        debate = create_mock_debate(personalities=["critic", "interpreter"])
        providers = {}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            adapter = APIConfigAdapter(debate, providers)
        
        assert "critic" in adapter.personalities
        assert "interpreter" in adapter.personalities
        # System personalities should also be present
        assert "consensus_check" in adapter.personalities
        assert "synthesizer" in adapter.personalities

    def test_provides_config_properties(self):
        """Should provide config-like properties."""
        debate = create_mock_debate(max_rounds=3)
        providers = {}
        
        with patch("modules.debates.state_builder.get_api_key_for_provider", return_value=""):
            adapter = APIConfigAdapter(debate, providers)
        
        assert adapter.max_rounds == 3
        assert adapter.consensus_prompt == "consensus_check"
        assert adapter.synthesizer_prompt == "synthesizer"


class TestDebateStreamAdapter:
    """Tests for the DebateStreamAdapter class."""

    @pytest.fixture
    def mock_debate(self):
        """Create a mock debate."""
        return create_mock_debate()

    @pytest.fixture
    def mock_service(self):
        """Create a mock debate service."""
        service = AsyncMock()
        service.update_debate_status = AsyncMock()
        service.update_debate_totals = AsyncMock()
        service.save_round = AsyncMock(return_value="round-123")
        service.save_response = AsyncMock(return_value="response-123")
        service.save_synthesis = AsyncMock(return_value="synthesis-123")
        return service

    @pytest.fixture
    def mock_usage_service(self):
        """Create a mock usage service."""
        mock = MagicMock()
        mock.record_usage = AsyncMock(
            return_value=MagicMock(
                input_tokens=100,
                output_tokens=200,
                cost=Decimal("0.001"),
            )
        )
        return mock

    @pytest.fixture
    def mock_graph(self):
        """Create a mock LangGraph that yields expected events."""
        
        async def mock_astream(*args, **kwargs):
            """Simulate LangGraph streaming with multiple modes."""
            # Simulate round 1
            yield ("custom", {"type": "round_started", "round_number": 1, "personalities": ["critic"]})
            yield ("custom", {"type": "personality_started", "round_number": 1, "personality": "critic"})
            yield ("messages", (MagicMock(content="Hello"), {"langgraph_node": "debate_round"}))
            yield ("messages", (MagicMock(content=" world!"), {"langgraph_node": "debate_round"}))
            yield ("custom", {"type": "personality_completed", "round_number": 1, "personality": "critic"})
            yield ("custom", {"type": "round_completed", "round_number": 1})
            
            # Simulate consensus check
            yield ("custom", {"type": "consensus_check", "round_number": 1, "checking": True})
            yield ("custom", {"type": "consensus_result", "consensus_reached": True, "reasoning": "Agreement reached"})
            
            # Simulate synthesis
            yield ("custom", {"type": "synthesis_started", "synthesizer": "synthesizer"})
            yield ("messages", (MagicMock(content="Final synthesis content"), {"langgraph_node": "synthesize"}))
            yield ("custom", {"type": "synthesis_completed", "content_length": 20})
            
            # Final state update
            yield ("updates", {"synthesize": {"final_synthesis": "Final synthesis content"}})

        mock = MagicMock()
        mock.astream = mock_astream
        return mock

    @pytest.mark.asyncio
    async def test_emits_debate_started_event(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit debate_started as first event."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)
                if event.type == DebateEventType.DEBATE_STARTED:
                    break

            assert len(events) >= 1
            assert events[0].type == DebateEventType.DEBATE_STARTED
            assert events[0].debate_id == "debate-123"

    @pytest.mark.asyncio
    async def test_emits_round_events(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit round_started and round_completed events."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            event_types = [e.type for e in events]
            assert DebateEventType.ROUND_STARTED in event_types
            assert DebateEventType.ROUND_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_emits_personality_events(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit personality_started and personality_completed events."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            event_types = [e.type for e in events]
            assert DebateEventType.PERSONALITY_STARTED in event_types
            assert DebateEventType.PERSONALITY_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_emits_answer_chunks(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit answer_chunk events from LangGraph messages stream."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            chunk_events = [
                e for e in events if e.type == DebateEventType.ANSWER_CHUNK
            ]
            assert len(chunk_events) > 0

    @pytest.mark.asyncio
    async def test_emits_synthesis_events(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit synthesis events from LangGraph custom stream."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            event_types = [e.type for e in events]
            assert DebateEventType.SYNTHESIS_STARTED in event_types
            assert DebateEventType.SYNTHESIS_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_emits_cost_update_events(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit cost_update events after personality completion."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            cost_events = [
                e for e in events if e.type == DebateEventType.COST_UPDATE
            ]
            assert len(cost_events) > 0

    @pytest.mark.asyncio
    async def test_emits_debate_completed_on_success(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should emit debate_completed event on success."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            assert events[-1].type == DebateEventType.DEBATE_COMPLETED
            assert events[-1].cost is not None

    @pytest.mark.asyncio
    async def test_emits_debate_failed_on_error(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
    ):
        """Should emit debate_failed event on error."""

        async def failing_astream(*args, **kwargs):
            raise ValueError("Test error")
            yield  # Make it a generator

        mock_graph = MagicMock()
        mock_graph.astream = failing_astream

        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = []
            async for event in adapter.run():
                events.append(event)

            assert events[-1].type == DebateEventType.DEBATE_FAILED
            assert "Test error" in events[-1].error

    @pytest.mark.asyncio
    async def test_records_usage_after_personality_completion(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should call UsageService.record_usage() after each personality."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = [e async for e in adapter.run()]

            # Should have called record_usage for personality + synthesis
            assert mock_usage_service.record_usage.call_count >= 1

    @pytest.mark.asyncio
    async def test_persists_rounds_to_database(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should call save_round when round starts."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = [e async for e in adapter.run()]

            # Should have called save_round at least once
            assert mock_service.save_round.call_count >= 1

    @pytest.mark.asyncio
    async def test_persists_responses_to_database(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should call save_response for each personality completion."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = [e async for e in adapter.run()]

            # Should have called save_response at least once
            assert mock_service.save_response.call_count >= 1

    @pytest.mark.asyncio
    async def test_persists_synthesis_to_database(
        self,
        mock_debate,
        mock_service,
        mock_usage_service,
        mock_graph,
    ):
        """Should call save_synthesis when synthesis completes."""
        with patch(
            "modules.debates.usage_tracker.get_usage_service",
            return_value=mock_usage_service,
        ), patch(
            "modules.debates.stream_adapter.get_providers",
            return_value={},
        ), patch(
            "modules.debates.stream_adapter.build_graph",
            return_value=mock_graph,
        ), patch(
            "modules.debates.state_builder.get_settings",
        ):
            adapter = DebateStreamAdapter(
                debate=mock_debate,
                user_id="user-123",
                debate_service=mock_service,
            )

            events = [e async for e in adapter.run()]

            # Should have called save_synthesis once
            mock_service.save_synthesis.assert_called_once()
