"""
Event mapper for translating LangGraph events to DebateEvents.

This module handles mapping between LangGraph's streaming events
and the SSE-friendly DebateEvent objects used by the API.
"""

from typing import AsyncIterator, Any, TYPE_CHECKING

from core.output import split_cot_and_answer

from .models import (
    DebateEvent,
    DebateEventType,
    DebateStatus,
    PersonalityResponse,
    DebateSynthesis,
)
from .usage_tracker import UsageTracker

if TYPE_CHECKING:
    from .service import DebateService


class EventMapper:
    """
    Maps LangGraph streaming events to DebateEvent objects.
    
    This class:
    - Handles all three stream modes: messages, custom, updates
    - Tracks streaming buffers for content accumulation
    - Coordinates with UsageTracker for token/cost tracking
    - Delegates persistence to DebateService
    """
    
    def __init__(
        self,
        debate_id: str,
        question: str,
        debate_service: "DebateService",
        usage_tracker: UsageTracker,
    ):
        self.debate_id = debate_id
        self.question = question
        self.debate_service = debate_service
        self.usage_tracker = usage_tracker
        
        # Track current state for persistence
        self.current_round_num = 0
        self.current_round_id: str | None = None
        self.round_responses: list[PersonalityResponse] = []
        
        # Accumulate streaming content per personality
        self.streaming_buffers: dict[str, str] = {}
        self.current_personality: str | None = None
    
    async def map_event(
        self, mode: str, data: Any
    ) -> AsyncIterator[DebateEvent]:
        """
        Map a LangGraph stream chunk to DebateEvents.
        
        Args:
            mode: Stream mode - "messages", "custom", or "updates"
            data: The data from the stream
            
        Yields:
            DebateEvent objects for SSE streaming
        """
        if mode == "messages":
            async for event in self._handle_messages(data):
                yield event
        elif mode == "custom":
            async for event in self._handle_custom(data):
                yield event
        elif mode == "updates":
            async for event in self._handle_updates(data):
                yield event
    
    async def _handle_messages(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle LLM token streaming events."""
        # data is (message_chunk, metadata)
        msg_chunk, metadata = data
        if msg_chunk.content:
            # Accumulate content for later processing
            if self.current_personality:
                if self.current_personality not in self.streaming_buffers:
                    self.streaming_buffers[self.current_personality] = ""
                self.streaming_buffers[self.current_personality] += msg_chunk.content
            
            yield DebateEvent(
                type=DebateEventType.ANSWER_CHUNK,
                debate_id=self.debate_id,
                round_number=self.current_round_num,
                personality=self.current_personality,
                content=msg_chunk.content,
            )
    
    async def _handle_custom(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle custom events from get_stream_writer()."""
        event_type = data.get("type", "")
        
        if event_type == "round_started":
            async for event in self._on_round_started(data):
                yield event
        elif event_type == "personality_started":
            async for event in self._on_personality_started(data):
                yield event
        elif event_type == "personality_completed":
            async for event in self._on_personality_completed(data):
                yield event
        elif event_type == "round_completed":
            async for event in self._on_round_completed(data):
                yield event
        elif event_type == "consensus_check":
            async for event in self._on_consensus_check(data):
                yield event
        elif event_type == "consensus_result":
            async for event in self._on_consensus_result(data):
                yield event
        elif event_type == "synthesis_started":
            async for event in self._on_synthesis_started(data):
                yield event
        elif event_type == "synthesis_completed":
            async for event in self._on_synthesis_completed(data):
                yield event
    
    async def _handle_updates(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle state updates after each node."""
        # data is {node_name: state_delta}
        for node_name, state_delta in data.items():
            if node_name == "synthesize" and "final_synthesis" in state_delta:
                # Synthesis complete - content already handled via custom events
                pass
        # No events yielded from updates currently
        return
        yield  # Make this a generator
    
    async def _on_round_started(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle round_started event."""
        self.current_round_num = data.get("round_number", 1)
        self.round_responses = []
        self.streaming_buffers = {}
        
        # Create round record in database
        self.current_round_id = await self.debate_service.save_round(
            debate_id=self.debate_id,
            round_number=self.current_round_num,
        )
        
        yield DebateEvent(
            type=DebateEventType.ROUND_STARTED,
            debate_id=self.debate_id,
            round_number=self.current_round_num,
        )
    
    async def _on_personality_started(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle personality_started event."""
        personality = data.get("personality", "")
        self.current_personality = personality
        self.streaming_buffers[personality] = ""
        
        yield DebateEvent(
            type=DebateEventType.PERSONALITY_STARTED,
            debate_id=self.debate_id,
            round_number=self.current_round_num,
            personality=personality,
        )
    
    async def _on_personality_completed(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle personality_completed event."""
        personality = data.get("personality", "")
        full_content = self.streaming_buffers.get(personality, "")
        
        # Parse thinking vs answer content
        thinking_content, answer_content = split_cot_and_answer(full_content)
        
        # Record usage via tracker
        usage_record = await self.usage_tracker.record_personality_usage(
            personality=personality,
            round_number=self.current_round_num,
            question=self.question,
            full_content=full_content,
        )
        
        # Build response model
        response = PersonalityResponse(
            personality_name=personality,
            thinking_content=thinking_content or None,
            answer_content=answer_content or full_content,
            input_tokens=usage_record.input_tokens,
            output_tokens=usage_record.output_tokens,
            cost=usage_record.cost,
        )
        self.round_responses.append(response)
        
        # Persist response to database
        if self.current_round_id:
            await self.debate_service.save_response(
                round_id=self.current_round_id,
                response=response,
            )
        
        yield DebateEvent(
            type=DebateEventType.PERSONALITY_COMPLETED,
            debate_id=self.debate_id,
            round_number=self.current_round_num,
            personality=personality,
            response=response,
        )
        
        # Emit cost update
        yield DebateEvent(
            type=DebateEventType.COST_UPDATE,
            debate_id=self.debate_id,
            cost=self.usage_tracker.total_cost,
        )
        
        self.current_personality = None
    
    async def _on_round_completed(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle round_completed event."""
        yield DebateEvent(
            type=DebateEventType.ROUND_COMPLETED,
            debate_id=self.debate_id,
            round_number=self.current_round_num,
            progress={
                "response_count": len(self.round_responses),
            },
        )
        
        # Update debate progress in database
        await self.debate_service.update_debate_status(
            self.debate_id,
            DebateStatus.ACTIVE,
            current_round=self.current_round_num,
        )
    
    async def _on_consensus_check(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle consensus_check event."""
        yield DebateEvent(
            type=DebateEventType.PROGRESS_UPDATE,
            debate_id=self.debate_id,
            progress={
                "phase": "consensus_check",
                "round_number": data.get("round_number"),
                "skipped": data.get("skipped", False),
            },
        )
    
    async def _on_consensus_result(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle consensus_result event."""
        yield DebateEvent(
            type=DebateEventType.PROGRESS_UPDATE,
            debate_id=self.debate_id,
            progress={
                "phase": "consensus_result",
                "consensus_reached": data.get("consensus_reached", False),
                "reasoning": data.get("reasoning", ""),
            },
        )
    
    async def _on_synthesis_started(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle synthesis_started event."""
        self.current_personality = "synthesizer"
        self.streaming_buffers["synthesizer"] = ""
        
        yield DebateEvent(
            type=DebateEventType.SYNTHESIS_STARTED,
            debate_id=self.debate_id,
        )
    
    async def _on_synthesis_completed(self, data: Any) -> AsyncIterator[DebateEvent]:
        """Handle synthesis_completed event."""
        full_content = self.streaming_buffers.get("synthesizer", "")
        
        # Record usage via tracker
        usage_record = await self.usage_tracker.record_synthesis_usage(
            full_content=full_content,
        )
        
        # Persist synthesis
        synthesis_id = await self.debate_service.save_synthesis(
            debate_id=self.debate_id,
            content=full_content,
            input_tokens=usage_record.input_tokens,
            output_tokens=usage_record.output_tokens,
            cost=usage_record.cost,
        )
        
        synthesis = DebateSynthesis(
            id=synthesis_id,
            debate_id=self.debate_id,
            content=full_content,
            input_tokens=usage_record.input_tokens,
            output_tokens=usage_record.output_tokens,
            cost=usage_record.cost,
        )
        
        yield DebateEvent(
            type=DebateEventType.SYNTHESIS_COMPLETED,
            debate_id=self.debate_id,
            synthesis=synthesis,
        )
        
        self.current_personality = None
