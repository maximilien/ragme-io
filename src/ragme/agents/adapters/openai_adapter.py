# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
from typing import Any, Dict, Optional

from llama_index.llms.openai import OpenAI

from ..abstract_agent import AbstractAgent
from ...utils.config_manager import config

# Set up logging
logger = logging.getLogger(__name__)


class OpenAIAdapter(AbstractAgent):
    """
    Adapter for OpenAI-based agents.
    
    This adapter provides a wrapper around OpenAI LLM functionality
    to conform to the AbstractAgent interface.
    """

    def __init__(
        self,
        name: str,
        role: str,
        llm_model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize OpenAI adapter."""
        super().__init__(
            name=name,
            role=role, 
            agent_type="openai",
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
        
        logger.info(f"Initialized OpenAI adapter for agent '{name}' with role '{role}'")

    async def run(self, query: str, **kwargs) -> str:
        """
        Run the OpenAI agent with a query.
        
        Args:
            query: The user query
            **kwargs: Additional arguments
            
        Returns:
            str: The agent's response
        """
        try:
            # Build the prompt with system prompt if available
            if self.system_prompt:
                # Build language instruction based on i18n configuration
                language_instruction = f"\nIMPORTANT: You are a helpful assistant that only responds in {self.language_name}. You MUST ALWAYS respond in {self.language_name}, regardless of the language used in the user's query."
                
                full_prompt = f"{self.system_prompt}{language_instruction}\n\nUser query: {query}"
            else:
                full_prompt = query
            
            # Use the OpenAI LLM to generate response
            response = await self.llm.acomplete(full_prompt)
            return str(response)
            
        except Exception as e:
            logger.error(f"Error in OpenAI adapter '{self.name}': {str(e)}")
            return f"Error processing query: {str(e)}"

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the OpenAI agent."""
        return {
            "name": self.name,
            "role": self.role,
            "type": self.agent_type,
            "model": self.llm_model,
            "description": f"OpenAI-based agent with role '{self.role}'",
            "capabilities": [
                "Text generation",
                "Query completion",
                "Language understanding",
                "Conversational AI"
            ],
            "language": self.language_name,
            "has_system_prompt": bool(self.system_prompt),
            "environment": list(self.env.keys()) if self.env else []
        }

    def cleanup(self):
        """Clean up OpenAI adapter resources."""
        try:
            if hasattr(self, 'llm'):
                self.llm = None
            logger.info(f"OpenAI adapter '{self.name}' cleanup completed")
        except Exception as e:
            logger.error(f"Error during OpenAI adapter cleanup: {str(e)}")