# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import warnings
from typing import Any

from src.ragme.agents.functional_agent import FunctionalAgent
from src.ragme.agents.query_agent import QueryAgent

# Set up logging
logger = logging.getLogger(__name__)

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based `config`.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Support for class-based `config`.*",
)


class RagMeAgent:
    """A dispatcher agent that routes queries to appropriate specialized agents."""

    def __init__(self, ragme_instance):
        """
        Initialize the RagMeAgent with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to vector database and methods
        """
        self.ragme = ragme_instance

        # Initialize the specialized agents
        self.functional_agent = FunctionalAgent(ragme_instance)
        self.query_agent = QueryAgent(ragme_instance)

    async def run(self, query: str):
        """
        Route a query to the appropriate agent based on its type.

        Args:
            query (str): The query to process

        Returns:
            The response from the appropriate agent
        """
        logger.info(f"RagMeAgent received query: '{query}'")

        # Determine which agent should handle this query
        if self.functional_agent.is_functional_query(query):
            logger.info(f"Routing query to FunctionalAgent: '{query}'")
            # Route to functional agent for tool-based operations
            return await self.functional_agent.run(query)
        elif self.query_agent.is_query_question(query):
            logger.info(f"Routing query to QueryAgent: '{query}'")
            # Route to query agent for content questions
            return await self.query_agent.run(query)
        else:
            logger.info(
                f"Query not matched by keywords, defaulting to QueryAgent: '{query}'"
            )
            # Default to query agent for unknown query types
            # This handles cases where the query might be a simple question
            # that doesn't match our keyword patterns
            return await self.query_agent.run(query)

    def get_agent_info(self) -> dict[str, Any]:
        """
        Get information about the available agents and their capabilities.

        Returns:
            dict: Information about the agents
        """
        return {
            "functional_agent": {
                "description": "Handles functional operations like adding, deleting, listing documents",
                "capabilities": [
                    "Add URLs to collection",
                    "Delete documents",
                    "List documents",
                    "Reset collection",
                    "Crawl webpages",
                    "Get vector database info",
                ],
            },
            "query_agent": {
                "description": "Answers questions about document content using vector search",
                "capabilities": [
                    "Search document content",
                    "Answer questions about documents",
                    "Provide document summaries",
                    "Find relevant information",
                ],
            },
        }
