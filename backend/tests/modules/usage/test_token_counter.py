"""Tests for token counting utilities."""

import pytest

from modules.usage.token_counter import (
    count_tokens,
    count_message_tokens,
    estimate_output_tokens,
    estimate_input_tokens,
    get_encoder,
    reset_encoder_cache,
)


class TestCountTokens:
    """Tests for count_tokens function."""

    def test_empty_string_returns_zero(self):
        """Empty string should return 0 tokens."""
        assert count_tokens("") == 0

    def test_none_like_empty_returns_zero(self):
        """Empty-like strings should return 0."""
        assert count_tokens("") == 0

    def test_simple_text_returns_positive(self):
        """Simple text should return positive token count."""
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10  # Should be around 4 tokens

    def test_longer_text_returns_more_tokens(self):
        """Longer text should return more tokens."""
        short = count_tokens("Hello")
        long = count_tokens("Hello, this is a much longer sentence with many more words.")
        assert long > short

    def test_model_parameter_accepted(self):
        """Should accept different model names."""
        # All these should work without error
        count_tokens("Test", model="gpt-4")
        count_tokens("Test", model="claude-3-5-sonnet")
        count_tokens("Test", model="gemini-1.5-pro")
        count_tokens("Test", model="llama-3-70b")

    def test_consistent_results(self):
        """Same input should return same token count."""
        text = "The quick brown fox jumps over the lazy dog."
        assert count_tokens(text) == count_tokens(text)

    def test_unicode_text(self):
        """Should handle Unicode text."""
        tokens = count_tokens("Hello, 世界! 🌍")
        assert tokens > 0

    def test_newlines_and_whitespace(self):
        """Should handle newlines and whitespace."""
        text = "Line 1\nLine 2\n\nLine 4"
        tokens = count_tokens(text)
        assert tokens > 0


class TestCountMessageTokens:
    """Tests for count_message_tokens function."""

    def test_empty_messages_returns_overhead_only(self):
        """Empty message list should return just the priming overhead."""
        tokens = count_message_tokens([])
        assert tokens == 2  # Priming overhead

    def test_single_message(self):
        """Single message should include content plus overhead."""
        messages = [{"role": "user", "content": "Hello"}]
        tokens = count_message_tokens(messages)
        assert tokens > 4  # At least overhead

    def test_multiple_messages(self):
        """Multiple messages should accumulate."""
        single = count_message_tokens([{"role": "user", "content": "Hello"}])
        double = count_message_tokens([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ])
        assert double > single

    def test_chat_conversation(self):
        """Should handle typical chat conversation."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
        ]
        tokens = count_message_tokens(messages)
        assert tokens > 10  # Reasonable token count for this conversation


class TestEstimateOutputTokens:
    """Tests for estimate_output_tokens function."""

    def test_delegates_to_count_tokens(self):
        """Should return same as count_tokens."""
        text = "This is a test response from the model."
        assert estimate_output_tokens(text) == count_tokens(text)

    def test_empty_returns_zero(self):
        """Empty content should return 0."""
        assert estimate_output_tokens("") == 0


class TestGetEncoder:
    """Tests for encoder caching."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_encoder_cache()

    def test_returns_encoder(self):
        """Should return a tiktoken encoder."""
        encoder = get_encoder("gpt-4")
        assert encoder is not None
        assert hasattr(encoder, "encode")

    def test_caches_encoder(self):
        """Should cache encoder for repeated calls."""
        encoder1 = get_encoder("gpt-4")
        encoder2 = get_encoder("gpt-4")
        assert encoder1 is encoder2

    def test_same_encoding_for_similar_models(self):
        """Similar models should use same encoding."""
        gpt4 = get_encoder("gpt-4")
        claude = get_encoder("claude-3-5-sonnet")
        assert gpt4 is claude  # Both use cl100k_base


class TestResetEncoderCache:
    """Tests for cache reset."""

    def test_reset_clears_internal_cache(self):
        """Reset should clear the internal cache dict."""
        # Import the internal cache to verify it's cleared
        from modules.usage import token_counter
        
        # Populate cache
        get_encoder("gpt-4")
        assert len(token_counter._encoders) > 0
        
        # Reset
        reset_encoder_cache()
        
        # Internal cache should be empty
        assert len(token_counter._encoders) == 0


class TestEstimateInputTokens:
    """Tests for estimate_input_tokens function."""

    def test_counts_question_tokens(self):
        """Should count tokens in question."""
        result = estimate_input_tokens("Hello, how are you?")
        question_tokens = count_tokens("Hello, how are you?")
        # Result includes question + default overhead (200) + message overhead (10)
        assert result == question_tokens + 200 + 10

    def test_uses_system_prompt_tokens_when_provided(self):
        """Should use actual system prompt tokens instead of default."""
        question = "What is 2+2?"
        system_prompt = "You are a math tutor."
        
        result = estimate_input_tokens(question, system_prompt=system_prompt)
        
        expected = (
            count_tokens(question) +
            count_tokens(system_prompt) +
            10  # Message overhead
        )
        assert result == expected

    def test_adds_prior_context_tokens(self):
        """Should add tokens for prior context."""
        question = "What is 2+2?"
        prior_context = "In the previous round, we discussed addition."
        
        result = estimate_input_tokens(question, prior_context=prior_context)
        
        expected = (
            count_tokens(question) +
            200 +  # Default system overhead
            count_tokens(prior_context) +
            10  # Message overhead
        )
        assert result == expected

    def test_combines_all_components(self):
        """Should combine question, system prompt, and context."""
        question = "What is the meaning of life?"
        system_prompt = "You are a philosopher."
        prior_context = "Previous perspectives discussed happiness."
        
        result = estimate_input_tokens(
            question,
            system_prompt=system_prompt,
            prior_context=prior_context,
        )
        
        expected = (
            count_tokens(question) +
            count_tokens(system_prompt) +
            count_tokens(prior_context) +
            10  # Message overhead
        )
        assert result == expected

    def test_accepts_custom_default_overhead(self):
        """Should accept custom default system overhead."""
        question = "Test"
        
        result = estimate_input_tokens(
            question,
            default_system_overhead=500,
        )
        
        expected = count_tokens(question) + 500 + 10
        assert result == expected

    def test_accepts_model_parameter(self):
        """Should accept model parameter for tokenizer."""
        question = "Test"
        
        # Should work without error for different models
        estimate_input_tokens(question, model="gpt-4")
        estimate_input_tokens(question, model="claude-3-5-sonnet")
        estimate_input_tokens(question, model="gemini-1.5-pro")

    def test_empty_question_returns_overhead_only(self):
        """Empty question should return just overhead."""
        result = estimate_input_tokens("")
        # Default overhead (200) + message overhead (10)
        assert result == 210

    def test_returns_integer(self):
        """Should return an integer."""
        result = estimate_input_tokens("Test question")
        assert isinstance(result, int)
