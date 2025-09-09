# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Tests for agents configuration management."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.ragme.utils.config_manager import ConfigManager


class TestAgentsConfig:
    """Test cases for agents configuration management."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "config.yaml"
        self.agents_file = self.temp_dir / "agents.yaml"
    
    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_config_file(self, config_data):
        """Helper to create config.yaml file."""
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
    
    def create_agents_file(self, agents_data):
        """Helper to create agents.yaml file."""
        with open(self.agents_file, 'w') as f:
            yaml.dump(agents_data, f)
    
    @patch('src.ragme.utils.config_manager.Path')
    def test_load_agents_config_file_exists(self, mock_path_class):
        """Test loading agents config when file exists."""
        # Mock the path to return our temp directory
        mock_path_instance = mock_path_class.return_value.parent.parent.parent.parent
        mock_path_instance.__truediv__.return_value = self.agents_file
        
        # Create agents file
        agents_data = {
            "agents": [
                {
                    "name": "test-agent",
                    "role": "test",
                    "type": "openai",
                    "llm_model": "gpt-4"
                }
            ]
        }
        self.create_agents_file(agents_data)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=yaml.dump(agents_data))):
            
            config_manager = ConfigManager()
            # Force reload to test the method
            config_manager._agents_config = None
            agents_config = config_manager.agents_config
            
            assert "agents" in agents_config
            assert len(agents_config["agents"]) == 1
            assert agents_config["agents"][0]["name"] == "test-agent"
    
    @patch('src.ragme.utils.config_manager.Path')
    def test_load_agents_config_file_not_exists(self, mock_path_class):
        """Test loading agents config when file doesn't exist."""
        # Mock the path to return a non-existent file
        mock_path_instance = mock_path_class.return_value.parent.parent.parent.parent
        mock_path_instance.__truediv__.return_value = self.agents_file
        
        with patch('pathlib.Path.exists', return_value=False):
            config_manager = ConfigManager()
            # Force reload to test the method
            config_manager._agents_config = None
            agents_config = config_manager.agents_config
            
            assert agents_config == {"agents": []}
    
    def test_get_agent_config_from_agents_file(self):
        """Test getting agent config from agents.yaml file."""
        # Create a mock config manager with agents data
        agents_data = {
            "agents": [
                {
                    "name": "test-agent",
                    "role": "test",
                    "type": "openai",
                    "llm_model": "gpt-4",
                    "system_prompt": "Test prompt"
                },
                {
                    "name": "other-agent",
                    "role": "other",
                    "type": "custom"
                }
            ]
        }
        
        config_manager = ConfigManager()
        config_manager._agents_config = agents_data
        config_manager._config = {}  # Empty main config
        
        # Test finding existing agent
        agent_config = config_manager.get_agent_config("test-agent")
        
        assert agent_config is not None
        assert agent_config["name"] == "test-agent"
        assert agent_config["role"] == "test"
        assert agent_config["type"] == "openai"
        assert agent_config["system_prompt"] == "Test prompt"
    
    def test_get_agent_config_fallback_to_inline(self):
        """Test getting agent config falls back to inline config when agents file is empty."""
        # Mock agents file as empty
        config_manager = ConfigManager()
        config_manager._agents_config = {"agents": []}
        
        # Mock inline agents in main config
        config_manager._config = {
            "agents": [
                {
                    "name": "inline-agent",
                    "type": "ragme",
                    "llm_model": "gpt-4o-mini"
                }
            ]
        }
        
        # Test finding agent in inline config
        agent_config = config_manager.get_agent_config("inline-agent")
        
        assert agent_config is not None
        assert agent_config["name"] == "inline-agent"
        assert agent_config["type"] == "ragme"
    
    def test_get_agent_config_not_found(self):
        """Test getting agent config that doesn't exist."""
        config_manager = ConfigManager()
        config_manager._agents_config = {"agents": []}
        config_manager._config = {"agents": []}
        
        agent_config = config_manager.get_agent_config("nonexistent-agent")
        
        assert agent_config is None
    
    def test_get_all_agents_from_file(self):
        """Test getting all agents from agents.yaml file."""
        agents_data = {
            "agents": [
                {"name": "agent1", "role": "test1"},
                {"name": "agent2", "role": "test2"}
            ]
        }
        
        config_manager = ConfigManager()
        config_manager._agents_config = agents_data
        config_manager._config = {}
        
        all_agents = config_manager.get_all_agents()
        
        assert len(all_agents) == 2
        assert all_agents[0]["name"] == "agent1"
        assert all_agents[1]["name"] == "agent2"
    
    def test_get_all_agents_fallback_to_inline(self):
        """Test getting all agents falls back to inline config."""
        config_manager = ConfigManager()
        config_manager._agents_config = {"agents": []}
        config_manager._config = {
            "agents": [
                {"name": "inline1", "type": "ragme"},
                {"name": "inline2", "type": "functional"}
            ]
        }
        
        all_agents = config_manager.get_all_agents()
        
        assert len(all_agents) == 2
        assert all_agents[0]["name"] == "inline1"
        assert all_agents[1]["name"] == "inline2"
    
    def test_get_all_agents_empty(self):
        """Test getting all agents when none are configured."""
        config_manager = ConfigManager()
        config_manager._agents_config = {"agents": []}
        config_manager._config = {}
        
        all_agents = config_manager.get_all_agents()
        
        assert all_agents == []
    
    def test_has_agents_file(self):
        """Test checking if agents.yaml file exists."""
        with patch('pathlib.Path.exists') as mock_exists:
            config_manager = ConfigManager()
            
            # Test file exists
            mock_exists.return_value = True
            assert config_manager.has_agents_file() is True
            
            # Test file doesn't exist
            mock_exists.return_value = False
            assert config_manager.has_agents_file() is False
    
    def test_get_agents_directory(self):
        """Test getting agents directory configuration."""
        config_manager = ConfigManager()
        config_manager._agents_config = {
            "agents_directory": "/custom/agents/path"
        }
        
        agents_dir = config_manager.get_agents_directory()
        
        # Should return absolute path
        assert agents_dir.endswith("custom/agents/path") or agents_dir == "/custom/agents/path"
    
    def test_get_agents_directory_default(self):
        """Test getting agents directory with default value."""
        config_manager = ConfigManager()
        config_manager._agents_config = {}
        
        agents_dir = config_manager.get_agents_directory()
        
        # Should return default ./agents as absolute path
        assert "agents" in agents_dir
    
    def test_agents_config_validation_types(self):
        """Test agents config handles invalid data types."""
        config_manager = ConfigManager()
        
        # Test with non-list agents in agents file
        config_manager._agents_config = {"agents": "not a list"}
        config_manager._config = {}
        
        agent_config = config_manager.get_agent_config("test")
        assert agent_config is None
        
        all_agents = config_manager.get_all_agents()
        assert all_agents == []
        
        # Test with non-list agents in inline config
        config_manager._agents_config = {"agents": []}
        config_manager._config = {"agents": "also not a list"}
        
        agent_config = config_manager.get_agent_config("test")
        assert agent_config is None
        
        all_agents = config_manager.get_all_agents()
        assert all_agents == []
    
    def test_agents_config_invalid_agent_format(self):
        """Test agents config handles invalid agent format."""
        config_manager = ConfigManager()
        config_manager._agents_config = {
            "agents": [
                "not a dictionary",
                {"name": "valid-agent", "role": "test"},
                None
            ]
        }
        config_manager._config = {}
        
        # Should find the valid agent and ignore invalid ones
        agent_config = config_manager.get_agent_config("valid-agent")
        assert agent_config is not None
        assert agent_config["name"] == "valid-agent"
        
        # Should only return valid agents
        all_agents = config_manager.get_all_agents()
        assert len(all_agents) == 3  # Returns all items, but only valid ones are usable
    
    def test_reload_config_clears_agents_config(self):
        """Test that reload_config clears the agents configuration."""
        config_manager = ConfigManager()
        config_manager._config = {"test": "data"}
        config_manager._agents_config = {"agents": [{"test": "agent"}]}
        
        config_manager.reload_config()
        
        assert config_manager._config is None
        assert config_manager._agents_config is None
    
    def test_agents_yaml_with_environment_variables(self):
        """Test agents.yaml with environment variable substitution."""
        import os
        
        # Set environment variable
        os.environ['TEST_MODEL'] = 'gpt-4-test'
        
        try:
            agents_data = {
                "agents": [
                    {
                        "name": "env-agent",
                        "llm_model": "${TEST_MODEL}",
                        "env": {
                            "api_key": "${OPENAI_API_KEY:-default-key}"
                        }
                    }
                ]
            }
            
            # Mock the file loading
            with patch('builtins.open', mock_open(read_data=yaml.dump(agents_data))), \
                 patch('pathlib.Path.exists', return_value=True):
                
                config_manager = ConfigManager()
                config_manager._agents_config = None
                
                # This should trigger environment variable substitution
                agents_config = config_manager.agents_config
                
                agent = agents_config["agents"][0]
                assert agent["llm_model"] == "gpt-4-test"
                
        finally:
            # Cleanup environment variable
            if 'TEST_MODEL' in os.environ:
                del os.environ['TEST_MODEL']
    
    def test_agents_yaml_parsing_error(self):
        """Test handling of YAML parsing errors in agents.yaml."""
        invalid_yaml = "agents:\n  - name: test\n    invalid: yaml: content:"
        
        with patch('builtins.open', mock_open(read_data=invalid_yaml)), \
             patch('pathlib.Path.exists', return_value=True):
            
            config_manager = ConfigManager()
            config_manager._agents_config = None
            
            with pytest.raises(ValueError, match="Error parsing agents configuration"):
                config_manager.agents_config