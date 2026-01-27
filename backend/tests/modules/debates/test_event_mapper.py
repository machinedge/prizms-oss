"""Tests for event_mapper module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from modules.debates.event_mapper import EventMapper
from modules.debates.models import DebateEventType
from modules.debates.usage_tracker import UsageTracker


class TestEventMapper:
    """Tests for the EventMapper class."""

    @pytest.fixture
    def mock_debate_service(self):
        """Create a mock debate service."""
        service = AsyncMock()
        service.save_round = AsyncMock(return_value="round-123")
        service.save_response = AsyncMock(return_value="response-123")
        service.save_synthesis = AsyncMock(return_value="synthesis-123")
        service.update_debate_status = AsyncMock()
        return service

    @pytest.fixture
    def mock_usage_tracker(self):
        """Create a mock usage tracker."""
        tracker = MagicMock(spec=UsageTracker)
        tracker.record_personality_usage = AsyncMock(
            return_value=MagicMock(
                input_tokens=100,
                output_tokens=200,
                cost=Decimal("0.001"),
            )
        )
        tracker.record_synthesis_usage = AsyncMock(
            return_value=MagicMock(
                input_tokens=500,
                output_tokens=100,
                cost=Decimal("0.002"),
            )
        )
        tracker.total_cost = Decimal("0.001")
        return tracker

    @pytest.fixture
    def event_mapper(self, mock_debate_service, mock_usage_tracker):
        """Create an EventMapper instance."""
        return EventMapper(
            debate_id="debate-123",
            question="What is the meaning of life?",
            debate_service=mock_debate_service,
            usage_tracker=mock_usage_tracker,
        )

    def test_initialization(self, event_mapper):
        """Should initialize with correct state."""
        assert event_mapper.debate_id == "debate-123"
        assert event_mapper.question == "What is the meaning of life?"
        assert event_mapper.current_round_num == 0
        assert event_mapper.current_round_id is None
        assert event_mapper.round_responses == []
        assert event_mapper.streaming_buffers == {}
        assert event_mapper.current_personality is None

    @pytest.mark.asyncio
    async def test_handles_messages_mode(self, event_mapper):
        """Should handle messages mode and emit answer chunks."""
        mock_chunk = MagicMock(content="Hello world")
        event_mapper.current_personality = "critic"
        
        events = []
        async for event in event_mapper.map_event(
            "messages", (mock_chunk, {"langgraph_node": "debate_round"})
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.ANSWER_CHUNK
        assert events[0].content == "Hello world"
        assert events[0].debate_id == "debate-123"

    @pytest.mark.asyncio
    async def test_accumulates_content_in_buffer(self, event_mapper):
        """Should accumulate content in streaming buffer."""
        event_mapper.current_personality = "critic"
        
        mock_chunk1 = MagicMock(content="Hello ")
        mock_chunk2 = MagicMock(content="world!")
        
        async for _ in event_mapper.map_event(
            "messages", (mock_chunk1, {})
        ):
            pass
        async for _ in event_mapper.map_event(
            "messages", (mock_chunk2, {})
        ):
            pass
        
        assert event_mapper.streaming_buffers["critic"] == "Hello world!"

    @pytest.mark.asyncio
    async def test_handles_round_started(self, event_mapper, mock_debate_service):
        """Should handle round_started custom event."""
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "round_started", "round_number": 1}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.ROUND_STARTED
        assert events[0].round_number == 1
        assert event_mapper.current_round_num == 1
        mock_debate_service.save_round.assert_called_once_with(
            debate_id="debate-123",
            round_number=1,
        )

    @pytest.mark.asyncio
    async def test_handles_personality_started(self, event_mapper):
        """Should handle personality_started custom event."""
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "personality_started", "personality": "critic"}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.PERSONALITY_STARTED
        assert events[0].personality == "critic"
        assert event_mapper.current_personality == "critic"
        assert event_mapper.streaming_buffers["critic"] == ""

    @pytest.mark.asyncio
    async def test_handles_personality_completed(
        self, event_mapper, mock_debate_service, mock_usage_tracker
    ):
        """Should handle personality_completed custom event."""
        # Setup: simulate streaming content
        event_mapper.current_round_id = "round-123"
        event_mapper.streaming_buffers["critic"] = "This is the response content."
        
        events = []
        with patch("modules.debates.event_mapper.split_cot_and_answer", return_value=(None, "Answer")):
            async for event in event_mapper.map_event(
                "custom", {"type": "personality_completed", "personality": "critic"}
            ):
                events.append(event)
        
        # Should emit personality_completed and cost_update events
        assert len(events) == 2
        assert events[0].type == DebateEventType.PERSONALITY_COMPLETED
        assert events[0].personality == "critic"
        assert events[0].response is not None
        assert events[1].type == DebateEventType.COST_UPDATE
        
        # Should record usage
        mock_usage_tracker.record_personality_usage.assert_called_once()
        
        # Should save response to database
        mock_debate_service.save_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_round_completed(self, event_mapper, mock_debate_service):
        """Should handle round_completed custom event."""
        event_mapper.current_round_num = 1
        
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "round_completed"}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.ROUND_COMPLETED
        assert events[0].round_number == 1
        
        # Should update debate status
        mock_debate_service.update_debate_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_consensus_check(self, event_mapper):
        """Should handle consensus_check custom event."""
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "consensus_check", "round_number": 1, "skipped": False}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.PROGRESS_UPDATE
        assert events[0].progress["phase"] == "consensus_check"
        assert events[0].progress["round_number"] == 1

    @pytest.mark.asyncio
    async def test_handles_consensus_result(self, event_mapper):
        """Should handle consensus_result custom event."""
        events = []
        async for event in event_mapper.map_event(
            "custom", {
                "type": "consensus_result",
                "consensus_reached": True,
                "reasoning": "All agreed",
            }
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.PROGRESS_UPDATE
        assert events[0].progress["phase"] == "consensus_result"
        assert events[0].progress["consensus_reached"] is True
        assert events[0].progress["reasoning"] == "All agreed"

    @pytest.mark.asyncio
    async def test_handles_synthesis_started(self, event_mapper):
        """Should handle synthesis_started custom event."""
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "synthesis_started"}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.SYNTHESIS_STARTED
        assert event_mapper.current_personality == "synthesizer"
        assert event_mapper.streaming_buffers["synthesizer"] == ""

    @pytest.mark.asyncio
    async def test_handles_synthesis_completed(
        self, event_mapper, mock_debate_service, mock_usage_tracker
    ):
        """Should handle synthesis_completed custom event."""
        event_mapper.streaming_buffers["synthesizer"] = "Final synthesis content."
        
        events = []
        async for event in event_mapper.map_event(
            "custom", {"type": "synthesis_completed"}
        ):
            events.append(event)
        
        assert len(events) == 1
        assert events[0].type == DebateEventType.SYNTHESIS_COMPLETED
        assert events[0].synthesis is not None
        assert events[0].synthesis.content == "Final synthesis content."
        
        # Should record usage
        mock_usage_tracker.record_synthesis_usage.assert_called_once()
        
        # Should save synthesis to database
        mock_debate_service.save_synthesis.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_updates_mode(self, event_mapper):
        """Should handle updates mode without emitting events."""
        events = []
        async for event in event_mapper.map_event(
            "updates", {"synthesize": {"final_synthesis": "Content"}}
        ):
            events.append(event)
        
        # Updates mode doesn't emit events currently
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_ignores_empty_message_content(self, event_mapper):
        """Should not emit events for empty message content."""
        mock_chunk = MagicMock(content="")
        
        events = []
        async for event in event_mapper.map_event(
            "messages", (mock_chunk, {})
        ):
            events.append(event)
        
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_clears_current_personality_after_completion(
        self, event_mapper, mock_usage_tracker
    ):
        """Should clear current_personality after personality_completed."""
        event_mapper.current_round_id = "round-123"
        event_mapper.current_personality = "critic"
        event_mapper.streaming_buffers["critic"] = "Response"
        
        with patch("modules.debates.event_mapper.split_cot_and_answer", return_value=(None, "Answer")):
            async for _ in event_mapper.map_event(
                "custom", {"type": "personality_completed", "personality": "critic"}
            ):
                pass
        
        assert event_mapper.current_personality is None

    @pytest.mark.asyncio
    async def test_resets_buffers_on_new_round(self, event_mapper, mock_debate_service):
        """Should reset streaming buffers when new round starts."""
        event_mapper.streaming_buffers = {"old_content": "data"}
        event_mapper.round_responses = [MagicMock()]
        
        async for _ in event_mapper.map_event(
            "custom", {"type": "round_started", "round_number": 2}
        ):
            pass
        
        assert event_mapper.streaming_buffers == {}
        assert event_mapper.round_responses == []
        assert event_mapper.current_round_num == 2
