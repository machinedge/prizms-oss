"""
Adapter that runs debates using LangGraph and yields SSE events.

This adapter bridges the API's Debate model to LangGraph's DebateState,
then uses graph.astream() with multiple stream modes to get:
- LLM tokens via stream_mode="messages"
- State updates via stream_mode="updates"
- Custom events via stream_mode="custom"

These are then mapped to DebateEvent objects for SSE streaming.
"""

from pathlib import Path
from typing import AsyncIterator, TYPE_CHECKING, Any
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass

from core.graph import build_graph, DebateState
from core.output import split_cot_and_answer
from providers.factory import get_providers
from providers.base import ModelConfig, LLMProvider
from shared.config import get_settings
from modules.usage.service import get_usage_service
from modules.usage.models import UsageRecord

from .models import (
    Debate,
    DebateEvent,
    DebateEventType,
    DebateStatus,
    PersonalityResponse,
    DebateSynthesis,
    SYSTEM_PERSONALITIES,
)

if TYPE_CHECKING:
    from .service import DebateService


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


class DebateStreamAdapter:
    """
    Runs a debate using LangGraph and yields DebateEvent objects.

    This adapter:
    - Bridges API Debate model to LangGraph DebateState
    - Uses graph.astream() with multiple stream modes
    - Maps LangGraph events to DebateEvent objects
    - Records usage via UsageService
    - Persists data through DebateService
    """

    def __init__(
        self,
        debate: Debate,
        user_id: str,
        debate_service: "DebateService",
    ):
        self.debate = debate
        self.user_id = user_id
        self.debate_service = debate_service
        self.usage_service = get_usage_service()
        self.providers = get_providers()

        # Track totals for completion event
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = Decimal(0)

        # Track current state for persistence
        self.current_round_num = 0
        self.current_round_id: str | None = None
        self.round_responses: list[PersonalityResponse] = []
        
        # Accumulate streaming content per personality
        self.streaming_buffers: dict[str, str] = {}
        self.current_personality: str | None = None

    def _build_initial_state(self) -> DebateState:
        """Convert API Debate model to LangGraph DebateState."""
        # Filter out system personalities from debate participants
        debate_personalities = [
            p for p in self.debate.settings.personalities
            if p not in SYSTEM_PERSONALITIES
        ]
        
        config_adapter = APIConfigAdapter(self.debate, self.providers)
        
        return {
            "question": self.debate.question,
            "personalities": debate_personalities,
            "config": config_adapter,  # type: ignore - adapter provides same interface
            "providers": self.providers,
            "max_rounds": self.debate.max_rounds,
            "current_round": 0,
            "rounds": [],
            "consensus_reached": False,
            "consensus_reasoning": "",
            "final_synthesis": None,
        }

    async def run(self) -> AsyncIterator[DebateEvent]:
        """Run the debate using LangGraph and yield events."""
        try:
            # Update status to active
            await self.debate_service.update_debate_status(
                self.debate.id, DebateStatus.ACTIVE
            )

            # Emit start event
            yield DebateEvent(
                type=DebateEventType.DEBATE_STARTED,
                debate_id=self.debate.id,
                progress={
                    "question": self.debate.question,
                    "max_rounds": self.debate.max_rounds,
                    "personalities": self.debate.settings.personalities,
                },
            )

            # Build and run the LangGraph
            graph = build_graph()
            initial_state = self._build_initial_state()

            # Stream with multiple modes
            async for chunk in graph.astream(
                initial_state,
                stream_mode=["messages", "updates", "custom"],
            ):
                # Each chunk is a tuple of (mode, data)
                mode, data = chunk
                
                # Map LangGraph events to DebateEvents
                async for event in self._handle_stream_chunk(mode, data):
                    yield event

            # Update final status
            await self.debate_service.update_debate_status(
                self.debate.id,
                DebateStatus.COMPLETED,
                current_round=self.current_round_num,
            )

            # Update debate totals
            await self.debate_service.update_debate_totals(
                self.debate.id,
                self.total_input_tokens,
                self.total_output_tokens,
                self.total_cost,
            )

            yield DebateEvent(
                type=DebateEventType.DEBATE_COMPLETED,
                debate_id=self.debate.id,
                progress={
                    "total_rounds": self.current_round_num,
                    "total_input_tokens": self.total_input_tokens,
                    "total_output_tokens": self.total_output_tokens,
                },
                cost=self.total_cost,
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

    async def _handle_stream_chunk(
        self, mode: str, data: Any
    ) -> AsyncIterator[DebateEvent]:
        """Handle a chunk from LangGraph streaming and yield DebateEvents."""
        
        if mode == "messages":
            # LLM token streaming: data is (message_chunk, metadata)
            msg_chunk, metadata = data
            if msg_chunk.content:
                # Determine if this is thinking or answer content
                event_type = DebateEventType.ANSWER_CHUNK
                
                # Accumulate content for later processing
                if self.current_personality:
                    if self.current_personality not in self.streaming_buffers:
                        self.streaming_buffers[self.current_personality] = ""
                    self.streaming_buffers[self.current_personality] += msg_chunk.content
                
                yield DebateEvent(
                    type=event_type,
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                    personality=self.current_personality,
                    content=msg_chunk.content,
                )
        
        elif mode == "custom":
            # Custom events from get_stream_writer()
            event_type = data.get("type", "")
            
            if event_type == "round_started":
                self.current_round_num = data.get("round_number", 1)
                self.round_responses = []
                self.streaming_buffers = {}
                
                # Create round record in database
                self.current_round_id = await self.debate_service.save_round(
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                )
                
                yield DebateEvent(
                    type=DebateEventType.ROUND_STARTED,
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                )
            
            elif event_type == "personality_started":
                personality = data.get("personality", "")
                self.current_personality = personality
                self.streaming_buffers[personality] = ""
                
                yield DebateEvent(
                    type=DebateEventType.PERSONALITY_STARTED,
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                    personality=personality,
                )
            
            elif event_type == "personality_completed":
                personality = data.get("personality", "")
                full_content = self.streaming_buffers.get(personality, "")
                
                # Parse thinking vs answer content
                thinking_content, answer_content = split_cot_and_answer(full_content)
                
                # Estimate tokens
                input_tokens = len(self.debate.question) // 4 + 200
                output_tokens = len(full_content) // 4
                
                # Record usage
                usage_record = await self.usage_service.record_usage(
                    user_id=self.user_id,
                    record=UsageRecord(
                        user_id=self.user_id,
                        debate_id=self.debate.id,
                        provider=self.debate.provider,
                        model=self.debate.model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        operation="debate_response",
                        personality=personality,
                        round_number=self.current_round_num,
                    ),
                )
                
                self.total_input_tokens += usage_record.input_tokens
                self.total_output_tokens += usage_record.output_tokens
                self.total_cost += usage_record.cost
                
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
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                    personality=personality,
                    response=response,
                )
                
                # Emit cost update
                yield DebateEvent(
                    type=DebateEventType.COST_UPDATE,
                    debate_id=self.debate.id,
                    cost=self.total_cost,
                )
                
                self.current_personality = None
            
            elif event_type == "round_completed":
                yield DebateEvent(
                    type=DebateEventType.ROUND_COMPLETED,
                    debate_id=self.debate.id,
                    round_number=self.current_round_num,
                    progress={
                        "response_count": len(self.round_responses),
                    },
                )
                
                # Update debate progress in database
                await self.debate_service.update_debate_status(
                    self.debate.id,
                    DebateStatus.ACTIVE,
                    current_round=self.current_round_num,
                )
            
            elif event_type == "consensus_check":
                yield DebateEvent(
                    type=DebateEventType.PROGRESS_UPDATE,
                    debate_id=self.debate.id,
                    progress={
                        "phase": "consensus_check",
                        "round_number": data.get("round_number"),
                        "skipped": data.get("skipped", False),
                    },
                )
            
            elif event_type == "consensus_result":
                yield DebateEvent(
                    type=DebateEventType.PROGRESS_UPDATE,
                    debate_id=self.debate.id,
                    progress={
                        "phase": "consensus_result",
                        "consensus_reached": data.get("consensus_reached", False),
                        "reasoning": data.get("reasoning", ""),
                    },
                )
            
            elif event_type == "synthesis_started":
                self.current_personality = "synthesizer"
                self.streaming_buffers["synthesizer"] = ""
                
                yield DebateEvent(
                    type=DebateEventType.SYNTHESIS_STARTED,
                    debate_id=self.debate.id,
                )
            
            elif event_type == "synthesis_completed":
                full_content = self.streaming_buffers.get("synthesizer", "")
                
                # Estimate tokens
                input_tokens = self.total_output_tokens + 500
                output_tokens = len(full_content) // 4
                
                # Record usage
                usage_record = await self.usage_service.record_usage(
                    user_id=self.user_id,
                    record=UsageRecord(
                        user_id=self.user_id,
                        debate_id=self.debate.id,
                        provider=self.debate.provider,
                        model=self.debate.model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        operation="synthesis",
                    ),
                )
                
                self.total_input_tokens += usage_record.input_tokens
                self.total_output_tokens += usage_record.output_tokens
                self.total_cost += usage_record.cost
                
                # Persist synthesis
                synthesis_id = await self.debate_service.save_synthesis(
                    debate_id=self.debate.id,
                    content=full_content,
                    input_tokens=usage_record.input_tokens,
                    output_tokens=usage_record.output_tokens,
                    cost=usage_record.cost,
                )
                
                synthesis = DebateSynthesis(
                    id=synthesis_id,
                    debate_id=self.debate.id,
                    content=full_content,
                    input_tokens=usage_record.input_tokens,
                    output_tokens=usage_record.output_tokens,
                    cost=usage_record.cost,
                )
                
                yield DebateEvent(
                    type=DebateEventType.SYNTHESIS_COMPLETED,
                    debate_id=self.debate.id,
                    synthesis=synthesis,
                )
                
                self.current_personality = None
        
        elif mode == "updates":
            # State updates after each node - used for tracking progress
            # data is {node_name: state_delta}
            for node_name, state_delta in data.items():
                if node_name == "synthesize" and "final_synthesis" in state_delta:
                    # Synthesis complete - content already handled via custom events
                    pass
