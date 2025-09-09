# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Integration tests for the agent system."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.ragme.agents.agent_factory import AgentFactory
from src.ragme.agents.adapters import OpenAIAdapter, LlamaIndexAdapter, CustomAdapter
from src.ragme.utils.config_manager import ConfigManager


class TestAgentSystemIntegration:
    """Integration tests for the complete agent system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.agents_dir = self.temp_dir / "agents"
        self.agents_dir.mkdir(exist_ok=True)
        
        # Create agents.yaml file
        self.agents_file = self.temp_dir / "agents.yaml"
        self.config_file = self.temp_dir / "config.yaml"
        
        self.factory = AgentFactory(str(self.agents_dir))
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_agents_yaml(self, agents_data):
        """Helper to create agents.yaml file."""
        with open(self.agents_file, 'w') as f:
            yaml.dump(agents_data, f)
    
    def create_config_yaml(self, config_data):
        """Helper to create config.yaml file."""
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
    
    @patch('src.ragme.utils.config_manager.config')
    def test_end_to_end_openai_agent_creation(self, mock_config):
        """Test creating and using an OpenAI agent end-to-end."""
        # Setup configuration
        agents_config = {
            "agents": [
                {
                    "name": "test-openai-agent",
                    "role": "query",
                    "type": "openai",
                    "llm_model": "gpt-4",
                    "system_prompt": "You are a test assistant.",
                    "env": {
                        "temperature": 0.8
                    }
                }
            ]
        }
        
        self.create_agents_yaml(agents_config)
        
        # Mock config manager
        mock_config.get_llm_config.return_value = {"temperature": 0.7}
        mock_config.get_preferred_language.return_value = "en"
        mock_config.get_language_name.return_value = "English"
        
        # Mock the ConfigManager to use our test file
        with patch.object(ConfigManager, 'agents_config', agents_config), \
             patch('src.ragme.agents.adapters.openai_adapter.OpenAI') as mock_openai:
            
            # Setup OpenAI mock
            mock_llm = AsyncMock()
            mock_llm.acomplete.return_value = "Hello, I'm a test assistant!"
            mock_openai.return_value = mock_llm
            
            # Create agent through factory
            agent_config = agents_config["agents"][0]
            agent = self.factory.create_agent(agent_config)
            
            # Verify agent was created correctly
            assert isinstance(agent, OpenAIAdapter)
            assert agent.name == "test-openai-agent"
            assert agent.role == "query"
            assert agent.agent_type == "openai"
            
            # Test agent functionality
            async def test_agent():
                response = await agent.run("Hello!")
                assert "test assistant" in response
                
                # Verify system prompt was used
                call_args = mock_llm.acomplete.call_args[0][0]
                assert "You are a test assistant" in call_args
                assert "Hello!" in call_args
            
            import asyncio
            asyncio.run(test_agent())
    
    def test_end_to_end_custom_agent_with_local_file(self):
        """Test creating and using a custom agent with local file."""
        # Create custom agent file
        agent_file = self.agents_dir / "custom_test_agent.py"
        agent_code = '''
class CustomTestAgent:
    def __init__(self, **kwargs):
        self.name = "custom_test_agent"
        self.kwargs = kwargs
    
    def run(self, query, **kwargs):
        return f"Custom agent response to: {query}"
    
    def get_agent_info(self):
        return {
            "name": self.name,
            "description": "Custom test agent",
            "capabilities": ["Basic responses"]
        }
    
    def cleanup(self):
        pass
'''
        agent_file.write_text(agent_code)
        
        # Create agent configuration
        agent_config = {
            "name": "custom-test",
            "role": "test",
            "type": "custom",
            "llm_model": "gpt-4",
            "class_name": "CustomTestAgent",
            "code": {
                "uri": str(agent_file)
            },
            "env": {
                "test_key": "test_value"
            }
        }
        
        # Create agent
        agent = self.factory.create_agent(agent_config)
        
        # Verify agent
        assert isinstance(agent, CustomAdapter)
        assert agent.name == "custom-test"
        assert agent.role == "test"
        assert agent.agent_type == "custom"
        
        # Test functionality
        async def test_agent():
            response = await agent.run("test query")
            assert "Custom agent response to: test query" == response
            
            # Test agent info
            info = agent.get_agent_info()
            assert info["name"] == "custom-test"
            assert "custom" in info  # Should include custom agent info
            
            # Test cleanup
            agent.cleanup()
        
        import asyncio
        asyncio.run(test_agent())
    
    def test_end_to_end_custom_agent_with_inline_code(self):
        """Test creating and using a custom agent with inline code."""
        inline_code = '''
class InlineTestAgent:
    def __init__(self):
        self.name = "inline_test_agent"
    
    def run(self, query):
        return f"Inline agent says: {query.upper()}"
    
    def get_agent_info(self):
        return {
            "type": "inline",
            "version": "1.0"
        }
'''
        
        agent_config = {
            "name": "inline-test",
            "role": "test",
            "type": "custom",
            "class_name": "InlineTestAgent",
            "code": {
                "inline": inline_code
            }
        }
        
        # Create agent
        agent = self.factory.create_agent(agent_config)
        
        # Test functionality
        async def test_agent():
            response = await agent.run("hello world")
            assert response == "Inline agent says: HELLO WORLD"
            
            # Test agent info includes inline info
            info = agent.get_agent_info()
            assert info["type"] == "inline"
            assert info["version"] == "1.0"
        
        import asyncio
        asyncio.run(test_agent())
    
    @patch('src.ragme.utils.config_manager.config')
    def test_config_manager_integration(self, mock_config):
        """Test integration with ConfigManager."""
        # Create config files
        config_data = {
            "application": {"name": "RAGme Test"},
            "network": {"api": {"port": 8021}},
            # No inline agents - should use agents.yaml
        }
        
        agents_data = {
            "agents": [
                {
                    "name": "config-test-agent",
                    "role": "test",
                    "type": "openai",
                    "llm_model": "gpt-4"
                }
            ],
            "agents_directory": str(self.agents_dir)
        }
        
        self.create_config_yaml(config_data)
        self.create_agents_yaml(agents_data)
        
        # Mock the path resolution
        with patch('src.ragme.utils.config_manager.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent = self.temp_dir
            mock_path.return_value.parent.parent.parent.parent.__truediv__.return_value = self.agents_file
            
            # Mock config methods
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_preferred_language.return_value = "en"
            mock_config.get_language_name.return_value = "English"
            
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('builtins.open', side_effect=lambda path, *args, **kwargs: open(path, *args, **kwargs)):
                
                # Test ConfigManager loading
                config_manager = ConfigManager()
                config_manager._config = config_data  # Set main config
                config_manager._agents_config = None  # Force reload
                
                # Test agents config loading
                agents_config = config_manager.agents_config
                assert "agents" in agents_config
                assert len(agents_config["agents"]) == 1
                
                # Test getting specific agent config
                agent_config = config_manager.get_agent_config("config-test-agent")
                assert agent_config is not None
                assert agent_config["name"] == "config-test-agent"
                
                # Test getting all agents
                all_agents = config_manager.get_all_agents()
                assert len(all_agents) == 1
                
                # Test agents directory
                agents_dir = config_manager.get_agents_directory()
                assert str(self.agents_dir) in agents_dir
    
    def test_multiple_agent_types_integration(self):
        """Test creating multiple different types of agents."""
        agents_config = {
            "agents": [
                {
                    "name": "openai-agent",
                    "role": "query",
                    "type": "openai",
                    "llm_model": "gpt-4"
                },
                {
                    "name": "llamaindex-agent", 
                    "role": "functional",
                    "type": "llamaindex",
                    "llm_model": "gpt-4"
                },
                {
                    "name": "custom-agent",
                    "role": "test",
                    "type": "custom",
                    "class_name": "TestAgent",
                    "code": {
                        "inline": "class TestAgent:\n    def run(self, query): return 'test'"
                    }
                }
            ]
        }
        
        created_agents = []
        
        with patch('src.ragme.utils.config_manager.config') as mock_config:
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_preferred_language.return_value = "en"
            mock_config.get_language_name.return_value = "English"
            
            with patch('src.ragme.agents.adapters.openai_adapter.OpenAI'), \
                 patch('src.ragme.agents.adapters.llamaindex_adapter.FunctionAgent'):
                
                for agent_config in agents_config["agents"]:
                    agent = self.factory.create_agent(agent_config)
                    created_agents.append(agent)
        
        # Verify all agents were created with correct types
        assert len(created_agents) == 3
        assert isinstance(created_agents[0], OpenAIAdapter)
        assert isinstance(created_agents[1], LlamaIndexAdapter)
        assert isinstance(created_agents[2], CustomAdapter)
        
        # Verify agent properties
        assert created_agents[0].name == "openai-agent"
        assert created_agents[1].name == "llamaindex-agent"
        assert created_agents[2].name == "custom-agent"
    
    def test_error_handling_integration(self):
        """Test error handling across the integrated system."""
        # Test invalid agent type
        invalid_config = {
            "name": "invalid-agent",
            "role": "test",
            "type": "invalid-type"
        }
        
        with pytest.raises(ValueError, match="Unknown agent type"):
            self.factory.create_agent(invalid_config)
        
        # Test missing required fields
        incomplete_config = {
            "name": "incomplete-agent"
            # Missing role, type, etc.
        }
        
        # Should use defaults for missing fields
        with patch('src.ragme.utils.config_manager.config') as mock_config:
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_preferred_language.return_value = "en"
            mock_config.get_language_name.return_value = "English"
            
            with patch('src.ragme.agents.adapters.openai_adapter.OpenAI'):
                agent = self.factory.create_agent(incomplete_config)
                assert agent.name == "incomplete-agent"
                assert agent.role == "unknown"  # Default value
                assert agent.agent_type == "openai"  # Default type
    
    def test_factory_cleanup_integration(self):
        """Test factory cleanup affects all components."""
        # Create some agents first
        agents_config = [
            {
                "name": "test-agent-1",
                "role": "test",
                "type": "custom",
                "class_name": "TestAgent",
                "code": {
                    "inline": "class TestAgent:\n    def run(self, q): return 'test1'"
                }
            },
            {
                "name": "test-agent-2",
                "role": "test", 
                "type": "custom",
                "class_name": "TestAgent",
                "code": {
                    "inline": "class TestAgent:\n    def run(self, q): return 'test2'"
                }
            }
        ]
        
        created_agents = []
        for config in agents_config:
            agent = self.factory.create_agent(config)
            created_agents.append(agent)
        
        # Verify agents were created
        assert len(created_agents) == 2
        
        # Cleanup factory
        self.factory.cleanup()
        
        # Verify cleanup completed
        assert len(self.factory._loaded_modules) == 0
        
        # Agents should still work (they have their own instances)
        async def test_agents():
            for agent in created_agents:
                response = await agent.run("test")
                assert "test" in response
        
        import asyncio
        asyncio.run(test_agents())
    
    @patch('subprocess.run')
    def test_github_integration_simulation(self, mock_subprocess):
        """Test GitHub integration (simulated, no actual network calls)."""
        mock_subprocess.return_value = MagicMock()
        
        # Simulate successful clone
        github_config = {
            "name": "github-agent",
            "role": "test",
            "type": "custom",
            "class_name": "GitHubAgent",
            "code": {
                "uri": "https://github.com/test-user/test-agents/blob/main/agent.py"
            }
        }
        
        # Create a mock agent file in the expected location
        repo_dir = self.agents_dir / "test-user_test-agents"
        repo_dir.mkdir(parents=True, exist_ok=True)
        agent_file = repo_dir / "agent.py"
        agent_file.write_text('''
class GitHubAgent:
    def __init__(self):
        self.name = "github_agent"
    
    def run(self, query):
        return f"GitHub agent: {query}"
''')
        
        # Test agent creation
        agent = self.factory.create_agent(github_config)
        
        # Verify GitHub clone was attempted
        mock_subprocess.assert_called()
        
        # Verify agent works
        assert isinstance(agent, CustomAdapter)
        
        async def test_github_agent():
            response = await agent.run("test from github")
            assert "GitHub agent: test from github" in response
        
        import asyncio
        asyncio.run(test_github_agent())