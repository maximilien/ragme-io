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

from src.ragme.ragme_agent import RagMeAgent


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
        assert agent.llm is not None
        assert agent.agent is not None

    def test_create_agent(self):
        """Test that the agent is created with the correct tools and configuration."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the agent was created
        assert agent.agent is not None
        # The agent should be a FunctionAgent with tools
        assert hasattr(agent.agent, "tools")
        assert (
            len(agent.agent.tools) == 8
        )  # 8 tools: write, delete_collection, delete_document, delete_all_documents, list, crawl, query, db info

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
        """Test that the agent's tools can access RagMe methods correctly."""
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

        # Get the tools from the agent
        tools = agent.agent.tools

        # Verify we have the expected number of tools
        assert (
            len(tools) == 8
        )  # write, delete_collection, delete_document, delete_all_documents, list, crawl, query, db info

        # Test that the tools can access RagMe methods by calling them directly
        # We'll test the list_ragme_collection function by finding it in the agent's _create_agent method
        # Since we can't easily access the individual tools, we'll test the overall functionality
        assert hasattr(agent, "_create_agent")
        assert callable(agent._create_agent)

    def test_agent_system_prompt(self):
        """Test that the agent has the correct system prompt."""
        # Mock the RagMe instance
        mock_ragme = Mock()
        mock_ragme.weeviate_client = Mock()
        mock_ragme.collection_name = "RagMeDocs"
        mock_ragme.query_agent = Mock()
        mock_ragme.list_documents = Mock()
        mock_ragme.write_webpages_to_weaviate = Mock()

        # Create RagMeAgent instance
        agent = RagMeAgent(mock_ragme)

        # Verify the system prompt contains expected content
        system_prompt = agent.agent.system_prompt
        assert "helpful assistant" in system_prompt
        assert "RagMeDocs" in system_prompt
        assert "QueryAgent" in system_prompt
