"""Tests for usage tracking callbacks."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from langchain_core.outputs import LLMResult, Generation
from langchain_core.messages import AIMessage

from modules.usage.callback import (
    UsageMetadata,
    UsageTrackingCallback,
    StreamingUsageTracker,
)


class TestUsageMetadata:
    """Tests for the UsageMetadata dataclass."""

    def test_default_values(self):
        """Should have zero defaults."""
        metadata = UsageMetadata()
        assert metadata.input_tokens == 0
        assert metadata.output_tokens == 0
        assert metadata.total_tokens == 0
        assert metadata.cache_creation_input_tokens == 0
        assert metadata.cache_read_input_tokens == 0

    def test_custom_values(self):
        """Should accept custom values."""
        metadata = UsageMetadata(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
        )
        assert metadata.input_tokens == 100
        assert metadata.output_tokens == 200
        assert metadata.total_tokens == 300

    def test_bool_true_when_tokens_present(self):
        """Should return True when tokens are present."""
        assert bool(UsageMetadata(input_tokens=100))
        assert bool(UsageMetadata(output_tokens=100))
        assert bool(UsageMetadata(input_tokens=50, output_tokens=50))

    def test_bool_false_when_no_tokens(self):
        """Should return False when no tokens."""
        assert not bool(UsageMetadata())
        assert not bool(UsageMetadata(input_tokens=0, output_tokens=0))


class TestUsageTrackingCallback:
    """Tests for the UsageTrackingCallback class."""

    def test_initialization(self):
        """Should initialize with None usage."""
        callback = UsageTrackingCallback()
        assert callback.usage is None
        assert callback.get_usage() == (0, 0)

    def test_on_llm_start_resets_usage(self):
        """Should reset usage on LLM start."""
        callback = UsageTrackingCallback()
        callback._usage = UsageMetadata(input_tokens=100, output_tokens=50)
        
        callback.on_llm_start(
            serialized={},
            prompts=["test"],
            run_id=uuid4(),
        )
        
        assert callback.usage is None

    def test_on_chat_model_start_resets_usage(self):
        """Should reset usage on chat model start."""
        callback = UsageTrackingCallback()
        callback._usage = UsageMetadata(input_tokens=100, output_tokens=50)
        
        callback.on_chat_model_start(
            serialized={},
            messages=[[]],
            run_id=uuid4(),
        )
        
        assert callback.usage is None

    def test_on_llm_end_extracts_openai_style_usage(self):
        """Should extract usage from OpenAI-style token_usage."""
        callback = UsageTrackingCallback()
        
        response = LLMResult(
            generations=[],
            llm_output={
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                    "total_tokens": 300,
                }
            },
        )
        
        callback.on_llm_end(response, run_id=uuid4())
        
        assert callback.usage is not None
        assert callback.usage.input_tokens == 100
        assert callback.usage.output_tokens == 200
        assert callback.usage.total_tokens == 300

    def test_on_llm_end_extracts_anthropic_style_usage(self):
        """Should extract usage from Anthropic-style usage dict."""
        callback = UsageTrackingCallback()
        
        response = LLMResult(
            generations=[],
            llm_output={
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 250,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 5,
                }
            },
        )
        
        callback.on_llm_end(response, run_id=uuid4())
        
        assert callback.usage is not None
        assert callback.usage.input_tokens == 150
        assert callback.usage.output_tokens == 250
        assert callback.usage.cache_creation_input_tokens == 10
        assert callback.usage.cache_read_input_tokens == 5

    def test_on_llm_end_handles_no_usage(self):
        """Should handle responses without usage metadata."""
        callback = UsageTrackingCallback()
        
        response = LLMResult(
            generations=[],
            llm_output={},
        )
        
        callback.on_llm_end(response, run_id=uuid4())
        
        # Usage should remain None or empty
        assert callback.get_usage() == (0, 0)

    def test_on_llm_end_handles_none_llm_output(self):
        """Should handle None llm_output."""
        callback = UsageTrackingCallback()
        
        response = LLMResult(
            generations=[],
            llm_output=None,
        )
        
        callback.on_llm_end(response, run_id=uuid4())
        
        assert callback.get_usage() == (0, 0)

    def test_get_usage_returns_tuple(self):
        """Should return (input_tokens, output_tokens) tuple."""
        callback = UsageTrackingCallback()
        callback._usage = UsageMetadata(input_tokens=100, output_tokens=200)
        
        result = callback.get_usage()
        
        assert result == (100, 200)

    def test_reset_clears_usage(self):
        """Should clear usage on reset."""
        callback = UsageTrackingCallback()
        callback._usage = UsageMetadata(input_tokens=100, output_tokens=200)
        callback._run_id = uuid4()
        
        callback.reset()
        
        assert callback.usage is None
        assert callback._run_id is None


class TestStreamingUsageTracker:
    """Tests for the StreamingUsageTracker class."""

    def test_initialization(self):
        """Should initialize with empty state."""
        tracker = StreamingUsageTracker()
        assert tracker.accumulated_content == ""
        assert tracker.chunk_count == 0
        assert tracker.callback is not None

    def test_process_chunk_accumulates_content(self):
        """Should accumulate content from chunks."""
        tracker = StreamingUsageTracker()
        
        chunk1 = MagicMock()
        chunk1.content = "Hello "
        chunk1.usage_metadata = None
        
        chunk2 = MagicMock()
        chunk2.content = "world!"
        chunk2.usage_metadata = None
        
        tracker.process_chunk(chunk1)
        tracker.process_chunk(chunk2)
        
        assert tracker.accumulated_content == "Hello world!"
        assert tracker.chunk_count == 2

    def test_process_chunk_extracts_usage_metadata(self):
        """Should extract usage_metadata from chunk."""
        tracker = StreamingUsageTracker()
        
        chunk = MagicMock()
        chunk.content = "test"
        chunk.usage_metadata = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        }
        
        tracker.process_chunk(chunk)
        
        input_tokens, output_tokens = tracker.get_usage()
        assert input_tokens == 100
        assert output_tokens == 50

    def test_process_chunk_handles_missing_content(self):
        """Should handle chunks without content."""
        tracker = StreamingUsageTracker()
        
        chunk = MagicMock()
        chunk.content = None
        chunk.usage_metadata = None
        
        tracker.process_chunk(chunk)
        
        assert tracker.accumulated_content == ""
        assert tracker.chunk_count == 1

    def test_process_chunk_handles_missing_usage_metadata(self):
        """Should handle chunks without usage_metadata attr."""
        tracker = StreamingUsageTracker()
        
        chunk = MagicMock(spec=["content"])  # No usage_metadata attr
        chunk.content = "test"
        
        tracker.process_chunk(chunk)
        
        assert tracker.accumulated_content == "test"
        assert tracker.get_usage() == (0, 0)

    def test_get_usage_prefers_chunk_usage(self):
        """Should prefer chunk-level usage over callback usage."""
        tracker = StreamingUsageTracker()
        
        # Set callback usage
        tracker._callback._usage = UsageMetadata(input_tokens=50, output_tokens=25)
        
        # Set chunk usage (should be preferred)
        chunk = MagicMock()
        chunk.content = ""
        chunk.usage_metadata = {"input_tokens": 100, "output_tokens": 75}
        tracker.process_chunk(chunk)
        
        # Chunk usage should be returned
        assert tracker.get_usage() == (100, 75)

    def test_get_usage_falls_back_to_callback(self):
        """Should fall back to callback usage if no chunk usage."""
        tracker = StreamingUsageTracker()
        tracker._callback._usage = UsageMetadata(input_tokens=50, output_tokens=25)
        
        assert tracker.get_usage() == (50, 25)

    def test_get_usage_metadata_returns_object(self):
        """Should return UsageMetadata object."""
        tracker = StreamingUsageTracker()
        
        chunk = MagicMock()
        chunk.content = ""
        chunk.usage_metadata = {"input_tokens": 100, "output_tokens": 75}
        tracker.process_chunk(chunk)
        
        metadata = tracker.get_usage_metadata()
        assert isinstance(metadata, UsageMetadata)
        assert metadata.input_tokens == 100
        assert metadata.output_tokens == 75

    def test_reset_clears_state(self):
        """Should reset all state."""
        tracker = StreamingUsageTracker()
        
        chunk = MagicMock()
        chunk.content = "test"
        chunk.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        tracker.process_chunk(chunk)
        
        tracker.reset()
        
        assert tracker.accumulated_content == ""
        assert tracker.chunk_count == 0
        assert tracker.get_usage() == (0, 0)

    def test_callback_property_returns_callback(self):
        """Should expose callback for passing to LLM."""
        tracker = StreamingUsageTracker()
        
        callback = tracker.callback
        
        assert isinstance(callback, UsageTrackingCallback)
