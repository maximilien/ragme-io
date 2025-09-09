# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Tests for the AgentFactory class."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.ragme.agents.agent_factory import AgentFactory
from src.ragme.agents.adapters import OpenAIAdapter, LlamaIndexAdapter, CustomAdapter


class TestAgentFactory:
    """Test cases for AgentFactory."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.agents_dir = Path(self.temp_dir) / "test_agents"
        self.factory = AgentFactory(str(self.agents_dir))
    
    def teardown_method(self):
        """Cleanup test environment."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = AgentFactory()
        assert Path("./agents").resolve() == Path(factory.agents_dir).resolve()
        
        custom_factory = AgentFactory("/tmp/custom_agents")
        assert Path("/tmp/custom_agents") == Path(custom_factory.agents_dir)
    
    @patch('src.ragme.agents.agent_factory.OpenAIAdapter')
    def test_create_openai_agent(self, mock_openai_adapter):
        """Test creating an OpenAI agent."""
        mock_adapter = MagicMock()
        mock_openai_adapter.return_value = mock_adapter
        
        config = {
            "name": "test-openai",
            "role": "query",
            "type": "openai",
            "llm_model": "gpt-4",
            "system_prompt": "Test prompt"
        }
        
        agent = self.factory.create_agent(config)
        
        assert agent is mock_adapter
        mock_openai_adapter.assert_called_once_with(
            name="test-openai",
            role="query",
            llm_model="gpt-4",
            system_prompt="Test prompt",
            env={}
        )
    
    @patch('src.ragme.agents.agent_factory.LlamaIndexAdapter')
    def test_create_llamaindex_agent(self, mock_llamaindex_adapter):
        """Test creating a LlamaIndex agent."""
        mock_adapter = MagicMock()
        mock_llamaindex_adapter.return_value = mock_adapter
        
        config = {
            "name": "test-llamaindex",
            "role": "functional",
            "type": "llamaindex",
            "llm_model": "gpt-4"
        }
        
        # Mock RagMeTools import
        with patch('src.ragme.agents.agent_factory.RagMeTools') as mock_tools:
            mock_ragme_instance = MagicMock()
            mock_tools_instance = MagicMock()
            mock_tools_instance.get_tools.return_value = ["tool1", "tool2"]
            mock_tools.return_value = mock_tools_instance
            
            agent = self.factory.create_agent(config, ragme_instance=mock_ragme_instance)
            
            assert agent is mock_adapter
            mock_llamaindex_adapter.assert_called_once()
            call_args = mock_llamaindex_adapter.call_args
            assert call_args[1]["name"] == "test-llamaindex"
            assert call_args[1]["role"] == "functional"
            assert call_args[1]["agent_class"] == "FunctionAgent"
            assert call_args[1]["tools"] == ["tool1", "tool2"]
    
    @patch('src.ragme.agents.agent_factory.LlamaIndexAdapter')
    def test_create_llamaindex_dispatch_agent(self, mock_llamaindex_adapter):
        """Test creating a LlamaIndex dispatch agent (should use ReActAgent)."""
        mock_adapter = MagicMock()
        mock_llamaindex_adapter.return_value = mock_adapter
        
        config = {
            "name": "test-dispatch",
            "role": "dispatch",
            "type": "llamaindex"
        }
        
        agent = self.factory.create_agent(config)
        
        call_args = mock_llamaindex_adapter.call_args
        assert call_args[1]["agent_class"] == "ReActAgent"
    
    @patch('src.ragme.agents.agent_factory.CustomAdapter')
    def test_create_custom_agent_with_import(self, mock_custom_adapter):
        """Test creating a custom agent using direct import."""
        mock_adapter = MagicMock()
        mock_custom_adapter.return_value = mock_adapter
        
        config = {
            "name": "test-custom",
            "role": "test",
            "type": "custom",
            "class_name": "src.ragme.agents.query_agent.QueryAgent"
        }
        
        with patch.object(self.factory, '_load_custom_agent_class') as mock_load:
            mock_instance = MagicMock()
            mock_load.return_value = mock_instance
            
            agent = self.factory.create_agent(config)
            
            assert agent is mock_adapter
            mock_custom_adapter.assert_called_once()
            assert mock_custom_adapter.call_args[1]["custom_agent_instance"] is mock_instance
    
    def test_create_agent_unknown_type(self):
        """Test creating agent with unknown type raises error."""
        config = {
            "name": "test",
            "role": "test",
            "type": "unknown"
        }
        
        with pytest.raises(ValueError, match="Unknown agent type: unknown"):
            self.factory.create_agent(config)
    
    def test_load_from_import_success(self):
        """Test loading agent from direct import."""
        # Test with a real importable module
        class_name = "pathlib.Path"
        
        instance = self.factory._load_from_import(class_name)
        
        # Path() creates an instance
        assert instance is not None
    
    def test_load_from_import_invalid_format(self):
        """Test loading agent with invalid class name format."""
        with pytest.raises(ValueError, match="Class name must be fully qualified"):
            self.factory._load_from_import("InvalidClassName")
    
    def test_load_from_import_module_not_found(self):
        """Test loading agent with non-existent module."""
        with pytest.raises(ModuleNotFoundError):
            self.factory._load_from_import("nonexistent.module.ClassName")
    
    def test_load_from_import_class_not_found(self):
        """Test loading agent with non-existent class."""
        with pytest.raises(AttributeError):
            self.factory._load_from_import("pathlib.NonExistentClass")
    
    def test_load_from_file_success(self):
        """Test loading agent from local file."""
        # Create a test Python file
        test_file = self.agents_dir / "test_agent.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        test_code = '''
