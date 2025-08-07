# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import warnings

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from src.ragme.agents.tools import RagMeTools
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


class FunctionalAgent:
    """A functional agent that handles tool-based operations using LlamaIndex FunctionAgent."""

    def __init__(self, ragme_instance):
        """
        Initialize the FunctionalAgent with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to vector database and methods
        """
        self.ragme = ragme_instance
        self.tools = RagMeTools(ragme_instance)

        # Get agent configuration
        agent_config = config.get_agent_config("functional-agent")
        llm_model = (
            agent_config.get("llm_model", "gpt-4o-mini")
            if agent_config
            else "gpt-4o-mini"
        )

        # Get LLM configuration
        llm_config = config.get_llm_config()
        temperature = llm_config.get("temperature", 0.7)

        self.llm = OpenAI(model=llm_model, temperature=temperature)
        self.agent = self._create_agent()

    def _create_agent(self):
        """
        Create the functional agent with tools for managing the RagMeDocs collection.
        """
        return FunctionAgent(
            tools=self.tools.get_all_tools(),
            llm=self.llm,
            system_prompt="""You are a helpful assistant that can perform functional operations on the RagMeDocs collection.

You can perform the following operations:
- Add URLs to the collection using write_to_ragme_collection(urls)
- List documents in the collection using list_ragme_collection(limit, offset)
- Delete specific documents using delete_document(doc_id)
- Delete documents by URL using delete_document_by_url(url)
- Delete all documents using delete_all_documents()
- Delete documents by pattern using delete_documents_by_pattern(pattern)
- Reset the collection using delete_ragme_collection()
- Find URLs by crawling webpages using find_urls_crawling_webpage(start_url, max_pages)
- Get vector database information using get_vector_db_info()

For functional queries like:
- "add this URL to my collection"
- "delete document with ID 123"
- "delete document https://example.com"
- "list all documents"
- "delete all documents matching pattern test_*"
- "reset the collection"

Use the appropriate tool to perform the requested operation.

When deleting documents:
- If the user provides a URL, use delete_document_by_url(url)
- If the user provides an ID, use delete_document(doc_id)
- If the user provides a pattern, use delete_documents_by_pattern(pattern)

DO NOT answer questions about document content - that should be handled by the QueryAgent.
Focus only on functional operations that modify or query the collection structure.
""",
        )

    async def run(self, query: str):
        """
        Run a functional query through the agent.

        Args:
            query (str): The functional query to process

        Returns:
            The response from the agent
        """
        logger.info(f"FunctionalAgent received query: '{query}'")

        try:
            logger.info(
                f"FunctionalAgent calling FunctionAgent.run with query: '{query}'"
            )
            # Use the simple approach that was working before
            response = await self.agent.run(query)
            logger.info(
                f"FunctionalAgent got response: {type(response)} - {str(response)[:100]}..."
            )

            return str(response)
        except Exception as e:
            logger.error(f"FunctionalAgent error: {str(e)}")
            return f"Error executing functional operation: {str(e)}"

    def is_functional_query(self, query: str) -> bool:
        """
        Determine if a query is functional (should be handled by this agent).

        Args:
            query (str): The user query

        Returns:
            bool: True if the query is functional, False otherwise
        """
        functional_keywords = [
            "add",
            "delete",
            "remove",
            "list",
            "show",
            "reset",
            "clear",
            "upload",
            "import",
            "export",
            "crawl",
            "find urls",
            "collection",
            "documents",
            "docs",
            "urls",
        ]

        query_lower = query.lower()
        is_functional = any(keyword in query_lower for keyword in functional_keywords)
        logger.info(f"FunctionalAgent.is_functional_query('{query}') = {is_functional}")
        return is_functional
