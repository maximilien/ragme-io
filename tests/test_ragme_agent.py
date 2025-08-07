# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

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

import os
import sys
from unittest.mock import Mock

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

    def test_create_agent(self):
        """Test that the agents are created with the correct configuration."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the agents were created
        assert agent.functional_agent is not None
        assert agent.query_agent is not None
        # The functional agent should have tools
        assert hasattr(agent.functional_agent, "tools")
        assert hasattr(agent.functional_agent, "agent")

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
        # We can't easily mock the FunctionAgent's run method, so we'll just test the interface
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
            len(tools) == 8
        )  # write, delete_collection, delete_document, delete_all_documents, delete_documents_by_pattern, list, crawl, db info

        # Test that the tools can access RagMe methods
        assert hasattr(agent.functional_agent.tools, "list_ragme_collection")
        assert callable(agent.functional_agent.tools.list_ragme_collection)

    def test_agent_system_prompt(self):
        """Test that the functional agent has the correct system prompt."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the functional agent system prompt contains expected content
        system_prompt = agent.functional_agent.agent.system_prompt
        assert "helpful assistant" in system_prompt
        assert "RagMeDocs" in system_prompt
        assert "functional operations" in system_prompt

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

        # Verify the system prompt includes pattern-based deletion
        system_prompt = agent.functional_agent.agent.system_prompt
        assert "delete_documents_by_pattern" in system_prompt
        assert "pattern" in system_prompt.lower()

        # Verify the tool is in the tools list
        tool_names = [
            tool.__name__ for tool in agent.functional_agent.tools.get_all_tools()
        ]
        assert "delete_documents_by_pattern" in tool_names
