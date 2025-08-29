# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import re
import warnings
from pathlib import Path
from typing import Any, Optional

import dotenv
import yaml

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)


class ConfigManager:
    """
    Configuration manager for RAGme application.

    Loads configuration from config.yaml and handles environment variable substitution.
    Provides a centralized way to access all application settings.
    """

    _instance: Optional["ConfigManager"] = None
    _config: dict[str, Any] | None = None

    def __new__(cls) -> "ConfigManager":
        """Singleton pattern to ensure only one config manager instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the configuration manager."""
        if self._config is None:
            # Load environment variables first
            dotenv.load_dotenv()
            # Note: Config will be loaded lazily when first accessed

    @property
    def config(self) -> dict[str, Any]:
        """Get the configuration, loading it if necessary."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from config.yaml file."""
        # Look for config.yaml in the project root directory
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as file:
                config = yaml.safe_load(file)

            # Substitute environment variables
            config = self._substitute_env_vars(config)

            # Validate required environment variables
            self._validate_required_env_vars(config)

            return config

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading configuration: {e}") from e

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Variables in format ${VAR_NAME} are replaced with their environment values.
        """
        if isinstance(obj, dict):
            return {key: self._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Pattern to match ${VAR_NAME}
            pattern = r"\$\{([^}]+)\}"

            def replace_var(match):
                var_name = match.group(1)
                env_value = os.getenv(var_name)
                if env_value is None:
                    # Keep the placeholder if environment variable is not set
                    return match.group(0)
                return env_value

            return re.sub(pattern, replace_var, obj)
        else:
            return obj

    def _validate_required_env_vars(self, config: dict[str, Any]) -> None:
        """Validate that all required environment variables are set."""
        required_vars = config.get("environment", {}).get("required", [])

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Required environment variables not set: {', '.join(missing_vars)}"
            )

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the configuration value (e.g., 'network.api.port')
            default: Default value to return if key is not found

        Returns:
            Configuration value or default if not found

        Examples:
            config.get('network.api.port')  # Returns 8021
            config.get('vector_databases.default')  # Returns 'weaviate-local'
        """
        try:
            keys = key_path.split(".")
            current = self.config

            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError, FileNotFoundError):
            return default

    def get_database_config(self, db_name: str | None = None) -> dict[str, Any] | None:
        """
        Get vector database configuration by name.

        Args:
            db_name: Name of the database configuration. If None, returns default database.

        Returns:
            Database configuration dictionary or None if not found
        """
        if db_name is None:
            db_name = self.get("vector_databases.default")

        databases = self.get("vector_databases.databases", [])

        # Handle case where databases is not a list
        if not isinstance(databases, list):
            return None

        for db_config in databases:
            # Handle case where db_config is not a dict
            if isinstance(db_config, dict) and db_config.get("name") == db_name:
                return db_config

        return None

    def get_collections_config(
        self, db_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get collections configuration for a vector database.

        Args:
            db_name: Name of the database configuration. If None, uses default database.

        Returns:
            List of collection configurations or empty list if not found
        """
        db_config = self.get_database_config(db_name)
        if db_config is None:
            return []

        collections = db_config.get("collections", [])

        # Handle legacy collection_name format
        if not collections and "collection_name" in db_config:
            # Convert legacy format to new format
            collections = [{"name": db_config["collection_name"], "type": "text"}]

        return collections if isinstance(collections, list) else []

    def get_text_collection_name(self, db_name: str | None = None) -> str:
        """
        Get the name of the text collection from configuration.

        Args:
            db_name: Name of the database configuration. If None, uses default database.

        Returns:
            Name of the text collection, defaults to "RagMeDocs"
        """
        # Environment override (new) and backward compatibility (legacy)
        env_override = os.getenv("VECTOR_DB_TEXT_COLLECTION_NAME")
        if env_override:
            return env_override

        collections = self.get_collections_config(db_name)
        import re

        placeholder_pattern = re.compile(r"^\$\{[^}]+\}$")

        for collection in collections:
            if isinstance(collection, dict) and collection.get("type") == "text":
                name = collection.get("name", "RagMeDocs")
                # If name is an unsubstituted placeholder like ${VAR}, ignore and fallback
                if isinstance(name, str) and placeholder_pattern.match(name):
                    continue
                return name

        # Fallback to default
        return "RagMeDocs"

    def get_image_collection_name(self, db_name: str | None = None) -> str:
        """
        Get the name of the image collection from configuration.

        Args:
            db_name: Name of the database configuration. If None, uses default database.

        Returns:
            Name of the image collection, defaults to "RagMeImages"
        """
        # Environment override for convenience
        env_override = os.getenv("VECTOR_DB_IMAGE_COLLECTION_NAME")
        if env_override:
            return env_override
        collections = self.get_collections_config(db_name)

        import re

        placeholder_pattern = re.compile(r"^\$\{[^}]+\}$")

        for collection in collections:
            if isinstance(collection, dict) and collection.get("type") == "image":
                name = collection.get("name", "RagMeImages")
                if isinstance(name, str) and placeholder_pattern.match(name):
                    continue
                return name

        # Fallback to default
        return "RagMeImages"

    def get_embedding_model(self, db_name: str | None = None) -> str:
        """
        Get the text embedding model from configuration.

        Args:
            db_name: Name of the database configuration. If None, uses default database.

        Returns:
            Text embedding model name, defaults to "text-embedding-3-large"
        """
        db_config = self.get_database_config(db_name)
        if db_config is None:
            return "text-embedding-3-large"

        return db_config.get("embedding_model", "text-embedding-3-large")

    def get_image_embedding_model(self, db_name: str | None = None) -> str:
        """
        Get the image embedding model from configuration.

        Args:
            db_name: Name of the database configuration. If None, uses default database.

        Returns:
            Image embedding model name, defaults to "text-embedding-3-large"
        """
        db_config = self.get_database_config(db_name)
        if db_config is None:
            return "text-embedding-3-large"

        return db_config.get("image_embedding_model", "text-embedding-3-large")

    def get_storage_config(self) -> dict[str, Any]:
        """
        Get storage service configuration.

        Returns:
            Storage configuration dictionary
        """
        return self.get("storage", {})

    def get_storage_type(self) -> str:
        """
        Get the storage service type.

        Returns:
            Storage type (minio, s3, local), defaults to "minio"
        """
        return self.get("storage.type", "minio")

    def get_storage_backend_config(
        self, backend_type: str | None = None
    ) -> dict[str, Any]:
        """
        Get configuration for a specific storage backend.

        Args:
            backend_type: Storage backend type (minio, s3, local). If None, uses current storage type.

        Returns:
            Backend configuration dictionary
        """
        if backend_type is None:
            backend_type = self.get_storage_type()

        return self.get(f"storage.{backend_type}", {})

    def get_storage_bucket_name(self) -> str:
        """
        Get the storage bucket name for the current storage type.

        Returns:
            Bucket name, defaults to "ragme-storage"
        """
        backend_config = self.get_storage_backend_config()
        return backend_config.get("bucket_name", "ragme-storage")

    def is_copy_uploaded_docs_enabled(self) -> bool:
        """
        Check if copying uploaded documents to storage is enabled.

        Returns:
            True if copying documents is enabled, False otherwise
        """
        return self.get("storage.copy_uploaded_docs", False)

    def is_copy_uploaded_images_enabled(self) -> bool:
        """
        Check if copying uploaded images to storage is enabled.

        Returns:
            True if copying images is enabled, False otherwise
        """
        return self.get("storage.copy_uploaded_images", False)

    def get_agent_config(self, agent_name: str) -> dict[str, Any] | None:
        """
        Get agent configuration by name.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dictionary or None if not found
        """
        agents = self.get("agents", [])

        # Handle case where agents is not a list
        if not isinstance(agents, list):
            return None

        for agent_config in agents:
            # Handle case where agent_config is not a dict
            if (
                isinstance(agent_config, dict)
                and agent_config.get("name") == agent_name
            ):
                return agent_config

        return None

    def get_mcp_server_config(self, server_name: str) -> dict[str, Any] | None:
        """
        Get MCP server configuration by name.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCP server configuration dictionary or None if not found
        """
        servers = self.get("mcp_servers", [])

        for server_config in servers:
            if server_config.get("name") == server_name:
                return server_config

        return None

    def get_all_mcp_servers(self) -> list[dict[str, Any]]:
        """Get all MCP server configurations."""
        servers = self.get("mcp_servers", [])
        # Handle case where mcp_servers is not a list
        if not isinstance(servers, list):
            return []
        return servers

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature_name: Name of the feature

        Returns:
            True if feature is enabled, False otherwise
        """
        return self.get(f"features.{feature_name}", False)

    def get_network_config(self) -> dict[str, Any]:
        """Get network configuration."""
        return self.get("network", {})

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration."""
        return self.get("llm", {})

    def get_frontend_config(self) -> dict[str, Any]:
        """Get frontend configuration."""
        return self.get("frontend", {})

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})

    def get_client_config(self) -> dict[str, Any]:
        """Get client customization configuration."""
        return self.get("client", {})

    def get_ocr_config(self) -> dict[str, Any]:
        """Get OCR configuration."""
        return self.get("ocr", {})

    def get_safe_config(self) -> dict[str, Any]:
        """
        Get configuration safe for frontend/API exposure.

        This method only includes explicitly safe sections and filters out all sensitive data.

        Returns:
            Configuration dictionary with only safe, non-sensitive data
        """
        try:
            config_data = self.config
        except FileNotFoundError:
            return {}

        # Only include explicitly safe sections
        safe_sections = {
            "application": ["name", "version", "title", "description"],
            "frontend": True,  # All frontend config is safe
            "client": True,  # All client config is safe
            "features": True,  # All feature flags are safe
            "logging": [
                "level",
                "format",
                "date_format",
            ],  # Only non-sensitive logging config
        }

        safe_config = {}

        for section_name, allowed_fields in safe_sections.items():
            section_data = config_data.get(section_name, {})
            if not section_data:
                continue

            if allowed_fields is True:
                # Include entire section
                safe_config[section_name] = section_data
            elif isinstance(allowed_fields, list):
                # Include only specified fields
                safe_section = {}
                for field in allowed_fields:
                    if field in section_data:
                        safe_section[field] = section_data[field]
                if safe_section:
                    safe_config[section_name] = safe_section

        return safe_config

    def get_safe_frontend_config(self) -> dict[str, Any]:
        """Get frontend configuration safe for API exposure."""
        safe_config = self.get_safe_config()

        # Add safe MCP server configurations (filtered for security)
        try:
            mcp_servers = self.config.get("mcp_servers", [])
        except FileNotFoundError:
            mcp_servers = []
        safe_mcp_servers = []
        for server in mcp_servers:
            if isinstance(server, dict):
                safe_server = {
                    "name": server.get("name"),
                    "icon": server.get("icon"),
                    "enabled": server.get("enabled", False),
                    "description": server.get("description", ""),
                }
                # Only include URL if it's localhost (safe to expose)
                url = server.get("url", "")
                if url and ("localhost" in url or "127.0.0.1" in url):
                    safe_server["url"] = url
                safe_mcp_servers.append(safe_server)

        return {
            "application": safe_config.get("application", {}),
            "frontend": safe_config.get("frontend", {}),
            "client": safe_config.get("client", {}),
            "mcp_servers": safe_mcp_servers,
            "features": safe_config.get("features", {}),
        }

    def reload(self) -> None:
        """Reload configuration from file."""
        self._config = self._load_config()

    def update_query_settings(self, settings: dict[str, Any]) -> None:
        """
        Update query settings in the configuration file.

        Args:
            settings: Dictionary containing query settings to update
        """
        try:
            # Get the current config
            current_config = self.config

            # Update the query section
            if "query" not in current_config:
                current_config["query"] = {}

            # Update individual settings
            if "top_k" in settings:
                current_config["query"]["top_k"] = settings["top_k"]

            if "text_rerank_top_k" in settings:
                current_config["query"]["text_rerank_top_k"] = settings[
                    "text_rerank_top_k"
                ]

            if "relevance_thresholds" in settings:
                current_config["query"]["relevance_thresholds"] = settings[
                    "relevance_thresholds"
                ]

            # Write the updated config back to file
            config_path = Path("config.yaml")
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(current_config, f, default_flow_style=False, indent=2)

            # Reload the config
            self.reload()

        except Exception as e:
            raise Exception(f"Failed to update query settings: {str(e)}") from e

    def __str__(self) -> str:
        """String representation of the configuration."""
        try:
            config_keys = list(self.config.keys())
        except FileNotFoundError:
            config_keys = []
        return f"ConfigManager(config_keys={config_keys})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


# Global configuration instance
config = ConfigManager()
