# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AbstractAgent(ABC):
    """
    Abstract base class defining the interface that all RAGme agents must implement.
    
    This interface provides a unified way to interact with different agent frameworks
    (OpenAI, LlamaIndex, Custom) while maintaining a consistent API.
    """

    def __init__(
        self,
        name: str,
        role: str,
        agent_type: str,
        llm_model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the agent with basic configuration.
        
        Args:
            name: The agent name
            role: The agent role (dispatch, functional, query, react, local)
            agent_type: The framework type (openai, llamaindex, custom)
            llm_model: The LLM model to use
            system_prompt: Optional system prompt
            env: Optional environment variables and configuration
        """
        self.name = name
        self.role = role
        self.agent_type = agent_type
        self.llm_model = llm_model
        self.system_prompt = system_prompt
        self.env = env or {}
        
    @abstractmethod
    async def run(self, query: str, **kwargs) -> str:
        """
        Run the agent with a query and return the response.
        
        Args:
            query: The user query or input
            **kwargs: Additional arguments specific to the agent
            
        Returns:
            str: The agent's response
        """
        pass

    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the agent's capabilities and configuration.
        
        Returns:
            dict: Agent information including description, capabilities, etc.
        """
        pass

    def cleanup(self):
        """
        Clean up resources when the agent is no longer needed.
        This method can be overridden by subclasses.
        """
        pass

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.name} ({self.role}/{self.agent_type})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"AbstractAgent(name='{self.name}', role='{self.role}', type='{self.agent_type}', model='{self.llm_model}')"