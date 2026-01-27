"""Tests for usage_tracker module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from modules.debates.usage_tracker import UsageTracker, UsageTotals


class TestUsageTotals:
    """Tests for the UsageTotals dataclass."""

    def test_default_values(self):
        """Should have zero defaults."""
        totals = UsageTotals()
        assert totals.input_tokens == 0
        assert totals.output_tokens == 0
        assert totals.cost == Decimal(0)

    def test_custom_values(self):
        """Should accept custom values."""
        totals = UsageTotals(
            input_tokens=100,
            output_tokens=200,
            cost=Decimal("0.001"),
        )
        assert totals.input_tokens == 100
        assert totals.output_tokens == 200
        assert totals.cost == Decimal("0.001")


class TestUsageTracker:
    """Tests for the UsageTracker class."""

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

    def test_initialization(self, mock_usage_service):
        """Should initialize with zero totals."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        assert tracker.user_id == "user-123"
        assert tracker.debate_id == "debate-123"
        assert tracker.provider == "anthropic"
        assert tracker.model == "claude-sonnet-4-5"
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_cost == Decimal(0)

    def test_get_totals_returns_copy(self, mock_usage_service):
        """Should return a copy of totals."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        # Modify internal state
        tracker._totals.input_tokens = 100
        tracker._totals.output_tokens = 200
        tracker._totals.cost = Decimal("0.001")
        
        totals = tracker.get_totals()
        assert totals.input_tokens == 100
        assert totals.output_tokens == 200
        assert totals.cost == Decimal("0.001")

    @pytest.mark.asyncio
    async def test_record_personality_usage(self, mock_usage_service):
        """Should record usage for personality response."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=50):
            record = await tracker.record_personality_usage(
                personality="critic",
                round_number=1,
                question="What is the meaning of life?",
                full_content="This is the response content.",
            )
        
        # Verify record_usage was called
        mock_usage_service.record_usage.assert_called_once()
        call_args = mock_usage_service.record_usage.call_args
        assert call_args.kwargs["user_id"] == "user-123"
        
        usage_record = call_args.kwargs["record"]
        assert usage_record.debate_id == "debate-123"
        assert usage_record.provider == "anthropic"
        assert usage_record.model == "claude-sonnet-4-5"
        assert usage_record.operation == "debate_response"
        assert usage_record.personality == "critic"
        assert usage_record.round_number == 1

    @pytest.mark.asyncio
    async def test_record_personality_usage_updates_totals(self, mock_usage_service):
        """Should update running totals after recording."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=50):
            await tracker.record_personality_usage(
                personality="critic",
                round_number=1,
                question="Test question?",
                full_content="Test response.",
            )
        
        assert tracker.total_input_tokens == 100
        assert tracker.total_output_tokens == 200
        assert tracker.total_cost == Decimal("0.001")

    @pytest.mark.asyncio
    async def test_record_synthesis_usage(self, mock_usage_service):
        """Should record usage for synthesis."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=100):
            record = await tracker.record_synthesis_usage(
                full_content="This is the synthesis content.",
            )
        
        # Verify record_usage was called
        mock_usage_service.record_usage.assert_called_once()
        call_args = mock_usage_service.record_usage.call_args
        
        usage_record = call_args.kwargs["record"]
        assert usage_record.operation == "synthesis"
        assert usage_record.personality is None
        assert usage_record.round_number is None

    @pytest.mark.asyncio
    async def test_record_synthesis_usage_updates_totals(self, mock_usage_service):
        """Should update running totals after synthesis."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=100):
            await tracker.record_synthesis_usage(
                full_content="Synthesis content.",
            )
        
        assert tracker.total_input_tokens == 100
        assert tracker.total_output_tokens == 200
        assert tracker.total_cost == Decimal("0.001")

    @pytest.mark.asyncio
    async def test_multiple_recordings_accumulate(self, mock_usage_service):
        """Should accumulate totals from multiple recordings."""
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=50):
            # Record two personality responses
            await tracker.record_personality_usage(
                personality="critic",
                round_number=1,
                question="Test?",
                full_content="Response 1",
            )
            await tracker.record_personality_usage(
                personality="interpreter",
                round_number=1,
                question="Test?",
                full_content="Response 2",
            )
        
        # Should have accumulated totals from both calls
        assert tracker.total_input_tokens == 200  # 100 + 100
        assert tracker.total_output_tokens == 400  # 200 + 200
        assert tracker.total_cost == Decimal("0.002")  # 0.001 + 0.001

    @pytest.mark.asyncio
    async def test_synthesis_uses_accumulated_output_tokens_for_input(self):
        """Should use accumulated output tokens as input estimate for synthesis."""
        mock_usage_service = MagicMock()
        mock_usage_service.record_usage = AsyncMock(
            return_value=MagicMock(
                input_tokens=500,
                output_tokens=100,
                cost=Decimal("0.002"),
            )
        )
        
        tracker = UsageTracker(
            user_id="user-123",
            debate_id="debate-123",
            provider="anthropic",
            model="claude-sonnet-4-5",
            usage_service=mock_usage_service,
        )
        
        # Simulate some prior output tokens
        tracker._totals.output_tokens = 1000
        
        with patch("modules.debates.usage_tracker.count_tokens", return_value=100):
            await tracker.record_synthesis_usage(full_content="Synthesis")
        
        # Verify the input_tokens includes prior output + overhead
        call_args = mock_usage_service.record_usage.call_args
        usage_record = call_args.kwargs["record"]
        # Input should be prior output (1000) + 500 overhead
        assert usage_record.input_tokens == 1500

    def test_uses_get_usage_service_by_default(self):
        """Should get usage service from module if not provided."""
        with patch("modules.debates.usage_tracker.get_usage_service") as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service
            
            tracker = UsageTracker(
                user_id="user-123",
                debate_id="debate-123",
                provider="anthropic",
                model="claude-sonnet-4-5",
            )
            
            mock_get.assert_called_once()
            assert tracker._usage_service == mock_service
