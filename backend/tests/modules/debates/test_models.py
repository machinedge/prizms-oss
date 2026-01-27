"""Tests for debates module data models."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from modules.debates.models import (
    Debate,
    DebateStatus,
    CreateDebateRequest,
    DebateSettings,
    DebateEvent,
    DebateEventType,
    PersonalityResponse,
    DebateRound,
    DebateSynthesis,
    DebateListItem,
    DebateListResponse,
    SYSTEM_PERSONALITIES,
    get_default_personalities,
)


class TestDebateStatus:
    def test_status_values(self):
        """Should have all expected status values."""
        assert DebateStatus.PENDING == "pending"
        assert DebateStatus.ACTIVE == "active"
        assert DebateStatus.COMPLETED == "completed"
        assert DebateStatus.FAILED == "failed"
        assert DebateStatus.CANCELLED == "cancelled"

    def test_status_is_string_enum(self):
        """Should be usable as string."""
        # str() returns the enum name, .value returns the string value
        assert DebateStatus.PENDING.value == "pending"
        assert DebateStatus.ACTIVE.value == "active"
        # String enum can be compared directly
        assert DebateStatus.PENDING == "pending"


class TestSystemPersonalities:
    def test_system_personalities_defined(self):
        """Should have system personalities defined."""
        assert "consensus_check" in SYSTEM_PERSONALITIES
        assert "synthesizer" in SYSTEM_PERSONALITIES

    def test_get_default_personalities(self):
        """Should return non-system personalities."""
        defaults = get_default_personalities()
        assert isinstance(defaults, list)
        # Defaults should not include system personalities
        for personality in defaults:
            assert personality not in SYSTEM_PERSONALITIES


class TestDebateSettings:
    def test_default_settings(self):
        """Should have sensible defaults."""
        settings = DebateSettings()
        assert settings.max_rounds == 3
        assert settings.temperature == 0.7
        # Personalities are now dynamic based on prompts directory
        assert isinstance(settings.personalities, list)
        assert settings.include_synthesis is True

    def test_custom_settings(self):
        """Should allow custom values."""
        settings = DebateSettings(
            max_rounds=5,
            temperature=0.9,
            personalities=["optimist", "pessimist"],
            include_synthesis=False,
        )
        assert settings.max_rounds == 5
        assert settings.temperature == 0.9
        assert len(settings.personalities) == 2
        assert settings.include_synthesis is False

    def test_max_rounds_validation(self):
        """Should validate max_rounds range."""
        with pytest.raises(ValueError):
            DebateSettings(max_rounds=0)  # Too low
        with pytest.raises(ValueError):
            DebateSettings(max_rounds=11)  # Too high

    def test_temperature_validation(self):
        """Should validate temperature range."""
        with pytest.raises(ValueError):
            DebateSettings(temperature=-0.1)  # Too low
        with pytest.raises(ValueError):
            DebateSettings(temperature=2.1)  # Too high


class TestCreateDebateRequest:
    def test_create_debate_request(self):
        """Should create a debate request."""
        request = CreateDebateRequest(
            question="What is the meaning of life?",
            provider="anthropic",
            model="claude-3-5-sonnet",
        )
        assert request.question == "What is the meaning of life?"
        assert request.provider == "anthropic"
        assert request.model == "claude-3-5-sonnet"
        assert request.settings.max_rounds == 3  # Default

    def test_create_debate_request_with_settings(self):
        """Should accept custom settings."""
        request = CreateDebateRequest(
            question="Test question",
            provider="openai",
            model="gpt-4",
            settings=DebateSettings(max_rounds=5),
        )
        assert request.settings.max_rounds == 5

    def test_question_validation(self):
        """Should validate question length."""
        with pytest.raises(ValueError):
            CreateDebateRequest(
                question="",  # Too short
                provider="anthropic",
                model="claude",
            )


class TestPersonalityResponse:
    def test_personality_response(self):
        """Should create a personality response."""
        response = PersonalityResponse(
            personality_name="optimist",
            answer_content="This is a great opportunity!",
        )
        assert response.personality_name == "optimist"
        assert response.answer_content == "This is a great opportunity!"
        assert response.thinking_content is None
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.cost == Decimal(0)

    def test_personality_response_with_thinking(self):
        """Should include thinking content when provided."""
        response = PersonalityResponse(
            personality_name="analyst",
            thinking_content="Let me analyze this step by step...",
            answer_content="Based on my analysis...",
            input_tokens=100,
            output_tokens=50,
            cost=Decimal("0.005"),
        )
        assert response.thinking_content == "Let me analyze this step by step..."
        assert response.cost == Decimal("0.005")


class TestDebateRound:
    def test_debate_round(self):
        """Should create a debate round."""
        round_obj = DebateRound(
            id="round-123",
            debate_id="debate-456",
            round_number=1,
        )
        assert round_obj.id == "round-123"
        assert round_obj.debate_id == "debate-456"
        assert round_obj.round_number == 1
        assert round_obj.responses == []

    def test_debate_round_with_responses(self):
        """Should include responses."""
        response = PersonalityResponse(
            personality_name="optimist",
            answer_content="Great idea!",
        )
        round_obj = DebateRound(
            id="round-123",
            debate_id="debate-456",
            round_number=1,
            responses=[response],
        )
        assert len(round_obj.responses) == 1
        assert round_obj.responses[0].personality_name == "optimist"


class TestDebateSynthesis:
    def test_debate_synthesis(self):
        """Should create a synthesis."""
        synthesis = DebateSynthesis(
            id="synth-123",
            debate_id="debate-456",
            content="In conclusion, the perspectives show...",
        )
        assert synthesis.id == "synth-123"
        assert synthesis.content == "In conclusion, the perspectives show..."
        assert synthesis.cost == Decimal(0)


class TestDebate:
    def test_debate_creation(self):
        """Should create a debate."""
        now = datetime.now(timezone.utc)
        debate = Debate(
            id="debate-123",
            user_id="user-456",
            question="What should we do about climate change?",
            status=DebateStatus.PENDING,
            provider="anthropic",
            model="claude-3-5-sonnet",
            settings=DebateSettings(),
            max_rounds=3,
            created_at=now,
            updated_at=now,
        )
        assert debate.id == "debate-123"
        assert debate.user_id == "user-456"
        assert debate.status == DebateStatus.PENDING
        assert debate.current_round == 0
        assert debate.rounds == []
        assert debate.synthesis is None
        assert debate.total_cost == Decimal(0)

    def test_debate_with_content(self):
        """Should include rounds and synthesis."""
        now = datetime.now(timezone.utc)
        synthesis = DebateSynthesis(
            id="synth-1",
            debate_id="debate-123",
            content="Final synthesis...",
        )
        round_obj = DebateRound(
            id="round-1",
            debate_id="debate-123",
            round_number=1,
        )
        debate = Debate(
            id="debate-123",
            user_id="user-456",
            question="Test question",
            status=DebateStatus.COMPLETED,
            provider="openai",
            model="gpt-4",
            settings=DebateSettings(),
            max_rounds=3,
            current_round=3,
            rounds=[round_obj],
            synthesis=synthesis,
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        assert len(debate.rounds) == 1
        assert debate.synthesis is not None


class TestDebateListItem:
    def test_debate_list_item(self):
        """Should create a list item."""
        now = datetime.now(timezone.utc)
        item = DebateListItem(
            id="debate-123",
            question="Short question",
            status=DebateStatus.COMPLETED,
            provider="anthropic",
            model="claude",
            current_round=3,
            max_rounds=3,
            created_at=now,
        )
        assert item.id == "debate-123"
        assert item.status == DebateStatus.COMPLETED


class TestDebateListResponse:
    def test_debate_list_response(self):
        """Should create a list response."""
        response = DebateListResponse(
            debates=[],
            total=0,
            page=1,
            page_size=20,
            has_more=False,
        )
        assert response.total == 0
        assert response.page == 1
        assert response.has_more is False


class TestDebateEventType:
    def test_event_types(self):
        """Should have all expected event types."""
        assert DebateEventType.DEBATE_STARTED == "debate_started"
        assert DebateEventType.DEBATE_COMPLETED == "debate_completed"
        assert DebateEventType.THINKING_CHUNK == "thinking_chunk"
        assert DebateEventType.ANSWER_CHUNK == "answer_chunk"
        assert DebateEventType.SYNTHESIS_COMPLETED == "synthesis_completed"


class TestDebateEvent:
    def test_debate_event(self):
        """Should create an event."""
        event = DebateEvent(
            type=DebateEventType.DEBATE_STARTED,
            debate_id="debate-123",
        )
        assert event.type == DebateEventType.DEBATE_STARTED
        assert event.debate_id == "debate-123"
        assert event.timestamp is not None

    def test_debate_event_with_content(self):
        """Should include optional fields."""
        event = DebateEvent(
            type=DebateEventType.ANSWER_CHUNK,
            debate_id="debate-123",
            round_number=1,
            personality="optimist",
            content="This is great!",
        )
        assert event.round_number == 1
        assert event.personality == "optimist"
        assert event.content == "This is great!"

    def test_debate_event_to_sse(self):
        """Should convert event to SSE format."""
        event = DebateEvent(
            type=DebateEventType.DEBATE_STARTED,
            debate_id="debate-123",
        )
        sse = event.to_sse()
        assert "event: debate_started" in sse
        assert "debate-123" in sse
        assert "data:" in sse
        assert sse.endswith("\n\n")

    def test_debate_event_to_sse_excludes_none(self):
        """SSE format should exclude None fields."""
        event = DebateEvent(
            type=DebateEventType.DEBATE_STARTED,
            debate_id="debate-123",
        )
        sse = event.to_sse()
        assert "round_number" not in sse
        assert "personality" not in sse
        assert "content" not in sse

    def test_debate_event_with_cost(self):
        """Should handle cost field."""
        event = DebateEvent(
            type=DebateEventType.COST_UPDATE,
            debate_id="debate-123",
            cost=Decimal("0.0125"),
        )
        sse = event.to_sse()
        assert "0.0125" in sse


# ============================================================================
# Story 25: ConsensusResult and JsonOutputParser Tests
# ============================================================================

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from core.models import ConsensusResult


class TestConsensusResult:
    """Tests for the ConsensusResult Pydantic model."""

    def test_consensus_result_with_true(self):
        """Should create result with consensus=True."""
        result = ConsensusResult(
            consensus=True,
            reasoning="All parties agree on the main points.",
        )
        assert result.consensus is True
        assert result.reasoning == "All parties agree on the main points."

    def test_consensus_result_with_false(self):
        """Should create result with consensus=False."""
        result = ConsensusResult(
            consensus=False,
            reasoning="Fundamental disagreement on approach.",
        )
        assert result.consensus is False
        assert result.reasoning == "Fundamental disagreement on approach."

    def test_consensus_result_requires_consensus_field(self):
        """Should require consensus field."""
        with pytest.raises(ValueError):
            ConsensusResult(reasoning="Missing consensus field")

    def test_consensus_result_requires_reasoning_field(self):
        """Should require reasoning field."""
        with pytest.raises(ValueError):
            ConsensusResult(consensus=True)

    def test_consensus_result_validates_consensus_type(self):
        """Should validate that consensus is a boolean."""
        # Pydantic will coerce "true" string to True boolean
        result = ConsensusResult(consensus="true", reasoning="Test")
        assert result.consensus is True
        
        # Non-boolean-coercible values should fail
        with pytest.raises(ValueError):
            ConsensusResult(consensus="maybe", reasoning="Test")


class TestJsonOutputParserWithConsensusResult:
    """Tests for JsonOutputParser integration with ConsensusResult."""

    def test_parser_with_valid_json_consensus_true(self):
        """Should parse valid JSON with consensus=true."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        json_str = '{"consensus": true, "reasoning": "All perspectives align."}'
        
        result = parser.parse(json_str)
        
        assert result["consensus"] is True
        assert result["reasoning"] == "All perspectives align."

    def test_parser_with_valid_json_consensus_false(self):
        """Should parse valid JSON with consensus=false."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        json_str = '{"consensus": false, "reasoning": "Major disagreements remain."}'
        
        result = parser.parse(json_str)
        
        assert result["consensus"] is False
        assert result["reasoning"] == "Major disagreements remain."

    def test_parser_with_json_in_markdown_code_block(self):
        """Should parse JSON embedded in markdown code block."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        response = '''Based on my analysis:

