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
            system_prompt="""You are a helpful assistant that can perform functional operations on the RagMeDocs collection and RagMeImages collection.

IMPORTANT: When users ask to add URLs, extract ONLY the URL part from their request and pass it to the write_to_ragme_collection function.

You can perform the following operations:

TEXT DOCUMENTS:
- Add URLs to the collection using write_to_ragme_collection(urls) - IMPORTANT: Extract only the URL from user requests
- List documents in the collection using list_ragme_collection(limit, offset)
- Count documents in the collection using count_documents(date_filter)
- Delete specific documents using delete_document(doc_id)
- Delete documents by URL using delete_document_by_url(url)
- Delete all documents using delete_all_documents()
- Delete documents by pattern using delete_documents_by_pattern(pattern)
- Reset the collection using delete_ragme_collection()
- Find URLs by crawling webpages using find_urls_crawling_webpage(start_url, max_pages)

IMAGES:
- Add images from URLs to the image collection using write_image_to_collection(image_url)
- List images in the image collection using list_image_collection(limit, offset)
- Delete images from the collection using delete_image_from_collection(image_id)

GENERAL:
- Get vector database information using get_vector_db_info()

For functional queries like:
- "add maximilien.org" → call write_to_ragme_collection(["maximilien.org"])
- "add https://example.com" → call write_to_ragme_collection(["https://example.com"])
- "add this URL to my collection" → extract the URL and call write_to_ragme_collection([url])
- "add this image to the collection" or "add image from URL" → extract the image URL and call write_image_to_collection(image_url)
- "delete document with ID 123" → call delete_document("123")
- "delete image with ID abc" → call delete_image_from_collection("abc")
- "delete document https://example.com" → call delete_document_by_url("https://example.com")
- "list all documents" or "list all images" → call list_ragme_collection() or list_image_collection()
- "count documents" or "how many documents are there?" → call count_documents()
- "count documents from this week/month/year" → call count_documents("current"/"month"/"year")
- "delete all documents matching pattern test_*" → call delete_documents_by_pattern("test_*")
- "reset the collection" → call delete_ragme_collection()

Use the appropriate tool to perform the requested operation.

When counting documents:
- Use count_documents() for total count
- Use count_documents("current") for this week's documents
- Use count_documents("month") for this month's documents
- Use count_documents("year") for this year's documents

When deleting documents:
- If the user provides a URL, use delete_document_by_url(url)
- If the user provides an ID, use delete_document(doc_id)
- If the user provides a pattern, use delete_documents_by_pattern(pattern)

For images:
- When adding images, use write_image_to_collection(image_url) with the image URL
- When listing images, use list_image_collection(limit, offset)
- When deleting images, use delete_image_from_collection(image_id)

DO NOT answer questions about document content or image content - that should be handled by the QueryAgent.
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
            # Check if this is an "add URL" operation and handle it directly
            if self._is_add_url_query(query):
                return self._handle_add_url_directly(query)

            # Check if this is a "list" operation and handle it directly
            if self._is_list_query(query):
                return self._handle_list_directly(query)

            # Pre-process the query to extract URLs for add operations
            processed_query = self._preprocess_query(query)
            logger.info(
                f"FunctionalAgent calling FunctionAgent.run with processed query: '{processed_query}'"
            )

            # Use the simple approach that was working before
            response = await self.agent.run(processed_query)
            logger.info(
                f"FunctionalAgent got response: {type(response)} - {str(response)[:100]}..."
            )

            return str(response)
        except Exception as e:
            logger.error(f"FunctionalAgent error: {str(e)}")
            return f"Error executing functional operation: {str(e)}"

    def _is_add_url_query(self, query: str) -> bool:
        """Check if the query is asking to add a URL."""
        query_lower = query.lower().strip()
        return query_lower.startswith("add ") and not query_lower.startswith(
            "add image"
        )

    def _handle_add_url_directly(self, query: str) -> str:
        """Handle add URL operations directly without going through the LLM."""
        # Extract the URL part after "add "
        url_part = query[4:].strip()
        if not url_part:
            return "No URL provided. Please specify a URL to add."

        # Call the tool directly
        return self.tools.write_to_ragme_collection([url_part])

    def _is_list_query(self, query: str) -> bool:
        """Check if the query is asking to list something."""
        query_lower = query.lower().strip()
        return query_lower.startswith("list ")

    def _handle_list_directly(self, query: str) -> str:
        """Handle list operations directly without going through the LLM."""
        query_lower = query.lower().strip()

        # Extract what to list
        if "images" in query_lower or "image" in query_lower:
            logger.info("FunctionalAgent handling list images directly")
            return self.tools.list_image_collection(limit=10, offset=0)
        elif (
            "documents" in query_lower
            or "docs" in query_lower
            or "document" in query_lower
        ):
            logger.info("FunctionalAgent handling list documents directly")
            return self.tools.list_ragme_collection(limit=10, offset=0)
        else:
            # Default to listing documents if no specific type mentioned
            logger.info(
                "FunctionalAgent handling list (defaulting to documents) directly"
            )
            return self.tools.list_ragme_collection(limit=10, offset=0)

    def _preprocess_query(self, query: str) -> str:
        """
        Pre-process the query to extract URLs and make it easier for the LLM to understand.

        Args:
            query (str): The original query

        Returns:
            str: The processed query
        """
        query_lower = query.lower().strip()

        # Handle "add URL" patterns
        if query_lower.startswith("add "):
            # Extract the URL part after "add "
            url_part = query[4:].strip()
            if url_part:
                # Return a more explicit instruction
                return f"add URL: {url_part}"

        return query

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
