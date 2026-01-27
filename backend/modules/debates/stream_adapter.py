"""
Adapter that runs debates using LangGraph and yields SSE events.

Thin orchestrator coordinating StateBuilder, EventMapper, and UsageTracker.
"""

from typing import AsyncIterator, TYPE_CHECKING

from core.graph import build_graph
from providers.factory import get_providers

from .models import Debate, DebateEvent, DebateEventType, DebateStatus
from .state_builder import build_initial_state
from .event_mapper import EventMapper
from .usage_tracker import UsageTracker

if TYPE_CHECKING:
    from .service import DebateService


class DebateStreamAdapter:
    """Runs a debate using LangGraph and yields DebateEvent objects."""

    def __init__(
        self,
        debate: Debate,
        user_id: str,
        debate_service: "DebateService",
    ):
        self.debate = debate
        self.user_id = user_id
        self.debate_service = debate_service
        self.providers = get_providers()
        self.usage_tracker = UsageTracker(
            user_id=user_id,
            debate_id=debate.id,
            provider=debate.provider,
            model=debate.model,
        )
        self.event_mapper = EventMapper(
            debate_id=debate.id,
            question=debate.question,
            debate_service=debate_service,
            usage_tracker=self.usage_tracker,
        )

    async def run(self) -> AsyncIterator[DebateEvent]:
        """Run the debate using LangGraph and yield events."""
        try:
            await self.debate_service.update_debate_status(
                self.debate.id, DebateStatus.ACTIVE
            )

            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id=self.debate.id,
                progress={
                    "question": self.debate.question,
                    "max_rounds": self.debate.max_rounds,
                    "personalities": self.debate.settings.personalities,
                },
            )

            graph = build_graph()
            initial_state = build_initial_state(self.debate, self.providers)

            async for chunk in graph.astream(
                initial_state,
                stream_mode=["messages", "updates", "custom"],
            ):
                mode, data = chunk
                async for event in self.event_mapper.map_event(mode, data):
                    yield event

            await self.debate_service.update_debate_status(
                self.debate.id,
                DebateStatus.COMPLETED,
                current_round=self.event_mapper.current_round_num,
            )
            await self.debate_service.update_debate_totals(
                self.debate.id,
                self.usage_tracker.total_input_tokens,
                self.usage_tracker.total_output_tokens,
                self.usage_tracker.total_cost,
            )

            yield DebateEvent(
                type=DebateEventType.DEBATE_COMPLETED,
                debate_id=self.debate.id,
                progress={
                    "total_rounds": self.event_mapper.current_round_num,
                    "total_input_tokens": self.usage_tracker.total_input_tokens,
                    "total_output_tokens": self.usage_tracker.total_output_tokens,
                },
                cost=self.usage_tracker.total_cost,
            )

        except Exception as e:
            await self.debate_service.update_debate_status(
                self.debate.id, DebateStatus.FAILED, error_message=str(e)
            )
            yield DebateEvent(
                type=DebateEventType.DEBATE_FAILED,
                debate_id=self.debate.id,
                error=str(e),
            )
