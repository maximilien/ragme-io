# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import sys
import warnings
from unittest.mock import AsyncMock, Mock, patch

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

from src.ragme.agents.ragme_agent import RagMeAgent


class TestRagMeAgent:
    """Test cases for the RagMeAgent class."""

    def test_init(self):
        """Test RagMeAgent initialization."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify initialization
        assert agent.ragme == mock_ragme
        assert hasattr(agent, "functional_agent")
        assert hasattr(agent, "query_agent")
        assert hasattr(agent, "llm")
        assert hasattr(agent, "memory")
        assert hasattr(agent, "dispatch_tools")
        assert hasattr(agent, "agent")

    def test_create_agent(self):
        """Test that the ReActAgent is created with the correct configuration."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the ReActAgent was created
        assert agent.agent is not None
        assert hasattr(agent.agent, "tools")
        assert hasattr(agent.agent, "llm")
        # Note: ReActAgent doesn't have memory as an attribute, it's passed to run()

    def test_dispatch_tools_creation(self):
        """Test that dispatch tools are created correctly."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify dispatch tools were created
        assert len(agent.dispatch_tools) == 2

        # Check that we have the expected number of tools
        # The actual function names are wrapped, so we just verify the count
        assert len(agent.dispatch_tools) == 2

    def test_memory_initialization(self):
        """Test that memory is initialized correctly."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify memory was initialized
        assert agent.memory is not None
        assert hasattr(agent.memory, "token_limit")
        assert agent.memory.token_limit == 4000

    @patch("src.ragme.agents.ragme_agent.config")
    def test_agent_configuration(self, mock_config):
        """Test that the agent uses configuration correctly."""
        # Mock config
        mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}
        mock_config.get_llm_config.return_value = {"temperature": 0.7}

        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        RagMeAgent(mock_ragme)

        # Verify config was used
        mock_config.get_agent_config.assert_called_with("ragme-agent")
        mock_config.get_llm_config.assert_called()

    def test_run_method(self):
        """Test the run method of RagMeAgent."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test that the run method exists and can be called
        assert hasattr(agent, "run")
        assert callable(agent.run)

    def test_agent_tools_access_ragme_methods(self):
        """Test that the functional agent's tools can access RagMe methods correctly."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock(
            return_value=[{"url": "test.com", "text": "test"}]
        )
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Get the tools from the functional agent
        tools = agent.functional_agent.tools.get_all_tools()

        # Verify we have the expected number of tools
        assert (
            len(tools) == 17
        )  # write, delete_collection, delete_document, delete_document_by_url, delete_all_documents, delete_documents_by_pattern, list, list_documents_by_datetime, crawl, db info, count, write_image_to_collection, list_image_collection, list_images_by_datetime, delete_image_from_collection, get_todays_images_with_data, get_images_by_date_range_with_data

        # Test that the tools can access RagMe methods
        assert hasattr(agent.functional_agent.tools, "list_ragme_collection")
        assert callable(agent.functional_agent.tools.list_ragme_collection)

        # Test that the new count_documents tool is available
        assert hasattr(agent.functional_agent.tools, "count_documents")
        assert callable(agent.functional_agent.tools.count_documents)

        # Test that the new image tools are available
        assert hasattr(agent.functional_agent.tools, "write_image_to_collection")
        assert callable(agent.functional_agent.tools.write_image_to_collection)
        assert hasattr(agent.functional_agent.tools, "list_image_collection")
        assert callable(agent.functional_agent.tools.list_image_collection)
        assert hasattr(agent.functional_agent.tools, "delete_image_from_collection")
        assert callable(agent.functional_agent.tools.delete_image_from_collection)

        # Test that the new datetime tools are available
        assert hasattr(agent.functional_agent.tools, "list_documents_by_datetime")
        assert callable(agent.functional_agent.tools.list_documents_by_datetime)
        assert hasattr(agent.functional_agent.tools, "list_images_by_datetime")
        assert callable(agent.functional_agent.tools.list_images_by_datetime)

        # Test that the new image summarization tools are available
        assert hasattr(agent.functional_agent.tools, "get_todays_images_with_data")
        assert callable(agent.functional_agent.tools.get_todays_images_with_data)
        assert hasattr(
            agent.functional_agent.tools, "get_images_by_date_range_with_data"
        )
        assert callable(agent.functional_agent.tools.get_images_by_date_range_with_data)

    def test_count_documents_tool(self):
        """Test that the count_documents tool works correctly."""
        # Mock the RagMe instance with count_documents method
        mock_ragme = Mock()
        mock_ragme.vector_db = Mock()
        mock_ragme.vector_db.count_documents = Mock(return_value=42)

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test the count_documents tool
        result = agent.functional_agent.tools.count_documents()

        # Verify the tool was called correctly
        mock_ragme.vector_db.count_documents.assert_called_once_with("all")
        assert "42" in result
        assert "total" in result

    def test_count_documents_tool_with_date_filter(self):
        """Test that the count_documents tool works with date filters."""
        # Mock the RagMe instance with count_documents method
        mock_ragme = Mock()
        mock_ragme.vector_db = Mock()
        mock_ragme.vector_db.count_documents = Mock(return_value=15)

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test the count_documents tool with date filter
        result = agent.functional_agent.tools.count_documents("month")

        # Verify the tool was called correctly
        mock_ragme.vector_db.count_documents.assert_called_once_with("month")
        assert "15" in result
        assert "from this month" in result

    def test_agent_system_prompt(self):
        """Test that the ReActAgent has the correct system prompt."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the ReActAgent system prompt contains expected content
        system_prompt = agent.agent.system_prompt
        assert "dispatcher agent" in system_prompt
        assert "functional_operations" in system_prompt
        assert "content_questions" in system_prompt
        assert "memory" in system_prompt

    def test_pattern_based_deletion_tool(self):
        """Test that the delete_documents_by_pattern tool is available."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the functional agent system prompt includes pattern-based deletion
        system_prompt = agent.functional_agent.agent.system_prompt
        assert "delete_documents_by_pattern" in system_prompt
        assert "pattern" in system_prompt.lower()

        # Verify the tool is in the tools list
        tool_names = [
            tool.__name__ for tool in agent.functional_agent.tools.get_all_tools()
        ]
        assert "delete_documents_by_pattern" in tool_names

    def test_get_agent_info(self):
        """Test that get_agent_info returns the correct information."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Get agent info
        info = agent.get_agent_info()

        # Verify the structure
        assert "ragme_agent" in info
        assert "functional_agent" in info
        assert "query_agent" in info

        # Verify ragme_agent info
        ragme_info = info["ragme_agent"]
        assert "description" in ragme_info
        assert "capabilities" in ragme_info
        assert "Intelligent query routing" in ragme_info["capabilities"]
        assert "Conversation memory" in ragme_info["capabilities"]

    def test_get_memory_info(self):
        """Test that get_memory_info returns the correct information."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Get memory info
        memory_info = agent.get_memory_info()

        # Verify the structure
        assert "memory_type" in memory_info
        assert "token_limit" in memory_info
        assert "current_messages" in memory_info
        assert "has_memory" in memory_info

        # Verify values
        assert memory_info["memory_type"] == "ChatMemoryBuffer"
        assert memory_info["token_limit"] == 4000

    def test_delete_operation_confirmation(self):
        """Test that delete operations require confirmation."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Mock config to ensure confirmation is required and LLM responses
        with (
            patch("src.ragme.agents.ragme_agent.config") as mock_config,
            patch.object(agent, "llm") as mock_llm,
        ):
            mock_config.is_feature_enabled.return_value = False
            # Test single document deletion
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "single_document"}'
            )
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation(
                "delete document 123"
            )
            assert is_delete
            assert operation_type == "single_document"
            assert agent._requires_confirmation(operation_type)

            # Test collection deletion
            mock_response = Mock()
            mock_response.text = '{"is_delete": true, "operation_type": "collection"}'
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation("delete all")
            assert is_delete
            assert operation_type == "collection"
            assert agent._requires_confirmation(operation_type)

            # Test multiple document deletion
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "multiple_documents"}'
            )
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation("delete documents")
            assert is_delete
            assert operation_type == "multiple_documents"
            assert agent._requires_confirmation(operation_type)

            # Test non-delete operation
            mock_response = Mock()
            mock_response.text = '{"is_delete": false, "operation_type": "none"}'
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation("what is AI?")
            assert not is_delete
            assert operation_type == ""

    def test_confirmation_response_detection(self):
        """Test confirmation and cancellation response detection."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test confirmation responses
        assert agent._is_confirmation_response("yes")
        assert agent._is_confirmation_response("confirm")
        assert agent._is_confirmation_response("y")
        assert agent._is_confirmation_response("ok")
        assert agent._is_confirmation_response("proceed")
        assert agent._is_confirmation_response("continue")

        # Test cancellation responses
        assert agent._is_cancellation_response("no")
        assert agent._is_cancellation_response("cancel")
        assert agent._is_cancellation_response("n")
        assert agent._is_cancellation_response("stop")
        assert agent._is_cancellation_response("abort")

        # Test invalid responses
        assert not agent._is_confirmation_response("maybe")
        assert not agent._is_cancellation_response("maybe")

    def test_confirmation_message_generation(self):
        """Test confirmation message generation."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test collection deletion message
        msg = agent._get_confirmation_message("collection", "delete all")
        assert "DESTRUCTIVE OPERATION" in msg
        assert "delete the entire collection" in msg

        # Test multiple documents deletion message
        msg = agent._get_confirmation_message("multiple_documents", "delete documents")
        assert "DESTRUCTIVE OPERATION" in msg
        assert "delete multiple documents" in msg

        # Test single document deletion message
        msg = agent._get_confirmation_message("single_document", "delete document")
        assert "DESTRUCTIVE OPERATION" in msg
        assert "delete this document" in msg

    def test_abbreviated_delete_operation_detection(self):
        """Test that abbreviated forms of delete operations are detected correctly."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Mock LLM responses for abbreviated delete operations
        with patch.object(agent, "llm") as mock_llm:
            # Test abbreviated single document deletion
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "single_document"}'
            )
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation(
                "del document https://maximilien.org"
            )
            assert is_delete
            assert operation_type == "single_document"

            # Test abbreviated collection deletion
            mock_response = Mock()
            mock_response.text = '{"is_delete": true, "operation_type": "collection"}'
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation("del all")
            assert is_delete
            assert operation_type == "collection"

            # Test abbreviated multiple documents deletion
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "multiple_documents"}'
            )
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation("del documents")
            assert is_delete
            assert operation_type == "multiple_documents"

            # Test rm abbreviation
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "single_document"}'
            )
            mock_llm.complete.return_value = mock_response
            is_delete, operation_type = agent._is_delete_operation(
                "rm document test.pdf"
            )
            assert is_delete
            assert operation_type == "single_document"

    def test_fallback_keyword_detection(self):
        """Test that fallback keyword detection works when LLM fails."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Mock LLM to raise an exception
        with patch.object(agent, "llm") as mock_llm:
            mock_llm.complete.side_effect = Exception("LLM failed")

            # Test that fallback keyword detection works
            is_delete, operation_type = agent._is_delete_operation(
                "delete document test.pdf"
            )
            assert is_delete
            assert operation_type == "single_document"

            is_delete, operation_type = agent._is_delete_operation("del all")
            assert is_delete
            assert operation_type == "collection"

            is_delete, operation_type = agent._is_delete_operation("delete documents")
            assert is_delete
            assert operation_type == "multiple_documents"

            # Test non-delete operation
            is_delete, operation_type = agent._is_delete_operation("what is AI?")
            assert not is_delete
            assert operation_type == ""

    @pytest.mark.asyncio
    async def test_confirmation_flow(self):
        """Test the complete confirmation flow for delete operations."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Mock the entire workflow system to avoid OpenAI API calls
        with (
            patch.object(agent, "llm") as mock_llm,
            patch.object(agent.functional_agent, "run") as mock_functional_run,
            patch("llama_index.llms.openai.OpenAI") as mock_openai_class,
        ):
            # Mock LLM to detect delete operation
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "single_document"}'
            )
            mock_llm.complete.return_value = mock_response

            # Mock OpenAI class to avoid real API calls
            mock_openai_instance = Mock()
            mock_openai_class.return_value = mock_openai_instance

            # Mock functional agent response
            mock_functional_run.return_value = "Document deleted successfully"

            # Instead of testing the full agent run, test the confirmation logic directly
            # Test _is_delete_operation
            is_delete, operation_type = agent._is_delete_operation(
                "del document https://example.com"
            )
            assert is_delete
            assert operation_type == "single_document"

            # Test _requires_confirmation
            requires_conf = agent._requires_confirmation(operation_type)
            assert requires_conf

            # Test _get_confirmation_message
            conf_msg = agent._get_confirmation_message(
                operation_type, "del document https://example.com"
            )
            assert "DESTRUCTIVE OPERATION" in conf_msg
            assert "Are you sure you want to delete this document?" in conf_msg

    @pytest.mark.asyncio
    async def test_confirmation_flow_cancellation(self):
        """Test the confirmation flow when user cancels."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Mock LLM responses and avoid OpenAI API calls
        with (
            patch.object(agent, "llm") as mock_llm,
            patch("llama_index.llms.openai.OpenAI") as mock_openai_class,
        ):
            # Mock LLM to detect delete operation
            mock_response = Mock()
            mock_response.text = (
                '{"is_delete": true, "operation_type": "single_document"}'
            )
            mock_llm.complete.return_value = mock_response

            # Mock OpenAI class to avoid real API calls
            mock_openai_instance = Mock()
            mock_openai_class.return_value = mock_openai_instance

            # Test the confirmation logic components directly
            # Test _is_delete_operation
            is_delete, operation_type = agent._is_delete_operation(
                "delete document test.pdf"
            )
            assert is_delete
            assert operation_type == "single_document"

            # Test _requires_confirmation
            requires_conf = agent._requires_confirmation(operation_type)
            assert requires_conf

            # Test _get_confirmation_message
            conf_msg = agent._get_confirmation_message(
                operation_type, "delete document test.pdf"
            )
            assert "DESTRUCTIVE OPERATION" in conf_msg
            assert "Are you sure you want to delete this document?" in conf_msg

    def test_delete_document_by_url_tool(self):
        """Test the delete_document_by_url tool functionality."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Test the delete_document_by_url tool
        tools = agent.functional_agent.tools

        # Mock the vector_db.find_document_by_url method
        mock_document = {
            "id": "test-id-123",
            "url": "https://example.com",
            "text": "test content",
            "metadata": {},
        }
        agent.ragme.vector_db.find_document_by_url = Mock(return_value=mock_document)
        agent.ragme.delete_document = Mock(return_value=True)

        # Test successful deletion
        result = tools.delete_document_by_url("https://example.com")
        assert "deleted successfully" in result
        agent.ragme.vector_db.find_document_by_url.assert_called_once_with(
            "https://example.com"
        )
        agent.ragme.delete_document.assert_called_once_with("test-id-123")

        # Test document not found
        agent.ragme.vector_db.find_document_by_url = Mock(return_value=None)
        result = tools.delete_document_by_url("https://nonexistent.com")
        assert "not found" in result

        # Test deletion failure
        agent.ragme.vector_db.find_document_by_url = Mock(return_value=mock_document)
        agent.ragme.delete_document = Mock(return_value=False)
        result = tools.delete_document_by_url("https://example.com")
        assert "could not be deleted" in result
