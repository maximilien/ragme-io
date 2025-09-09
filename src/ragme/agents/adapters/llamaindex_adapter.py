# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
from typing import Any, Dict, Optional

from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from ..abstract_agent import AbstractAgent
from ...utils.config_manager import config

# Set up logging
logger = logging.getLogger(__name__)


class LlamaIndexAdapter(AbstractAgent):
    """
    Adapter for LlamaIndex-based agents.
    
    This adapter provides a wrapper around LlamaIndex agent functionality
    to conform to the AbstractAgent interface.
    """

    def __init__(
        self,
        name: str,
        role: str,
        llm_model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        tools: Optional[list] = None,
        agent_class: str = "FunctionAgent",
        **kwargs
    ):
        """Initialize LlamaIndex adapter."""
        super().__init__(
            name=name,
            role=role,
            agent_type="llamaindex",
            llm_model=llm_model,
            system_prompt=system_prompt,
            env=env
        )
        
        # Get LLM configuration
        llm_config = config.get_llm_config()
        temperature = llm_config.get("temperature", 0.7)
        
        # Get language settings
        self.preferred_language = config.get_preferred_language()
        self.language_name = config.get_language_name(self.preferred_language)
        
        # Initialize OpenAI LLM
        self.llm = OpenAI(model=llm_model, temperature=temperature)
        
        # Store tools and agent class
        self.tools = tools or []
        self.agent_class = agent_class
        
        # Initialize the LlamaIndex agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized LlamaIndex adapter for agent '{name}' with role '{role}' using {agent_class}")

    def _create_agent(self):
        """Create the appropriate LlamaIndex agent based on configuration."""
        try:
            if self.agent_class == "ReActAgent":
                # Initialize memory for ReActAgent
                memory = ChatMemoryBuffer.from_defaults(
                    token_limit=4000,
                    llm=self.llm
                )
                
                # Create ReActAgent with tools and memory
                agent = ReActAgent.from_tools(
                    tools=self.tools,
                    llm=self.llm,
                    memory=memory,
                    system_prompt=self.system_prompt,
                    verbose=True
                )
                
            elif self.agent_class == "FunctionAgent":
                # Create FunctionAgent with tools
                agent = FunctionAgent(
                    tools=self.tools,
                    llm=self.llm,
                    system_prompt=self.system_prompt,
                    verbose=True
                )
                
            else:
                # Default to FunctionAgent
                logger.warning(f"Unknown agent class '{self.agent_class}', defaulting to FunctionAgent")
                agent = FunctionAgent(
                    tools=self.tools,
                    llm=self.llm,
                    system_prompt=self.system_prompt,
                    verbose=True
                )
            
            return agent
            
        except Exception as e:
            logger.error(f"Error creating LlamaIndex agent: {str(e)}")
            raise

    async def run(self, query: str, **kwargs) -> str:
        """
        Run the LlamaIndex agent with a query.
        
        Args:
            query: The user query
            **kwargs: Additional arguments
            
        Returns:
            str: The agent's response
        """
        try:
            # Use the LlamaIndex agent to process the query
            response = await self.agent.achat(query)
            return str(response)
            
        except Exception as e:
            logger.error(f"Error in LlamaIndex adapter '{self.name}': {str(e)}")
            return f"Error processing query: {str(e)}"

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the LlamaIndex agent."""
        return {
            "name": self.name,
            "role": self.role,
            "type": self.agent_type,
            "model": self.llm_model,
            "agent_class": self.agent_class,
            "description": f"LlamaIndex-based {self.agent_class} with role '{self.role}'",
            "capabilities": [
                "Tool-based operations",
                "Function calling",
                "Memory management" if self.agent_class == "ReActAgent" else "Stateless operations",
                "Multi-step reasoning"
            ],
            "tools_count": len(self.tools),
            "language": self.language_name,
            "has_system_prompt": bool(self.system_prompt),
            "environment": list(self.env.keys()) if self.env else []
        }

    def cleanup(self):
        """Clean up LlamaIndex adapter resources."""
        try:
            if hasattr(self, 'agent'):
                self.agent = None
            if hasattr(self, 'llm'):
                self.llm = None
            logger.info(f"LlamaIndex adapter '{self.name}' cleanup completed")
        except Exception as e:
            logger.error(f"Error during LlamaIndex adapter cleanup: {str(e)}")