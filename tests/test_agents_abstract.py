# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Tests for the AbstractAgent interface and adapter classes."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ragme.agents.abstract_agent import AbstractAgent
from src.ragme.agents.adapters import CustomAdapter, LlamaIndexAdapter, OpenAIAdapter


class MockAgent(AbstractAgent):
    """Mock implementation for testing AbstractAgent."""

    async def run(self, query: str, **kwargs) -> str:
        return f"Mock response to: {query}"

    def get_agent_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "type": self.agent_type,
            "description": "Mock agent for testing",
        }


class TestAbstractAgent:
    """Test cases for AbstractAgent base class."""

    def test_agent_initialization(self):
        """Test agent initialization with all parameters."""
        agent = MockAgent(
            name="test-agent",
            role="test",
            agent_type="mock",
            llm_model="gpt-4",
            system_prompt="Test prompt",
            env={"key": "value"},
        )

        assert agent.name == "test-agent"
        assert agent.role == "test"
        assert agent.agent_type == "mock"
        assert agent.llm_model == "gpt-4"
        assert agent.system_prompt == "Test prompt"
        assert agent.env == {"key": "value"}

    def test_agent_initialization_minimal(self):
        """Test agent initialization with minimal parameters."""
        agent = MockAgent("test", "test", "mock")

        assert agent.name == "test"
        assert agent.role == "test"
        assert agent.agent_type == "mock"
        assert agent.llm_model == "gpt-4o-mini"  # default
        assert agent.system_prompt is None
        assert agent.env == {}

    @pytest.mark.asyncio
    async def test_agent_run(self):
        """Test agent run method."""
        agent = MockAgent("test", "test", "mock")
        response = await agent.run("test query")
        assert response == "Mock response to: test query"

    def test_agent_info(self):
        """Test agent get_agent_info method."""
        agent = MockAgent("test", "test", "mock")
        info = agent.get_agent_info()

        assert info["name"] == "test"
        assert info["role"] == "test"
        assert info["type"] == "mock"
        assert "description" in info

    def test_agent_cleanup(self):
        """Test agent cleanup method (should not raise)."""
        agent = MockAgent("test", "test", "mock")
        agent.cleanup()  # Should complete without error

    def test_agent_string_representation(self):
        """Test agent string representations."""
        agent = MockAgent("test-agent", "test", "mock")

        assert str(agent) == "test-agent (test/mock)"
        assert "AbstractAgent" in repr(agent)
        assert "name='test-agent'" in repr(agent)
        assert "role='test'" in repr(agent)
        assert "type='mock'" in repr(agent)


