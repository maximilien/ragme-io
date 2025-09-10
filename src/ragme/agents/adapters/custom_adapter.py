# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
from typing import Any

from ..abstract_agent import AbstractAgent

# Set up logging
logger = logging.getLogger(__name__)


class CustomAdapter(AbstractAgent):
    """
    Adapter for custom agent implementations.

    This adapter provides a wrapper around custom agent classes that implement
    their own logic, allowing them to conform to the AbstractAgent interface.
    """

    def __init__(
        self,
        name: str,
        role: str,
        llm_model: str = "gpt-4o-mini",
        system_prompt: str | None = None,
        env: dict[str, Any] | None = None,
        custom_agent_instance: Any | None = None,
        **kwargs,
    ):
        """Initialize Custom adapter."""
        super().__init__(
            name=name,
            role=role,
            agent_type="custom",
            llm_model=llm_model,
            system_prompt=system_prompt,
            env=env,
        )

        # Store the custom agent instance
        self.custom_agent = custom_agent_instance

        logger.info(f"Initialized Custom adapter for agent '{name}' with role '{role}'")

    async def run(self, query: str, **kwargs) -> str:
        """
        Run the custom agent with a query.

        Args:
            query: The user query
            **kwargs: Additional arguments

        Returns:
            str: The agent's response
        """
        try:
            if not self.custom_agent:
                return f"No custom agent instance available for '{self.name}'"

            # Check if the custom agent has an async run method
            if hasattr(self.custom_agent, "run") and callable(self.custom_agent.run):
                # Try to call async version first
                if hasattr(self.custom_agent.run, "__code__") and "await" in str(
                    self.custom_agent.run.__code__.co_code
                ):
                    response = await self.custom_agent.run(query, **kwargs)
                else:
                    response = self.custom_agent.run(query, **kwargs)
                return str(response)

            # Check for other common method names
            elif hasattr(self.custom_agent, "process") and callable(
                self.custom_agent.process
            ):
                response = self.custom_agent.process(query, **kwargs)
                return str(response)

            elif hasattr(self.custom_agent, "query") and callable(
                self.custom_agent.query
            ):
                response = self.custom_agent.query(query, **kwargs)
                return str(response)

            else:
                return f"Custom agent '{self.name}' does not have a recognized execution method (run, process, query)"

        except Exception as e:
            logger.error(f"Error in Custom adapter '{self.name}': {str(e)}")
            return f"Error processing query: {str(e)}"

    def get_agent_info(self) -> dict[str, Any]:
        """Get information about the custom agent."""
        info = {
            "name": self.name,
            "role": self.role,
            "type": self.agent_type,
            "model": self.llm_model,
            "description": f"Custom agent implementation with role '{self.role}'",
            "capabilities": ["Custom logic implementation", "Flexible functionality"],
            "has_system_prompt": bool(self.system_prompt),
            "environment": list(self.env.keys()) if self.env else [],
            "has_instance": bool(self.custom_agent),
        }

        # Try to get additional info from the custom agent if it has a get_agent_info method
        if self.custom_agent and hasattr(self.custom_agent, "get_agent_info"):
            try:
                custom_info = self.custom_agent.get_agent_info()
                if isinstance(custom_info, dict):
                    info.update(custom_info)
            except Exception as e:
                logger.warning(f"Error getting custom agent info: {str(e)}")

        return info

    def cleanup(self):
        """Clean up custom adapter resources."""
        try:
            # Call cleanup on the custom agent if it has one
            if self.custom_agent and hasattr(self.custom_agent, "cleanup"):
                self.custom_agent.cleanup()

            self.custom_agent = None
            logger.info(f"Custom adapter '{self.name}' cleanup completed")
        except Exception as e:
            logger.error(f"Error during Custom adapter cleanup: {str(e)}")
