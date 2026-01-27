"""
LangChain callback handlers for usage tracking.

Provides callback-based token usage tracking for both streaming and
non-streaming LLM calls. These handlers capture actual usage metadata
from LLM API responses instead of relying on estimation.

Usage:
    # For non-streaming calls (ainvoke)
    callback = UsageTrackingCallback()
    response = await llm.ainvoke(messages, config={"callbacks": [callback]})
    usage = callback.get_usage()
    
    # For streaming calls (astream)
    tracker = StreamingUsageTracker()
    async for chunk in llm.astream(messages, config={"callbacks": [tracker.callback]}):
        tracker.process_chunk(chunk)
    usage = tracker.get_usage()
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


@dataclass
class UsageMetadata:
    """Captured usage metadata from an LLM call."""
    
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    
    def __bool__(self) -> bool:
        """Returns True if any usage was captured."""
        return self.input_tokens > 0 or self.output_tokens > 0


class UsageTrackingCallback(BaseCallbackHandler):
    """
    Callback handler that captures usage metadata from LLM responses.
    
    Works with both streaming and non-streaming LLM calls. The usage
    metadata is extracted from LLMResult.llm_output in on_llm_end().
    
    Attributes:
        usage: Captured usage metadata (None until on_llm_end is called)
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._usage: UsageMetadata | None = None
        self._run_id: UUID | None = None
    
    @property
    def usage(self) -> UsageMetadata | None:
        """Get the captured usage metadata."""
        return self._usage
    
    def get_usage(self) -> tuple[int, int]:
        """
        Get usage as a tuple of (input_tokens, output_tokens).
        
        Returns:
            Tuple of (input_tokens, output_tokens), or (0, 0) if not captured.
        """
        if self._usage:
            return (self._usage.input_tokens, self._usage.output_tokens)
        return (0, 0)
    
    def reset(self) -> None:
        """Reset the callback for reuse."""
        self._usage = None
        self._run_id = None
    
    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts. Captures run_id for correlation."""
        self._run_id = run_id
        self._usage = None
    
    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when chat model starts. Captures run_id for correlation."""
        self._run_id = run_id
        self._usage = None
    
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """
        Called when LLM completes. Extracts usage metadata from response.
        
        The usage metadata location varies by provider:
        - OpenAI/OpenAI-compatible: response.llm_output["token_usage"]
        - Anthropic: response.llm_output["usage"]
        - Some providers: response.generations[0][0].message.usage_metadata
        """
        self._extract_usage_from_result(response)
    
    def _extract_usage_from_result(self, response: LLMResult) -> None:
        """Extract usage metadata from LLMResult."""
        usage = UsageMetadata()
        
        # Try llm_output first (most providers)
        if response.llm_output:
            # OpenAI-style: token_usage
            if "token_usage" in response.llm_output:
                token_usage = response.llm_output["token_usage"]
                usage.input_tokens = token_usage.get("prompt_tokens", 0)
                usage.output_tokens = token_usage.get("completion_tokens", 0)
                usage.total_tokens = token_usage.get("total_tokens", 0)
            # Anthropic-style: usage
            elif "usage" in response.llm_output:
                llm_usage = response.llm_output["usage"]
                usage.input_tokens = llm_usage.get("input_tokens", 0)
                usage.output_tokens = llm_usage.get("output_tokens", 0)
                usage.cache_creation_input_tokens = llm_usage.get(
                    "cache_creation_input_tokens", 0
                )
                usage.cache_read_input_tokens = llm_usage.get(
                    "cache_read_input_tokens", 0
                )
                usage.total_tokens = usage.input_tokens + usage.output_tokens
        
        # Fallback: Try to get from generation message metadata
        if not usage and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "message") and hasattr(gen.message, "usage_metadata"):
                        msg_usage = gen.message.usage_metadata
                        if msg_usage:
                            usage.input_tokens = msg_usage.get("input_tokens", 0)
                            usage.output_tokens = msg_usage.get("output_tokens", 0)
                            usage.total_tokens = msg_usage.get("total_tokens", 0)
                            break
                if usage:
                    break
        
        if usage:
            self._usage = usage
            logger.debug(
                f"Captured usage: input={usage.input_tokens}, "
                f"output={usage.output_tokens}"
            )
        else:
            logger.debug("No usage metadata found in LLM response")


class StreamingUsageTracker:
    """
    Tracks usage metadata from streaming LLM responses.
    
    Accumulates content from streaming chunks and extracts usage metadata
    from the final chunk (which typically contains the usage information).
    
    Usage:
        tracker = StreamingUsageTracker()
        async for chunk in llm.astream(messages, config={"callbacks": [tracker.callback]}):
            tracker.process_chunk(chunk)
            # ... use chunk.content
        usage = tracker.get_usage()
    """
    
    def __init__(self) -> None:
        self._callback = UsageTrackingCallback()
        self._usage: UsageMetadata | None = None
        self._accumulated_content: str = ""
        self._chunk_count: int = 0
    
    @property
    def callback(self) -> UsageTrackingCallback:
        """Get the underlying callback handler to pass to LLM calls."""
        return self._callback
    
    @property
    def accumulated_content(self) -> str:
        """Get the accumulated response content."""
        return self._accumulated_content
    
    @property
    def chunk_count(self) -> int:
        """Get the number of chunks processed."""
        return self._chunk_count
    
    def process_chunk(self, chunk: Any) -> None:
        """
        Process a streaming chunk.
        
        Accumulates content and checks for usage_metadata on the chunk.
        Usage metadata is typically present on the final chunk.
        
        Args:
            chunk: An AIMessageChunk from llm.astream()
        """
        self._chunk_count += 1
        
        # Accumulate content
        if hasattr(chunk, "content") and chunk.content:
            self._accumulated_content += chunk.content
        
        # Check for usage_metadata on chunk (final chunk often has this)
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            usage_dict = chunk.usage_metadata
            self._usage = UsageMetadata(
                input_tokens=usage_dict.get("input_tokens", 0),
                output_tokens=usage_dict.get("output_tokens", 0),
                total_tokens=usage_dict.get("total_tokens", 0),
            )
            logger.debug(
                f"Captured streaming usage from chunk: "
                f"input={self._usage.input_tokens}, output={self._usage.output_tokens}"
            )
    
    def get_usage(self) -> tuple[int, int]:
        """
        Get usage as a tuple of (input_tokens, output_tokens).
        
        Checks chunk-level usage first, then falls back to callback usage.
        
        Returns:
            Tuple of (input_tokens, output_tokens), or (0, 0) if not captured.
        """
        # Prefer chunk-level usage (more reliable for streaming)
        if self._usage:
            return (self._usage.input_tokens, self._usage.output_tokens)
        
        # Fallback to callback usage
        return self._callback.get_usage()
    
    def get_usage_metadata(self) -> UsageMetadata | None:
        """
        Get the full usage metadata object.
        
        Returns:
            UsageMetadata if captured, None otherwise.
        """
        if self._usage:
            return self._usage
        return self._callback.usage
    
    def reset(self) -> None:
        """Reset the tracker for reuse."""
        self._callback.reset()
        self._usage = None
        self._accumulated_content = ""
        self._chunk_count = 0