class TestOpenAIAdapter:
    """Test cases for OpenAI adapter."""

    @patch("src.ragme.utils.config_manager.config")
    def test_openai_adapter_initialization(self, mock_config):
        """Test OpenAI adapter initialization."""
        mock_config.get_llm_config.return_value = {"temperature": 0.8}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        adapter = OpenAIAdapter(
            name="openai-agent",
            role="test",
            llm_model="gpt-4",
            system_prompt="Test prompt",
        )

        assert adapter.name == "openai-agent"
        assert adapter.role == "test"
        assert adapter.agent_type == "openai"
        assert adapter.llm_model == "gpt-4"
        assert adapter.system_prompt == "Test prompt"
        assert hasattr(adapter, "llm")

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.openai_adapter.OpenAI")
    @pytest.mark.asyncio
    async def test_openai_adapter_run(self, mock_openai_class, mock_config):
        """Test OpenAI adapter run method."""
        # Setup mocks
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_llm = AsyncMock()
        mock_llm.acomplete.return_value = "OpenAI response"
        mock_openai_class.return_value = mock_llm

        # Create adapter and test
        adapter = OpenAIAdapter("test", "test", "gpt-4")
        response = await adapter.run("test query")

        assert response == "OpenAI response"
        mock_llm.acomplete.assert_called_once()

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.openai_adapter.OpenAI")
    @pytest.mark.asyncio
    async def test_openai_adapter_run_with_system_prompt(
        self, mock_openai_class, mock_config
    ):
        """Test OpenAI adapter run method with system prompt."""
        # Setup mocks
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_llm = AsyncMock()
        mock_llm.acomplete.return_value = "OpenAI response with prompt"
        mock_openai_class.return_value = mock_llm

        # Create adapter and test
        adapter = OpenAIAdapter(
            "test", "test", "gpt-4", system_prompt="You are a test assistant"
        )
        response = await adapter.run("test query")

        assert response == "OpenAI response with prompt"

        # Verify system prompt was included
        call_args = mock_llm.acomplete.call_args[0][0]
        assert "You are a test assistant" in call_args
        assert "test query" in call_args
        assert "English" in call_args

    @patch("src.ragme.utils.config_manager.config")
    def test_openai_adapter_get_info(self, mock_config):
        """Test OpenAI adapter get_agent_info method."""
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        adapter = OpenAIAdapter(
            name="openai-test",
            role="query",
            llm_model="gpt-4",
            system_prompt="Test",
            env={"key": "value"},
        )

        info = adapter.get_agent_info()

        assert info["name"] == "openai-test"
        assert info["role"] == "query"
        assert info["type"] == "openai"
        assert info["model"] == "gpt-4"
        assert info["language"] == "English"
        assert info["has_system_prompt"] is True
        assert "capabilities" in info

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.openai_adapter.OpenAI")
    @pytest.mark.asyncio
    async def test_openai_adapter_error_handling(self, mock_openai_class, mock_config):
        """Test OpenAI adapter error handling."""
        # Setup mocks
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_llm = AsyncMock()
        mock_llm.acomplete.side_effect = Exception("API error")
        mock_openai_class.return_value = mock_llm

        # Create adapter and test error handling
        adapter = OpenAIAdapter("test", "test", "gpt-4")
        response = await adapter.run("test query")

        assert "Error processing query" in response
        assert "API error" in response


class TestLlamaIndexAdapter:
    """Test cases for LlamaIndex adapter."""

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.llamaindex_adapter.FunctionAgent")
    def test_llamaindex_adapter_initialization(self, mock_function_agent, mock_config):
        """Test LlamaIndex adapter initialization."""
        mock_config.get_llm_config.return_value = {"temperature": 0.8}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_agent = MagicMock()
        mock_function_agent.return_value = mock_agent

        adapter = LlamaIndexAdapter(
            name="llamaindex-agent",
            role="functional",
            llm_model="gpt-4",
            tools=[],
            agent_class="FunctionAgent",
        )

        assert adapter.name == "llamaindex-agent"
        assert adapter.role == "functional"
        assert adapter.agent_type == "llamaindex"
        assert adapter.agent_class == "FunctionAgent"
        assert adapter.tools == []
        mock_function_agent.assert_called_once()

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.llamaindex_adapter.ReActAgent")
    def test_llamaindex_adapter_react_agent(self, mock_react_agent, mock_config):
        """Test LlamaIndex adapter with ReActAgent."""
        mock_config.get_llm_config.return_value = {"temperature": 0.8}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_agent = MagicMock()
        mock_react_agent.from_tools.return_value = mock_agent

        adapter = LlamaIndexAdapter(
            name="react-agent", role="dispatch", agent_class="ReActAgent"
        )

        assert adapter.agent_class == "ReActAgent"
        mock_react_agent.from_tools.assert_called_once()

    @patch("src.ragme.utils.config_manager.config")
    @patch("src.ragme.agents.adapters.llamaindex_adapter.FunctionAgent")
    @pytest.mark.asyncio
    async def test_llamaindex_adapter_run(self, mock_function_agent, mock_config):
        """Test LlamaIndex adapter run method."""
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"

        mock_agent = AsyncMock()
        mock_agent.achat.return_value = "LlamaIndex response"
        mock_function_agent.return_value = mock_agent

        adapter = LlamaIndexAdapter("test", "functional")
        response = await adapter.run("test query")

        assert response == "LlamaIndex response"
        mock_agent.achat.assert_called_once_with("test query")


