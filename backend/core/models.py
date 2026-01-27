"""Pydantic models for the debate core module.

These models define structured data types used by the debate graph nodes.
"""

from pydantic import BaseModel


class ConsensusResult(BaseModel):
    """Structured result from consensus checking.

    This model is used with LangChain's JsonOutputParser to parse
    LLM responses when checking for consensus between personalities.

    Attributes:
        consensus: Whether the personalities have reached substantial agreement.
        reasoning: Brief explanation of why consensus was or was not reached.
    """

    consensus: bool
    reasoning: str
