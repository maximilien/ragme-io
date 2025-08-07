# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import warnings
from typing import Any

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI

from src.ragme.agents.functional_agent import FunctionalAgent
from src.ragme.agents.query_agent import QueryAgent
from src.ragme.utils.config_manager import config

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
    """A dispatcher agent that routes queries to appropriate specialized agents using LlamaIndex ReActAgent with memory."""

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

        # Get agent configuration
        agent_config = config.get_agent_config("ragme-agent")
        llm_model = (
            agent_config.get("llm_model", "gpt-4o-mini")
            if agent_config
            else "gpt-4o-mini"
        )

        # Get LLM configuration
        llm_config = config.get_llm_config()
        temperature = llm_config.get("temperature", 0.7)

        # Initialize LLM
        self.llm = OpenAI(model=llm_model, temperature=temperature)

        # Initialize memory
        self.memory = ChatMemoryBuffer.from_defaults(
            token_limit=4000,
            llm=self.llm,  # Adjust based on your needs
        )

        # Initialize confirmation tracking
        self.confirmation_state = {
            "pending_delete_operation": None,
            "confirmed_delete_operations": set(),  # Track confirmed operations in this session
        }

        # Create dispatch tools
        self.dispatch_tools = self._create_dispatch_tools()

        # Create the ReActAgent
        self.agent = self._create_agent()

    def _is_delete_operation(self, query: str) -> tuple[bool, str]:
        """
        Check if a query is a delete operation and return the operation type using LLM.

        Args:
            query (str): The user query

        Returns:
            tuple[bool, str]: (is_delete_operation, operation_type)
        """
        try:
            # Use LLM to determine if this is a delete operation
            prompt = f"""Analyze the following user query and determine if it's a delete operation.

Query: "{query}"

Respond with ONLY a JSON object in this exact format:
{{
    "is_delete": true/false,
    "operation_type": "single_document" | "multiple_documents" | "collection" | "none"
}}

Rules:
- "single_document": Deleting one specific document (e.g., "delete document X", "del doc Y", "remove file Z")
- "multiple_documents": Deleting multiple documents or documents by pattern (e.g., "delete documents", "delete by pattern", "delete all PDFs")
- "collection": Deleting entire collection or all documents (e.g., "delete all", "reset collection", "clear everything")
- "none": Not a delete operation

Examples:
- "delete document https://example.com" → {{"is_delete": true, "operation_type": "single_document"}}
- "del doc test.pdf" → {{"is_delete": true, "operation_type": "single_document"}}
- "delete documents" → {{"is_delete": true, "operation_type": "multiple_documents"}}
- "delete all" → {{"is_delete": true, "operation_type": "collection"}}
- "what is AI?" → {{"is_delete": false, "operation_type": "none"}}

JSON response:"""

            # Get LLM response
            response = self.llm.complete(prompt)
            response_text = response.text.strip()

            # Extract JSON from response
            import json
            import re

            # Try to find JSON in the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                is_delete = result.get("is_delete", False)
                operation_type = result.get("operation_type", "none")

                # Map "none" to empty string for consistency
                if operation_type == "none":
                    operation_type = ""

                logger.info(
                    f"LLM detected delete operation: {is_delete}, type: {operation_type}"
                )
                return is_delete, operation_type
            else:
                logger.warning(
                    f"Could not parse JSON from LLM response: {response_text}"
                )
                return False, ""

        except Exception as e:
            logger.error(f"Error using LLM for delete operation detection: {str(e)}")
            # Fallback to keyword matching if LLM fails
            return self._fallback_keyword_detection(query)

    def _fallback_keyword_detection(self, query: str) -> tuple[bool, str]:
        """
        Fallback keyword-based detection if LLM fails.

        Args:
            query (str): The user query

        Returns:
            tuple[bool, str]: (is_delete_operation, operation_type)
        """
        query_lower = query.lower()

        # Check for collection deletion
        if any(
            phrase in query_lower
            for phrase in [
                "delete collection",
                "del collection",
                "reset collection",
                "clear collection",
                "delete all",
                "del all",
                "clear all",
                "reset all",
                "delete everything",
                "del everything",
            ]
        ):
            return True, "collection"

        # Check for multiple document deletion
        if any(
            phrase in query_lower
            for phrase in [
                "delete documents",
                "del documents",
                "delete docs",
                "del docs",
                "delete multiple",
                "del multiple",
                "delete by pattern",
                "del by pattern",
                "delete matching",
                "del matching",
            ]
        ):
            return True, "multiple_documents"

        # Check for single document deletion
        if any(
            phrase in query_lower
            for phrase in [
                "delete document",
                "del document",
                "delete doc",
                "del doc",
                "remove document",
                "rm document",
                "remove doc",
                "rm doc",
            ]
        ):
            return True, "single_document"

        return False, ""

    def _requires_confirmation(self, operation_type: str) -> bool:
        """
        Determine if an operation requires confirmation.

        Args:
            operation_type (str): The type of delete operation

        Returns:
            bool: True if confirmation is required
        """
        # Always require confirmation for collection and multiple document deletions
        if operation_type in ["collection", "multiple_documents"]:
            return True

        # For single document deletion, check if it's already been confirmed in this session
        if operation_type == "single_document":
            # Single document deletions only need confirmation once per session
            return (
                "single_document"
                not in self.confirmation_state["confirmed_delete_operations"]
            )

        return False

    def _get_confirmation_message(self, operation_type: str, query: str) -> str:
        """
        Generate a confirmation message for delete operations.

        Args:
            operation_type (str): The type of delete operation
            query (str): The original user query

        Returns:
            str: The confirmation message
        """
        if operation_type == "collection":
            return "⚠️ **DESTRUCTIVE OPERATION** ⚠️\n\nAre you sure you want to delete the entire collection? This will permanently remove all documents and cannot be undone.\n\nPlease confirm by typing 'yes' or 'confirm' to proceed, or 'no' to cancel."

        elif operation_type == "multiple_documents":
            return "⚠️ **DESTRUCTIVE OPERATION** ⚠️\n\nAre you sure you want to delete multiple documents? This operation cannot be undone.\n\nPlease confirm by typing 'yes' or 'confirm' to proceed, or 'no' to cancel."

        elif operation_type == "single_document":
            return "⚠️ **DESTRUCTIVE OPERATION** ⚠️\n\nAre you sure you want to delete this document? This operation cannot be undone.\n\nPlease confirm by typing 'yes' or 'confirm' to proceed, or 'no' to cancel."

        return ""

    def _is_confirmation_response(self, response: str) -> bool:
        """
        Check if a response is a confirmation.

        Args:
            response (str): The user response

        Returns:
            bool: True if it's a confirmation
        """
        response_lower = response.lower().strip()
        return response_lower in ["yes", "confirm", "y", "ok", "proceed", "continue"]

    def _is_cancellation_response(self, response: str) -> bool:
        """
        Check if a response is a cancellation.

        Args:
            response (str): The user response

        Returns:
            bool: True if it's a cancellation
        """
        response_lower = response.lower().strip()
        return response_lower in ["no", "cancel", "n", "stop", "abort"]

    def _create_dispatch_tools(self) -> list[FunctionTool]:
        """Create tools for dispatching to specialized agents."""

        async def dispatch_to_functional_agent(query: str) -> str:
            """Dispatch a query to the FunctionalAgent for tool-based operations.

            Use this tool when the user wants to:
            - Add URLs to the collection
            - Delete documents
            - List documents
            - Reset the collection
            - Crawl webpages
            - Get vector database info
            - Any other functional operations that modify the collection
            """
            logger.info(f"Dispatching to FunctionalAgent: '{query}'")
            return await self.functional_agent.run(query)

        async def dispatch_to_query_agent(query: str) -> str:
            """Dispatch a query to the QueryAgent for content-based questions.

            Use this tool when the user asks questions about:
            - Document content
            - Information in the stored documents
            - Summaries of documents
            - Any questions that require searching through document content
            """
            logger.info(f"Dispatching to QueryAgent: '{query}'")
            return await self.query_agent.run(query)

        return [
            FunctionTool.from_defaults(
                fn=dispatch_to_functional_agent,
                name="functional_operations",
                description="Use this tool for functional operations like adding URLs, deleting documents, listing documents, resetting the collection, crawling webpages, or getting vector database information.",
            ),
            FunctionTool.from_defaults(
                fn=dispatch_to_query_agent,
                name="content_questions",
                description="Use this tool for questions about document content, information in stored documents, or any queries that require searching through the document collection.",
            ),
        ]

    def _create_agent(self) -> ReActAgent:
        """Create the ReActAgent with memory and dispatch tools."""

        system_prompt = """You are a helpful assistant that can perform two types of operations:

1. FUNCTIONAL OPERATIONS: Use the functional_operations tool for:
   - Adding URLs to the collection
   - Deleting documents
   - List documents
   - Reset the collection
   - Crawl webpages
   - Get vector database info
   - Any operations that modify or manage the document collection

2. CONTENT QUESTIONS: Use the content_questions tool for:
   - Questions about document content
   - Information in stored documents
   - Summaries of documents
   - Any queries that require searching through document content

You have access to conversation memory, so you can reference previous context and maintain continuity in conversations.

IMPORTANT RULES:
- For ANY question about documents, content, or information, use the content_questions tool
- For ANY operation that modifies the collection (add, delete, list, reset, crawl), use the functional_operations tool
- Use your memory to maintain context across multiple queries
- If a user refers to previous context, use that information to provide better responses
- Always be helpful and provide clear explanations of what you're doing
- Delete operations are handled automatically with confirmation - just use the functional_operations tool

Examples:
- "Add this URL to my collection" → use functional_operations
- "What does the document say about AI?" → use content_questions
- "Delete all documents" → use functional_operations
- "Summarize the main points" → use content_questions
"""

        return ReActAgent(
            name="RagMeAgent",
            description="A dispatcher agent that routes queries to appropriate specialized agents",
            system_prompt=system_prompt,
            tools=self.dispatch_tools,
            llm=self.llm,
        )

    async def run(self, query: str):
        """
        Route a query to the appropriate agent using the ReActAgent with memory.

        Args:
            query (str): The query to process

        Returns:
            The response from the appropriate agent
        """
        logger.info(f"RagMeAgent received query: '{query}'")

        try:
            # Check if we have a pending confirmation first
            if self.confirmation_state["pending_delete_operation"]:
                # User is responding to a confirmation request
                if self._is_confirmation_response(query):
                    # User confirmed - proceed with the operation
                    pending_op = self.confirmation_state["pending_delete_operation"]
                    self.confirmation_state["pending_delete_operation"] = None

                    # Determine the operation type for the pending operation
                    _, operation_type = self._is_delete_operation(pending_op)

                    # Mark this operation type as confirmed for this session
                    if operation_type == "single_document":
                        self.confirmation_state["confirmed_delete_operations"].add(
                            "single_document"
                        )

                    # Execute the pending operation directly with FunctionalAgent
                    logger.info(f"User confirmed delete operation: {pending_op}")
                    return await self.functional_agent.run(pending_op)

                elif self._is_cancellation_response(query):
                    # User cancelled - clear pending operation
                    self.confirmation_state["pending_delete_operation"] = None
                    return "❌ Delete operation cancelled."

                else:
                    # Invalid response - ask again
                    return "Please respond with 'yes' to confirm or 'no' to cancel."

            # Check if this is a delete operation that requires confirmation
            is_delete, operation_type = self._is_delete_operation(query)

            if is_delete and self._requires_confirmation(operation_type):
                # First time requesting this delete operation - ask for confirmation
                confirmation_msg = self._get_confirmation_message(operation_type, query)
                self.confirmation_state["pending_delete_operation"] = query
                return confirmation_msg

            # Clear any pending confirmation if this is not a delete operation and not a confirmation response
            if (
                not is_delete
                and not self._is_confirmation_response(query)
                and not self._is_cancellation_response(query)
            ):
                self.confirmation_state["pending_delete_operation"] = None

            # Use the ReActAgent to intelligently dispatch the query with memory
            response = await self.agent.run(query, memory=self.memory)
            logger.info(
                f"RagMeAgent got response: {type(response)} - {str(response)[:100]}..."
            )

            return str(response)
        except Exception as e:
            logger.error(f"RagMeAgent error: {str(e)}")
            return f"Error processing query: {str(e)}"

    def reset_confirmation_state(self):
        """
        Reset the confirmation state (useful for new chat sessions).
        """
        self.confirmation_state = {
            "pending_delete_operation": None,
            "confirmed_delete_operations": set(),
        }

    def get_agent_info(self) -> dict[str, Any]:
        """
        Get information about the available agents and their capabilities.

        Returns:
            dict: Information about the agents
        """
        return {
            "ragme_agent": {
                "description": "Main dispatcher agent with memory that intelligently routes queries to specialized agents",
                "capabilities": [
                    "Intelligent query routing",
                    "Conversation memory",
                    "Context awareness",
                    "Functional operations via FunctionalAgent",
                    "Content questions via QueryAgent",
                    "Delete operation confirmation",
                ],
            },
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

    def get_memory_info(self) -> dict[str, Any]:
        """
        Get information about the agent's memory.

        Returns:
            dict: Information about the memory
        """
        try:
            # Get the current memory contents
            memory_messages = self.memory.get()
            return {
                "memory_type": "ChatMemoryBuffer",
                "token_limit": self.memory.token_limit,
                "current_messages": len(memory_messages),
                "has_memory": len(memory_messages) > 0,
                "confirmation_state": self.confirmation_state,
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {str(e)}")
            return {"memory_type": "ChatMemoryBuffer", "error": str(e)}
