"""
Agent implementations for RAGme.

This module provides various agent implementations including the main RAGme agent,
local file monitoring agent, and the new agent framework system with adapters.
"""

from .abstract_agent import AbstractAgent
from .adapters import CustomAdapter, LlamaIndexAdapter, OpenAIAdapter
from .agent_factory import AgentFactory
from .local_agent import RagMeLocalAgent
from .ragme_agent import RagMeAgent

__all__ = [
    "AbstractAgent",
    "AgentFactory",
    "RagMeAgent",
    "RagMeLocalAgent",
    "OpenAIAdapter",
    "LlamaIndexAdapter",
    "CustomAdapter",
]