class TestAgent:
    def __init__(self):
        self.name = "test_agent"
        
    def run(self, query):
        return f"Response to: {query}"
'''
        test_file.write_text(test_code)
        
        instance = self.factory._load_from_file(
            class_name="TestAgent",
            file_path=str(test_file)
        )
        
        assert instance is not None
        assert instance.name == "test_agent"
        assert instance.run("test") == "Response to: test"
    
    def test_load_from_file_not_found(self):
        """Test loading agent from non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.factory._load_from_file("TestAgent", "/nonexistent/path.py")
    
    def test_load_from_inline_code(self):
        """Test loading agent from inline code."""
        inline_code = '''
class InlineAgent:
    def __init__(self):
        self.name = "inline_agent"
        
    def run(self, query):
        return f"Inline response: {query}"
'''
        
        instance = self.factory._load_from_inline_code(
            class_name="InlineAgent",
            code=inline_code
        )
        
        assert instance is not None
        assert instance.name == "inline_agent"
        assert instance.run("test") == "Inline response: test"
    
    def test_is_github_uri(self):
        """Test GitHub URI detection."""
        assert self.factory._is_github_uri("https://github.com/user/repo")
        assert self.factory._is_github_uri("github.com/user/repo")
        assert not self.factory._is_github_uri("./local/file.py")
        assert not self.factory._is_github_uri("http://example.com/file.py")
    
    @patch('subprocess.run')
    def test_clone_github_repo_success(self, mock_subprocess):
        """Test successful GitHub repository cloning."""
        mock_subprocess.return_value = MagicMock()
        
        repo_dir = self.factory._clone_or_update_github_repo("user", "repo", "main")
        
        expected_dir = self.agents_dir / "user_repo"
        assert repo_dir == expected_dir
        
        # Should call git clone
        mock_subprocess.assert_called()
        call_args = mock_subprocess.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args
    
    @patch('subprocess.run')
    def test_update_existing_github_repo(self, mock_subprocess):
        """Test updating existing GitHub repository."""
        # Create existing repo directory
        repo_dir = self.agents_dir / "user_repo"
        repo_dir.mkdir(parents=True)
        
        mock_subprocess.return_value = MagicMock()
        
        result_dir = self.factory._clone_or_update_github_repo("user", "repo", "main")
        
        assert result_dir == repo_dir
        
        # Should call git pull
        mock_subprocess.assert_called()
        call_args = mock_subprocess.call_args[0][0]
        assert "git" in call_args
        assert "pull" in call_args
    
    @patch('subprocess.run')
    def test_clone_github_repo_failure(self, mock_subprocess):
        """Test GitHub repository cloning failure."""
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(1, "git")
        
        with pytest.raises(RuntimeError, match="Could not clone repository"):
            self.factory._clone_or_update_github_repo("user", "repo", "main")
    
    def test_find_agent_file_in_repo(self):
        """Test finding agent file in repository."""
        # Create test repository structure
        repo_dir = self.agents_dir / "test_repo"
        repo_dir.mkdir(parents=True)
        
        # Create some files
        (repo_dir / "myagent.py").touch()
        (repo_dir / "agent.py").touch()
        (repo_dir / "main.py").touch()
        
        # Test finding by class name
        found = self.factory._find_agent_file_in_repo(repo_dir, "MyAgent")
        assert found.name == "myagent.py"
        
        # Test fallback to agent.py
        found = self.factory._find_agent_file_in_repo(repo_dir, "UnknownAgent")
        assert found.name == "agent.py"
    
    def test_get_class_from_module_by_name(self):
        """Test getting class from module by exact name."""
        import types
        
        # Create a mock module with a test class
        module = types.ModuleType("test_module")
        
        class TestAgentClass:
            pass
        
        module.TestAgentClass = TestAgentClass
        
        result = self.factory._get_class_from_module(module, "TestAgentClass")
        assert result is TestAgentClass
    
    def test_get_class_from_module_by_pattern(self):
        """Test getting class from module by agent pattern."""
        import types
        
        # Create a mock module with a test class
        module = types.ModuleType("test_module")
        
        class MyCustomAgent:
            pass
        
        class NotAnAgent:
            pass
        
        module.MyCustomAgent = MyCustomAgent
        module.NotAnAgent = NotAnAgent
        
        result = self.factory._get_class_from_module(module, "UnknownClass")
        assert result is MyCustomAgent  # Should find the *Agent class
    
    def test_get_class_from_module_not_found(self):
        """Test getting class from module when not found."""
        import types
        
        module = types.ModuleType("test_module")
        
        with pytest.raises(AttributeError, match="No agent class found"):
            self.factory._get_class_from_module(module, "NonExistentClass")
    
    def test_create_agent_instance_with_ragme(self):
        """Test creating agent instance with ragme_instance parameter."""
        class TestAgent:
            def __init__(self, ragme_instance):
                self.ragme = ragme_instance
        
        mock_ragme = MagicMock()
        instance = self.factory._create_agent_instance(TestAgent, ragme_instance=mock_ragme)
        
        assert instance.ragme is mock_ragme
    
    def test_create_agent_instance_with_kwargs(self):
        """Test creating agent instance with kwargs."""
        class TestAgent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        
        instance = self.factory._create_agent_instance(TestAgent, test_arg="value")
        
        assert instance.kwargs == {"test_arg": "value"}
    
    def test_create_agent_instance_no_args(self):
        """Test creating agent instance with no arguments."""
        class TestAgent:
            def __init__(self):
                self.created = True
        
        instance = self.factory._create_agent_instance(TestAgent)
        
        assert instance.created is True
    
    def test_create_agent_instance_with_env(self):
        """Test creating agent instance with env parameter."""
        class TestAgent:
            def __init__(self, env=None):
                self.env = env
        
        env = {"test": "value"}
        instance = self.factory._create_agent_instance(TestAgent, env=env)
        
        assert instance.env == env
    
    def test_factory_cleanup(self):
        """Test factory cleanup method."""
        self.factory._loaded_modules = {"test": "module"}
        self.factory.cleanup()
        assert len(self.factory._loaded_modules) == 0