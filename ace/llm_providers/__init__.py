"""Production LLM client implementations for ACE."""

from typing import Optional
from .litellm_client import LiteLLMClient, LiteLLMConfig

try:
    from .langchain_client import LangChainLiteLLMClient as _LangChainLiteLLMClient

    LangChainLiteLLMClient: Optional[type] = _LangChainLiteLLMClient
except ImportError:
    LangChainLiteLLMClient: Optional[type] = None  # Optional dependency  # type: ignore

__all__ = [
    "LiteLLMClient",
    "LiteLLMConfig",
    "LangChainLiteLLMClient",
]
