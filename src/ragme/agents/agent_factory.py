# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import importlib.util
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .abstract_agent import AbstractAgent
from .adapters import CustomAdapter, LlamaIndexAdapter, OpenAIAdapter
from ..utils.config_manager import config

# Set up logging
logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory class for creating agent instances from configuration.
    
    This factory can create agents using different frameworks (OpenAI, LlamaIndex, Custom)
    and load agent code from various sources (local files, GitHub repositories).
    """
    
    def __init__(self, agents_dir: Optional[str] = None):
        """
        Initialize the AgentFactory.
        
        Args:
            agents_dir: Directory for storing downloaded agent code (default: ./agents)
        """
        self.agents_dir = Path(agents_dir or "./agents")
        self.agents_dir.mkdir(exist_ok=True)
        
        # Track loaded modules to avoid reloading
        self._loaded_modules = {}
        
        logger.info(f"Initialized AgentFactory with agents directory: {self.agents_dir}")

    def create_agent(
        self,
        agent_config: Dict[str, Any],
        ragme_instance: Optional[Any] = None,
        **kwargs
    ) -> AbstractAgent:
        """
        Create an agent instance from configuration.
        
        Args:
            agent_config: Agent configuration dictionary
            ragme_instance: Optional RAGme instance for agents that need it
            **kwargs: Additional arguments to pass to the agent
            
        Returns:
            AbstractAgent: The created agent instance
        """
        name = agent_config.get("name", "unknown")
        role = agent_config.get("role", "unknown") 
        agent_type = agent_config.get("type", "openai")
        llm_model = agent_config.get("llm_model", "gpt-4o-mini")
        system_prompt = agent_config.get("system_prompt")
        env = agent_config.get("env", {})
        
        logger.info(f"Creating agent '{name}' with role '{role}' and type '{agent_type}'")
        
        try:
            if agent_type == "openai":
                return self._create_openai_agent(
                    name=name,
                    role=role,
                    llm_model=llm_model,
                    system_prompt=system_prompt,
                    env=env,
                    **kwargs
                )
                
            elif agent_type == "llamaindex":
                return self._create_llamaindex_agent(
                    name=name,
                    role=role,
                    llm_model=llm_model,
                    system_prompt=system_prompt,
                    env=env,
                    agent_config=agent_config,
                    ragme_instance=ragme_instance,
                    **kwargs
                )
                
            elif agent_type == "custom":
                return self._create_custom_agent(
                    name=name,
                    role=role,
                    llm_model=llm_model,
                    system_prompt=system_prompt,
                    env=env,
                    agent_config=agent_config,
                    ragme_instance=ragme_instance,
                    **kwargs
                )
                
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
                
        except Exception as e:
            logger.error(f"Error creating agent '{name}': {str(e)}")
            raise

    def _create_openai_agent(
        self,
        name: str,
        role: str,
        llm_model: str,
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> OpenAIAdapter:
        """Create an OpenAI-based agent."""
        return OpenAIAdapter(
            name=name,
            role=role,
            llm_model=llm_model,
            system_prompt=system_prompt,
            env=env,
            **kwargs
        )

    def _create_llamaindex_agent(
        self,
        name: str,
        role: str,
        llm_model: str,
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        ragme_instance: Optional[Any] = None,
        **kwargs
    ) -> LlamaIndexAdapter:
        """Create a LlamaIndex-based agent."""
        
        # Determine the LlamaIndex agent class based on role
        agent_class = "FunctionAgent"  # Default
        if role == "dispatch":
            agent_class = "ReActAgent"
        elif role == "functional":
            agent_class = "FunctionAgent"
        
        # Get tools based on role and ragme instance
        tools = []
        if ragme_instance and role == "functional":
            # Import and create tools for functional agents
            try:
                from .tools import RagMeTools
                ragme_tools = RagMeTools(ragme_instance)
                tools = ragme_tools.get_tools()
            except ImportError:
                logger.warning("Could not import RagMeTools for functional agent")
        
        return LlamaIndexAdapter(
            name=name,
            role=role,
            llm_model=llm_model,
            system_prompt=system_prompt,
            env=env,
            tools=tools,
            agent_class=agent_class,
            **kwargs
        )

    def _create_custom_agent(
        self,
        name: str,
        role: str,
        llm_model: str,
        system_prompt: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        ragme_instance: Optional[Any] = None,
        **kwargs
    ) -> CustomAdapter:
        """Create a custom agent."""
        
        custom_instance = None
        
        if agent_config:
            class_name = agent_config.get("class_name")
            code_config = agent_config.get("code", {})
            
            if class_name and code_config:
                # Load the custom agent class and create an instance
                custom_instance = self._load_custom_agent_class(
                    class_name=class_name,
                    code_config=code_config,
                    ragme_instance=ragme_instance,
                    env=env,
                    **kwargs
                )
        
        return CustomAdapter(
            name=name,
            role=role,
            llm_model=llm_model,
            system_prompt=system_prompt,
            env=env,
            custom_agent_instance=custom_instance,
            **kwargs
        )

    def _load_custom_agent_class(
        self,
        class_name: str,
        code_config: Dict[str, Any],
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Load a custom agent class from code configuration.
        
        Args:
            class_name: Fully qualified class name (e.g., "ragme.agents.MyAgent")
            code_config: Code configuration containing uri or inline code
            ragme_instance: RAGme instance to pass to the agent
            env: Environment variables
            **kwargs: Additional arguments
            
        Returns:
            Instance of the custom agent class
        """
        try:
            # Handle different code sources
            code_uri = code_config.get("uri")
            inline_code = code_config.get("inline")
            
            if code_uri:
                # Load from URI (file path or GitHub)
                return self._load_from_uri(
                    class_name=class_name,
                    uri=code_uri,
                    ragme_instance=ragme_instance,
                    env=env,
                    **kwargs
                )
            elif inline_code:
                # Load from inline code
                return self._load_from_inline_code(
                    class_name=class_name,
                    code=inline_code,
                    ragme_instance=ragme_instance,
                    env=env,
                    **kwargs
                )
            else:
                # Try to import directly if no code source specified
                return self._load_from_import(
                    class_name=class_name,
                    ragme_instance=ragme_instance,
                    env=env,
                    **kwargs
                )
                
        except Exception as e:
            logger.error(f"Error loading custom agent class '{class_name}': {str(e)}")
            raise

    def _load_from_uri(
        self,
        class_name: str,
        uri: str,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Load agent class from a URI (local file or GitHub repository)."""
        
        if self._is_github_uri(uri):
            return self._load_from_github(
                class_name=class_name,
                github_uri=uri,
                ragme_instance=ragme_instance,
                env=env,
                **kwargs
            )
        else:
            return self._load_from_file(
                class_name=class_name,
                file_path=uri,
                ragme_instance=ragme_instance,
                env=env,
                **kwargs
            )

    def _load_from_file(
        self,
        class_name: str,
        file_path: str,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Load agent class from a local file."""
        
        file_path = Path(file_path)
        
        # Make path relative to project root if it's relative
        if not file_path.is_absolute():
            # Assume relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            file_path = project_root / file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"Agent code file not found: {file_path}")
            
        # Load the module from file
        module_name = f"agent_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {file_path}")
            
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules to make it importable
        sys.modules[module_name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Get the class from the module
        agent_class = self._get_class_from_module(module, class_name)
        
        # Create and return instance
        return self._create_agent_instance(
            agent_class=agent_class,
            ragme_instance=ragme_instance,
            env=env,
            **kwargs
        )

    def _load_from_github(
        self,
        class_name: str,
        github_uri: str,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Load agent class from a GitHub repository."""
        
        # Parse GitHub URI
        parsed = urlparse(github_uri)
        
        if parsed.netloc != "github.com":
            raise ValueError(f"Only github.com repositories are supported, got: {github_uri}")
            
        # Extract repo info
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GitHub URI format: {github_uri}")
            
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Determine branch and file path
        branch = "main"  # default
        file_path = ""
        
        if len(path_parts) > 2:
            if path_parts[2] == "blob" and len(path_parts) > 4:
                branch = path_parts[3]
                file_path = "/".join(path_parts[4:])
            else:
                file_path = "/".join(path_parts[2:])
        
        # Clone or update the repository
        repo_dir = self._clone_or_update_github_repo(owner, repo, branch)
        
        # Load the agent from the cloned repository
        if file_path:
            full_file_path = repo_dir / file_path
        else:
            # Look for common agent file names
            full_file_path = self._find_agent_file_in_repo(repo_dir, class_name)
            
        if not full_file_path.exists():
            raise FileNotFoundError(f"Agent file not found in repository: {full_file_path}")
            
        return self._load_from_file(
            class_name=class_name,
            file_path=str(full_file_path),
            ragme_instance=ragme_instance,
            env=env,
            **kwargs
        )

    def _clone_or_update_github_repo(self, owner: str, repo: str, branch: str) -> Path:
        """Clone or update a GitHub repository."""
        
        repo_dir = self.agents_dir / f"{owner}_{repo}"
        
        if repo_dir.exists():
            # Repository already cloned, try to update
            try:
                subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True
                )
                logger.info(f"Updated repository {owner}/{repo}")
            except subprocess.CalledProcessError:
                logger.warning(f"Could not update repository {owner}/{repo}, using existing version")
        else:
            # Clone the repository
            try:
                clone_url = f"https://github.com/{owner}/{repo}.git"
                subprocess.run(
                    ["git", "clone", "-b", branch, clone_url, str(repo_dir)],
                    check=True,
                    capture_output=True
                )
                logger.info(f"Cloned repository {owner}/{repo}")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Could not clone repository {owner}/{repo}: {e}")
                
        return repo_dir

    def _find_agent_file_in_repo(self, repo_dir: Path, class_name: str) -> Path:
        """Find the agent file in a repository based on class name."""
        
        # Extract the class name without module path
        simple_class_name = class_name.split(".")[-1].lower()
        
        # Common patterns for agent files
        patterns = [
            f"{simple_class_name}.py",
            f"{simple_class_name}_agent.py",
            "agent.py",
            "main.py",
            "__init__.py"
        ]
        
        # Search in common directories
        search_dirs = [repo_dir, repo_dir / "src", repo_dir / "agents", repo_dir / "lib"]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for pattern in patterns:
                    candidate = search_dir / pattern
                    if candidate.exists():
                        return candidate
                        
        # If not found, return the first pattern in repo root
        return repo_dir / patterns[0]

    def _load_from_inline_code(
        self,
        class_name: str,
        code: str,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Load agent class from inline code."""
        
        # Create a temporary module from the code
        module_name = f"inline_agent_{hash(code)}"
        module = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(module_name, loader=None)
        )
        
        # Execute the code in the module
        exec(code, module.__dict__)
        
        # Get the class from the module
        agent_class = self._get_class_from_module(module, class_name)
        
        # Create and return instance
        return self._create_agent_instance(
            agent_class=agent_class,
            ragme_instance=ragme_instance,
            env=env,
            **kwargs
        )

    def _load_from_import(
        self,
        class_name: str,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Load agent class from direct import."""
        
        # Split class name into module and class parts
        parts = class_name.split(".")
        if len(parts) < 2:
            raise ValueError(f"Class name must be fully qualified: {class_name}")
            
        module_name = ".".join(parts[:-1])
        class_name_simple = parts[-1]
        
        # Import the module
        module = importlib.import_module(module_name)
        
        # Get the class
        if not hasattr(module, class_name_simple):
            raise AttributeError(f"Class '{class_name_simple}' not found in module '{module_name}'")
            
        agent_class = getattr(module, class_name_simple)
        
        # Create and return instance
        return self._create_agent_instance(
            agent_class=agent_class,
            ragme_instance=ragme_instance,
            env=env,
            **kwargs
        )

    def _get_class_from_module(self, module: Any, class_name: str) -> type:
        """Get a class from a module by name."""
        
        # Handle fully qualified names
        parts = class_name.split(".")
        class_name_simple = parts[-1]
        
        if hasattr(module, class_name_simple):
            return getattr(module, class_name_simple)
        
        # If not found, try to find any class that looks like an agent
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                attr_name.lower().endswith('agent') and 
                not attr_name.startswith('_')):
                return attr
                
        raise AttributeError(f"No agent class found in module")

    def _create_agent_instance(
        self,
        agent_class: type,
        ragme_instance: Optional[Any] = None,
        env: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Create an instance of an agent class."""
        
        try:
            # Try different constructor patterns
            if ragme_instance is not None:
                # Try with ragme_instance first
                return agent_class(ragme_instance)
            else:
                # Try with just keyword arguments
                return agent_class(**kwargs)
                
        except TypeError:
            # Try with no arguments
            try:
                return agent_class()
            except TypeError:
                # Try with env if available
                if env:
                    return agent_class(env=env)
                else:
                    raise

    def _is_github_uri(self, uri: str) -> bool:
        """Check if a URI is a GitHub repository URI."""
        return uri.startswith("https://github.com/") or uri.startswith("github.com/")

    def cleanup(self):
        """Clean up factory resources."""
        try:
            # Clear loaded modules
            self._loaded_modules.clear()
            logger.info("AgentFactory cleanup completed")
        except Exception as e:
            logger.error(f"Error during AgentFactory cleanup: {str(e)}")