```json
{"consensus": true, "reasoning": "Parties reached agreement."}
```

That's my assessment.'''
        
        result = parser.parse(response)
        
        assert result["consensus"] is True
        assert result["reasoning"] == "Parties reached agreement."

    def test_parser_with_extra_whitespace(self):
        """Should handle JSON with extra whitespace."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        json_str = '''
        {
            "consensus": false,
            "reasoning": "Significant differences exist."
        }
        '''
        
        result = parser.parse(json_str)
        
        assert result["consensus"] is False

    def test_parser_raises_on_invalid_json(self):
        """Should raise OutputParserException on invalid JSON."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        invalid_json = "This is not valid JSON at all"
        
        with pytest.raises(OutputParserException):
            parser.parse(invalid_json)

    def test_parser_returns_dict_even_with_missing_field(self):
        """JsonOutputParser returns dict without Pydantic validation.
        
        Note: JsonOutputParser only parses JSON, it does not validate
        against the Pydantic model. Validation happens when the dict
        is used to create the Pydantic model.
        """
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        incomplete_json = '{"consensus": true}'  # Missing reasoning
        
        # Parser returns dict without validation
        result = parser.parse(incomplete_json)
        assert result == {"consensus": True}
        
        # Pydantic validation fails when creating model
        with pytest.raises(ValueError):
            ConsensusResult(**result)

    def test_parser_returns_dict_with_wrong_field_type(self):
        """JsonOutputParser returns dict without type coercion.
        
        Note: JsonOutputParser only parses JSON to dict, type coercion
        happens when creating the Pydantic model.
        Pydantic coerces "yes"/"no"/"true"/"false" to bool, but not arbitrary strings.
        """
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        wrong_type_json = '{"consensus": "maybe", "reasoning": "Test"}'
        
        # Parser returns dict
        result = parser.parse(wrong_type_json)
        assert result["consensus"] == "maybe"  # Still a string
        
        # Pydantic validation fails - "maybe" cannot be coerced to boolean
        with pytest.raises(ValueError):
            ConsensusResult(**result)

    def test_parser_format_instructions(self):
        """Should provide format instructions for the LLM."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        instructions = parser.get_format_instructions()
        
        # Should mention JSON format
        assert "json" in instructions.lower() or "JSON" in instructions
        # Should mention the expected fields
        assert "consensus" in instructions
        assert "reasoning" in instructions

    def test_parser_requires_clean_json_or_code_block(self):
        """Parser fails when JSON has surrounding text without code block.
        
        JsonOutputParser requires either:
        1. Pure JSON string
        2. JSON inside a markdown code block (```json ... ```)
        
        It does NOT extract JSON from surrounding prose text.
        """
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        response = '''After careful analysis:

{"consensus": false, "reasoning": "Disagreements remain."}

That's my assessment.'''
        
        # Parser fails on text with surrounding prose
        with pytest.raises(OutputParserException):
            parser.parse(response)

    def test_parser_with_json_only_response(self):
        """Should parse response that is pure JSON."""
        parser = JsonOutputParser(pydantic_object=ConsensusResult)
        response = '{"consensus": false, "reasoning": "Fundamental differences in approach remain."}'
        
        result = parser.parse(response)
        
        assert result["consensus"] is False
        assert "fundamental differences" in result["reasoning"].lower()