class TestCustomAdapter:
    """Test cases for Custom adapter."""

    def test_custom_adapter_initialization(self):
        """Test Custom adapter initialization."""
        mock_custom_agent = MagicMock()

        adapter = CustomAdapter(
            name="custom-agent", role="test", custom_agent_instance=mock_custom_agent
        )

        assert adapter.name == "custom-agent"
        assert adapter.role == "test"
        assert adapter.agent_type == "custom"
        assert adapter.custom_agent is mock_custom_agent

    @pytest.mark.asyncio
    async def test_custom_adapter_run_with_run_method(self):
        """Test Custom adapter run with custom agent that has run method."""
        mock_custom_agent = AsyncMock()
        mock_custom_agent.run.return_value = "Custom response"

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        response = await adapter.run("test query")

        assert response == "Custom response"
        mock_custom_agent.run.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_custom_adapter_run_with_process_method(self):
        """Test Custom adapter run with custom agent that has process method."""
        mock_custom_agent = MagicMock()
        mock_custom_agent.process.return_value = "Processed response"
        # Remove run method to test fallback
        del mock_custom_agent.run

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        response = await adapter.run("test query")

        assert response == "Processed response"
        mock_custom_agent.process.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_custom_adapter_run_with_query_method(self):
        """Test Custom adapter run with custom agent that has query method."""
        mock_custom_agent = MagicMock()
        mock_custom_agent.query.return_value = "Query response"
        # Remove run and process methods to test fallback
        del mock_custom_agent.run
        del mock_custom_agent.process

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        response = await adapter.run("test query")

        assert response == "Query response"
        mock_custom_agent.query.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_custom_adapter_run_no_methods(self):
        """Test Custom adapter run with custom agent that has no recognized methods."""
        mock_custom_agent = MagicMock()
        # Remove all recognized methods
        del mock_custom_agent.run
        del mock_custom_agent.process
        del mock_custom_agent.query

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        response = await adapter.run("test query")

        assert "does not have a recognized execution method" in response

    @pytest.mark.asyncio
    async def test_custom_adapter_run_no_instance(self):
        """Test Custom adapter run with no custom agent instance."""
        adapter = CustomAdapter("test", "test")
        response = await adapter.run("test query")

        assert "No custom agent instance available" in response

    def test_custom_adapter_get_info(self):
        """Test Custom adapter get_agent_info method."""
        mock_custom_agent = MagicMock()
        mock_custom_agent.get_agent_info.return_value = {"custom": "info"}

        adapter = CustomAdapter(
            name="custom-test",
            role="test",
            env={"key": "value"},
            custom_agent_instance=mock_custom_agent,
        )

        info = adapter.get_agent_info()

        assert info["name"] == "custom-test"
        assert info["role"] == "test"
        assert info["type"] == "custom"
        assert info["has_instance"] is True
        assert info["custom"] == "info"  # From custom agent

    def test_custom_adapter_get_info_no_custom_method(self):
        """Test Custom adapter get_agent_info when custom agent has no get_agent_info method."""
        mock_custom_agent = MagicMock()
        del mock_custom_agent.get_agent_info

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        info = adapter.get_agent_info()

        assert info["name"] == "test"
        assert info["has_instance"] is True

    def test_custom_adapter_cleanup(self):
        """Test Custom adapter cleanup method."""
        mock_custom_agent = MagicMock()

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        adapter.cleanup()

        mock_custom_agent.cleanup.assert_called_once()
        assert adapter.custom_agent is None

    def test_custom_adapter_cleanup_no_custom_cleanup(self):
        """Test Custom adapter cleanup when custom agent has no cleanup method."""
        mock_custom_agent = MagicMock()
        del mock_custom_agent.cleanup

        adapter = CustomAdapter("test", "test", custom_agent_instance=mock_custom_agent)
        adapter.cleanup()  # Should not raise

        assert adapter.custom_agent is None
