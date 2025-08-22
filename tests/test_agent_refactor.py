# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import asyncio
import os
import sys
import warnings
from unittest.mock import Mock, patch

import pytest

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

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.agents.functional_agent import FunctionalAgent
from src.ragme.agents.query_agent import QueryAgent
from src.ragme.agents.ragme_agent import RagMeAgent
from src.ragme.agents.tools import RagMeTools


class TestAgentRefactor:
    """Test cases for the refactored agent architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the RagMe instance
        self.mock_ragme = Mock()
        self.mock_ragme.vector_db = Mock()
        self.mock_ragme.list_documents = Mock()
        self.mock_ragme.delete_document = Mock()
        self.mock_ragme.write_webpages_to_weaviate = Mock()

    def test_ragme_tools_initialization(self):
        """Test that RagMeTools initializes correctly."""
        tools = RagMeTools(self.mock_ragme)
        assert tools.ragme == self.mock_ragme
        assert hasattr(tools, "write_to_ragme_collection")
        assert hasattr(tools, "list_ragme_collection")
        assert hasattr(tools, "delete_document")

    def test_ragme_tools_get_all_tools(self):
        """Test that get_all_tools returns the expected number of tools."""
        tools = RagMeTools(self.mock_ragme)
        all_tools = tools.get_all_tools()
        assert (
            len(all_tools) == 15
        )  # 15 tools: write, delete_collection, delete_document, delete_document_by_url, delete_all_documents, delete_documents_by_pattern, get_document_details, write_to_ragme_collection, get_vector_db_info, count_documents, list_documents_by_datetime, write_image_to_collection, list_image_collection, list_images_by_datetime, delete_image_from_collection

    def test_functional_agent_initialization(self):
        """Test that FunctionalAgent initializes correctly."""
        agent = FunctionalAgent(self.mock_ragme)
        assert agent.ragme == self.mock_ragme
        assert hasattr(agent, "tools")
        assert hasattr(agent, "llm")
        assert hasattr(agent, "agent")

    def test_functional_agent_is_functional_query(self):
        """Test that is_functional_query correctly identifies functional queries."""
        agent = FunctionalAgent(self.mock_ragme)

        # Test functional queries
        assert agent.is_functional_query("add this URL to my collection")
        assert agent.is_functional_query("list all documents")
        assert agent.is_functional_query("delete document 123")
        assert agent.is_functional_query("reset the collection")

        # Test non-functional queries
        assert not agent.is_functional_query("who is maximilien")
        assert not agent.is_functional_query("what is the content of this document")

    def test_query_agent_initialization(self):
        """Test that QueryAgent initializes correctly."""
        agent = QueryAgent(self.mock_ragme.vector_db)
        assert agent.vector_db == self.mock_ragme.vector_db
        assert hasattr(agent, "llm")
        assert hasattr(agent, "top_k")

    def test_query_agent_is_query_question(self):
        """Test that is_query_question correctly identifies question queries."""
        agent = QueryAgent(self.mock_ragme.vector_db)

        # Test question queries
        assert agent.is_query_question("who is maximilien")
        assert agent.is_query_question("what is the content of this document")
        assert agent.is_query_question("tell me about the project")
        assert agent.is_query_question("explain the architecture")

        # Test non-question queries
        assert not agent.is_query_question("add this URL")
        assert not agent.is_query_question("delete document 123")

    def test_ragme_agent_initialization(self):
        """Test that RagMeAgent initializes correctly as a dispatcher."""
        agent = RagMeAgent(self.mock_ragme)
        assert agent.ragme == self.mock_ragme
        assert hasattr(agent, "functional_agent")
        assert hasattr(agent, "query_agent")
        assert isinstance(agent.functional_agent, FunctionalAgent)
        assert isinstance(agent.query_agent, QueryAgent)

    def test_ragme_agent_get_agent_info(self):
        """Test that get_agent_info returns correct information."""
        agent = RagMeAgent(self.mock_ragme)
        info = agent.get_agent_info()

        assert "functional_agent" in info
        assert "query_agent" in info
        assert "description" in info["functional_agent"]
        assert "capabilities" in info["functional_agent"]
        assert "description" in info["query_agent"]
        assert "capabilities" in info["query_agent"]

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    async def test_functional_agent_run(self, mock_openai, mock_function_agent):
        """Test that FunctionalAgent.run calls the underlying FunctionAgent correctly."""
        # Mock the FunctionAgent response
        mock_response = "Successfully added URL to collection"
        mock_agent_instance = Mock()

        # Create an async mock for run
        async def mock_run(query):
            return mock_response

        mock_agent_instance.run = mock_run
        mock_function_agent.return_value = mock_agent_instance

        agent = FunctionalAgent(self.mock_ragme)
        result = await agent.run("add this URL to my collection")

        assert "Successfully added URL to collection" in result

    @pytest.mark.asyncio
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_query_agent_run_with_documents(self, mock_openai):
        """Test that QueryAgent.run works correctly when documents are found."""
        # Mock vector database methods
        mock_documents = [
            {
                "url": "https://maximilien.org",
                "text": "Maximilien is a software engineer who works on AI projects.",
                "metadata": {"filename": "maximilien.org"},
                "score": 0.95,
            }
        ]
        self.mock_ragme.vector_db.has_text_collection.return_value = True
        self.mock_ragme.vector_db.has_image_collection.return_value = False
        self.mock_ragme.vector_db.search_text_collection.return_value = mock_documents
        self.mock_ragme.vector_db.search_image_collection.return_value = []

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.complete.return_value = Mock(
            text="Maximilien is a software engineer who works on AI projects."
        )
        mock_openai.return_value = mock_llm

        agent = QueryAgent(self.mock_ragme.vector_db)
        result = await agent.run("who is maximilien")

        assert "Based on the stored documents" in result
        assert "https://maximilien.org" in result
        assert "Maximilien is a software engineer" in result

    @pytest.mark.asyncio
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_query_agent_run_no_documents(self, mock_openai):
        """Test that QueryAgent.run handles the case when no documents are found."""
        # Mock vector database methods
        self.mock_ragme.vector_db.has_text_collection.return_value = True
        self.mock_ragme.vector_db.has_image_collection.return_value = False
        self.mock_ragme.vector_db.search_text_collection.return_value = []
        self.mock_ragme.vector_db.search_image_collection.return_value = []

        agent = QueryAgent(self.mock_ragme.vector_db)
        result = await agent.run("who is maximilien")

        assert "couldn't find any relevant information" in result

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_ragme_agent_dispatch_to_functional(
        self, mock_query_openai, mock_func_openai, mock_function_agent
    ):
        """Test that RagMeAgent correctly dispatches functional queries to FunctionalAgent."""
        # Mock the FunctionalAgent response
        mock_response = "Successfully added URL to collection"
        mock_agent_instance = Mock()

        # Create an async mock for run
        async def mock_run(query):
            return mock_response

        mock_agent_instance.run = mock_run
        mock_function_agent.return_value = mock_agent_instance

        # Mock the LLM responses
        mock_llm = Mock()
        mock_llm.complete.return_value = Mock(
            text='{"is_delete": false, "operation_type": "none"}'
        )
        mock_func_openai.return_value = mock_llm
        mock_query_openai.return_value = mock_llm

        # Create agent and then patch its LLM
        agent = RagMeAgent(self.mock_ragme)
        agent.llm.complete = mock_llm.complete

        result = await agent.run("add this URL to my collection")

        assert "Successfully added URL to collection" in result

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_ragme_agent_dispatch_to_query(
        self, mock_query_openai, mock_func_openai, mock_function_agent
    ):
        """Test that RagMeAgent correctly dispatches question queries to QueryAgent."""
        # Mock vector database methods
        mock_documents = [
            {
                "url": "https://maximilien.org",
                "text": "Maximilien is a software engineer who works on AI projects.",
                "metadata": {"filename": "maximilien.org"},
                "score": 0.95,
            }
        ]
        self.mock_ragme.vector_db.has_text_collection.return_value = True
        self.mock_ragme.vector_db.has_image_collection.return_value = False
        self.mock_ragme.vector_db.search_text_collection.return_value = mock_documents
        self.mock_ragme.vector_db.search_image_collection.return_value = []

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.complete.return_value = Mock(
            text="Maximilien is a software engineer who works on AI projects."
        )
        mock_query_openai.return_value = mock_llm
        mock_func_openai.return_value = mock_llm

        # Create agent and then patch its LLM
        agent = RagMeAgent(self.mock_ragme)
        agent.llm.complete = mock_llm.complete

        result = await agent.run("who is maximilien")

        # The response should contain either the formatted response or the direct answer
        assert (
            "Based on the stored documents" in result
            or "Maximilien is a software engineer" in result
        )
        assert "https://maximilien.org" in result


class TestAgentIntegration:
    """Integration tests for the refactored agent architecture."""

    def setup_method(self):
        """Set up test fixtures for integration tests."""
        # Mock the RagMe instance with more realistic behavior
        self.mock_ragme = Mock()
        self.mock_ragme.vector_db = Mock()
        self.mock_ragme.list_documents = Mock()
        self.mock_ragme.delete_document = Mock()
        self.mock_ragme.write_webpages_to_weaviate = Mock()

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_integration_functional_agent_add_and_delete(
        self, mock_query_openai, mock_func_openai, mock_function_agent
    ):
        """Integration test: Test adding a document and then deleting it using FunctionalAgent."""
        # Mock the FunctionAgent responses
        mock_add_response = "Successfully added 1 URLs to the collection"
        mock_delete_response = "Document test_doc_123 deleted successfully"

        mock_agent_instance = Mock()

        # Create an async mock for run with side effects
        responses = [mock_add_response, mock_delete_response]
        response_index = [0]

        async def mock_run(query):
            response = responses[response_index[0]]
            response_index[0] += 1
            return response

        mock_agent_instance.run = mock_run
        mock_function_agent.return_value = mock_agent_instance

        agent = FunctionalAgent(self.mock_ragme)

        # Test adding a document
        add_result = await agent.run("add https://maximilien.org to my collection")
        assert "Successfully added 1 URLs" in add_result

        # Test deleting a document
        delete_result = await agent.run("delete document test_doc_123")
        assert "Document test_doc_123 deleted successfully" in delete_result

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_integration_query_agent_with_added_document(
        self, mock_query_openai, mock_func_openai, mock_function_agent
    ):
        """Integration test: Test adding a URL and then querying about it."""
        # Mock the FunctionalAgent for adding document
        mock_add_response = "Successfully added 1 URLs to the collection"
        mock_func_agent_instance = Mock()

        # Create an async mock for run
        async def mock_run(query):
            return mock_add_response

        mock_func_agent_instance.run = mock_run
        mock_function_agent.return_value = mock_func_agent_instance

        # Mock vector database methods
        mock_documents = [
            {
                "url": "https://maximilien.org",
                "text": "Maximilien is a software engineer who works on AI projects and has expertise in machine learning and natural language processing.",
                "metadata": {"filename": "maximilien.org"},
                "score": 0.95,
            }
        ]
        self.mock_ragme.vector_db.has_text_collection.return_value = True
        self.mock_ragme.vector_db.has_image_collection.return_value = False
        self.mock_ragme.vector_db.search_text_collection.return_value = mock_documents
        self.mock_ragme.vector_db.search_image_collection.return_value = []

        # Mock LLM response for query
        mock_llm = Mock()
        mock_llm.complete.return_value = Mock(
            text="Maximilien is a software engineer who works on AI projects and has expertise in machine learning and natural language processing."
        )
        mock_query_openai.return_value = mock_llm

        # Test the full flow
        functional_agent = FunctionalAgent(self.mock_ragme)
        query_agent = QueryAgent(self.mock_ragme.vector_db)

        # Add document
        add_result = await functional_agent.run(
            "add https://maximilien.org to my collection"
        )
        assert "Successfully added 1 URLs" in add_result

        # Query about the document
        query_result = await query_agent.run("who is maximilien")
        assert "Based on the stored documents" in query_result
        assert "https://maximilien.org" in query_result
        assert "software engineer" in query_result.lower()

    @pytest.mark.asyncio
    @patch("src.ragme.agents.functional_agent.FunctionAgent")
    @patch("src.ragme.agents.functional_agent.OpenAI")
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_integration_ragme_agent_dispatch(
        self, mock_query_openai, mock_func_openai, mock_function_agent
    ):
        """Integration test: Test that RagMeAgent correctly dispatches different types of queries."""
        # Mock the FunctionalAgent responses
        mock_func_response = "Successfully added 1 URLs to the collection"
        mock_func_agent_instance = Mock()

        # Create an async mock for run
        async def mock_run(query):
            return mock_func_response

        mock_func_agent_instance.run = mock_run
        mock_function_agent.return_value = mock_func_agent_instance

        # Mock vector database methods
        mock_documents = [
            {
                "url": "https://maximilien.org",
                "text": "Maximilien is a software engineer who works on AI projects.",
                "metadata": {"filename": "maximilien.org"},
                "score": 0.95,
            }
        ]
        self.mock_ragme.vector_db.has_text_collection.return_value = True
        self.mock_ragme.vector_db.has_image_collection.return_value = False
        self.mock_ragme.vector_db.search_text_collection.return_value = mock_documents
        self.mock_ragme.vector_db.search_image_collection.return_value = []

        # Mock LLM response for query
        mock_llm = Mock()
        mock_llm.complete.return_value = Mock(
            text="Maximilien is a software engineer who works on AI projects."
        )
        mock_query_openai.return_value = mock_llm

        agent = RagMeAgent(self.mock_ragme)

        # Test functional query dispatch
        func_result = await agent.run("add https://maximilien.org to my collection")
        assert "Successfully added 1 URLs" in func_result

        # Test query dispatch
        query_result = await agent.run("who is maximilien")
        assert "Based on the stored documents" in query_result
        assert "https://maximilien.org" in query_result
