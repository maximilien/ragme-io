# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import locale
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

    Loads configuration from config.yaml and agents.yaml, handles environment variable substitution.
    Provides a centralized way to access all application settings.
    """

    _instance: Optional["ConfigManager"] = None
    _config: dict[str, Any] | None = None
    _agents_config: dict[str, Any] | None = None

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

    def reload_config(self) -> None:
        """Reload the configuration from files."""
        self._config = None
        self._agents_config = None
        dotenv.load_dotenv()  # Reload environment variables

    @property
    def config(self) -> dict[str, Any]:
        """Get the configuration, loading it if necessary."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @property
    def agents_config(self) -> dict[str, Any]:
        """Get the agents configuration, loading it if necessary."""
        if self._agents_config is None:
            self._agents_config = self._load_agents_config()
        return self._agents_config

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

    def _load_agents_config(self) -> dict[str, Any]:
        """Load agents configuration from agents.yaml file."""
        # Look for agents.yaml in the project root directory
        agents_path = Path(__file__).parent.parent.parent.parent / "agents.yaml"

        if not agents_path.exists():
            # If agents.yaml doesn't exist, return empty config
            # This allows backward compatibility with inline agent configuration
            return {"agents": []}

        try:
            with open(agents_path, encoding="utf-8") as file:
                agents_config = yaml.safe_load(file)

            # Substitute environment variables in agents config
            agents_config = self._substitute_env_vars(agents_config)

            return agents_config if agents_config else {"agents": []}

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing agents configuration file: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading agents configuration: {e}") from e

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
                var_expr = match.group(1)
                # Handle ${VAR:-default} syntax
                if ":-" in var_expr:
                    var_name, default_value = var_expr.split(":-", 1)
                    env_value = os.getenv(var_name)
                    return env_value if env_value is not None else default_value
                else:
                    # Handle ${VAR} syntax
                    env_value = os.getenv(var_expr)
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
            db_name = self.get("databases.default")

        databases = self.get("databases.vector_databases", [])

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

        First checks agents.yaml, then falls back to inline agents in config.yaml
        for backward compatibility.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dictionary or None if not found
        """
        # First try agents.yaml
        agents_from_file = self.agents_config.get("agents", [])

        if isinstance(agents_from_file, list):
            for agent_config in agents_from_file:
                if (
                    isinstance(agent_config, dict)
                    and agent_config.get("name") == agent_name
                ):
                    return agent_config

        # Fallback to inline agents in config.yaml for backward compatibility
        agents_inline = self.get("agents", [])

        # Handle case where agents is not a list
        if not isinstance(agents_inline, list):
            return None

        for agent_config in agents_inline:
            # Handle case where agent_config is not a dict
            if (
                isinstance(agent_config, dict)
                and agent_config.get("name") == agent_name
            ):
                return agent_config

        return None

    def get_all_agents(self) -> list[dict[str, Any]]:
        """
        Get all agent configurations.

        Returns all agents from agents.yaml and falls back to config.yaml
        for backward compatibility.

        Returns:
            List of agent configuration dictionaries
        """
        # First try agents.yaml
        agents_from_file = self.agents_config.get("agents", [])

        if isinstance(agents_from_file, list) and agents_from_file:
            return agents_from_file

        # Fallback to inline agents in config.yaml for backward compatibility
        agents_inline = self.get("agents", [])

        if isinstance(agents_inline, list):
            return agents_inline

        return []

    def has_agents_file(self) -> bool:
        """
        Check if agents.yaml file exists.

        Returns:
            True if agents.yaml exists, False otherwise
        """
        agents_path = Path(__file__).parent.parent.parent.parent / "agents.yaml"
        return agents_path.exists()

    def get_agents_directory(self) -> str:
        """
        Get the agents directory path for storing downloaded agent code.

        Returns:
            Path to the agents directory
        """
        agents_dir = self.agents_config.get("agents_directory", "./agents")
        return str(Path(agents_dir).resolve())

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

    def get_i18n_config(self) -> dict[str, Any]:
        """Get internationalization configuration."""
        return self.get("i18n", {})

    def get_preferred_language(self) -> str:
        """
        Get the preferred language for LLM responses.

        Returns:
            ISO language code (e.g., "en", "fr", "es", "de") or "en" as default
        """
        i18n_config = self.get_i18n_config()
        preferred_language = i18n_config.get("preferred_language", "default")

        if preferred_language == "default":
            return self._detect_system_language()

        return preferred_language

    def get_preferred_locale(self) -> str:
        """
        Get the preferred locale for the system.

        Returns:
            ISO locale code (e.g., "en_US", "fr_FR", "es_ES", "de_DE") or "en_US" as default
        """
        i18n_config = self.get_i18n_config()
        preferred_locale = i18n_config.get("preferred_locale", "default")

        if preferred_locale == "default":
            return self._detect_system_locale()

        return preferred_locale

    def get_language_name(self, language_code: str | None = None) -> str:
        """
        Get the human-readable language name from ISO language code.

        Args:
            language_code: ISO language code (e.g., "en", "fr", "es", "de").
                          If None, uses the preferred language from config.

        Returns:
            Human-readable language name (e.g., "English", "French", "Spanish", "German")
        """
        if language_code is None:
            language_code = self.get_preferred_language()

        language_names = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "nl": "Dutch",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "pl": "Polish",
            "tr": "Turkish",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ms": "Malay",
            "tl": "Filipino",
            "uk": "Ukrainian",
            "be": "Belarusian",
            "ka": "Georgian",
            "hy": "Armenian",
            "az": "Azerbaijani",
            "kk": "Kazakh",
            "ky": "Kyrgyz",
            "uz": "Uzbek",
            "tg": "Tajik",
            "mn": "Mongolian",
            "my": "Burmese",
            "km": "Khmer",
            "lo": "Lao",
            "si": "Sinhala",
            "ne": "Nepali",
            "bn": "Bengali",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
            "or": "Odia",
            "as": "Assamese",
            "mr": "Marathi",
            "ur": "Urdu",
            "fa": "Persian",
            "ps": "Pashto",
            "sd": "Sindhi",
            "bo": "Tibetan",
            "dz": "Dzongkha",
            "am": "Amharic",
            "ti": "Tigrinya",
            "om": "Oromo",
            "so": "Somali",
            "sw": "Swahili",
            "zu": "Zulu",
            "xh": "Xhosa",
            "af": "Afrikaans",
            "is": "Icelandic",
            "ga": "Irish",
            "cy": "Welsh",
            "mt": "Maltese",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
            "mk": "Macedonian",
            "sq": "Albanian",
            "sr": "Serbian",
            "bs": "Bosnian",
            "me": "Montenegrin",
        }

        return language_names.get(language_code, "English")

    def _detect_system_language(self) -> str:
        """
        Detect the system's preferred language.

        Returns:
            ISO language code (e.g., "en", "fr", "es", "de")
        """
        try:
            # Try to get the system locale
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                # Extract language code from locale (e.g., "en_US" -> "en")
                language_code = system_locale.split("_")[0].lower()
                return language_code
        except (locale.Error, AttributeError, IndexError):
            pass

        # Fallback to environment variables
        for env_var in ["LANG", "LC_ALL", "LC_CTYPE"]:
            try:
                env_locale = os.getenv(env_var)
                if env_locale:
                    # Extract language code from locale (e.g., "en_US.UTF-8" -> "en")
                    language_code = env_locale.split("_")[0].split(".")[0].lower()
                    # Validate that it's a reasonable language code (2-3 characters, alphabetic)
                    if (
                        language_code
                        and len(language_code) <= 3
                        and language_code.isalpha()
                    ):
                        return language_code
            except (AttributeError, IndexError):
                continue

        # Final fallback to English
        return "en"

    def _detect_system_locale(self) -> str:
        """
        Detect the system's preferred locale.

        Returns:
            ISO locale code (e.g., "en_US", "fr_FR", "es_ES", "de_DE")
        """
        try:
            # Try to get the system locale
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                return system_locale
        except (locale.Error, AttributeError):
            pass

        # Fallback to environment variables
        for env_var in ["LANG", "LC_ALL", "LC_CTYPE"]:
            try:
                env_locale = os.getenv(env_var)
                if env_locale:
                    # Clean up locale string (e.g., "en_US.UTF-8" -> "en_US")
                    locale_code = env_locale.split(".")[0]
                    # Validate that it's a reasonable locale format (language_country)
                    if "_" in locale_code and len(locale_code.split("_")) == 2:
                        lang, country = locale_code.split("_")
                        if (
                            lang
                            and len(lang) <= 3
                            and lang.isalpha()
                            and country
                            and len(country) <= 3
                            and country.isalpha()
                        ):
                            return locale_code
            except (AttributeError, IndexError):
                continue

        # Final fallback to English US
        return "en_US"

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
            "i18n": True,  # All i18n config is safe
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

            # Update relevance thresholds
            if "relevance_thresholds" in settings:
                current_config["query"]["relevance_thresholds"] = settings[
                    "relevance_thresholds"
                ]

            # Update rerank settings (nested structure)
            if "rerank" in settings:
                if "rerank" not in current_config["query"]:
                    current_config["query"]["rerank"] = {}

                rerank_settings = settings["rerank"]

                # Update text reranking settings
                if "text" in rerank_settings:
                    if "text" not in current_config["query"]["rerank"]:
                        current_config["query"]["rerank"]["text"] = {}
                    current_config["query"]["rerank"]["text"].update(
                        rerank_settings["text"]
                    )

                # Update image reranking settings
                if "image" in rerank_settings:
                    if "image" not in current_config["query"]["rerank"]:
                        current_config["query"]["rerank"]["image"] = {}
                    current_config["query"]["rerank"]["image"].update(
                        rerank_settings["image"]
                    )

            # Write the updated config back to file
            config_path = Path("config.yaml")
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(current_config, f, default_flow_style=False, indent=2)

            # Reload the config
            self.reload()

        except Exception as e:
            raise Exception(f"Failed to update query settings: {str(e)}") from e

    def get_query_config(self) -> dict[str, Any]:
        """
        Get query configuration with proper defaults and nested structure handling.

        Returns:
            dict: Query configuration with defaults applied
        """
        query_config = self.config.get("query", {})

        # Ensure nested structure exists with defaults
        if "rerank" not in query_config:
            query_config["rerank"] = {}

        if "text" not in query_config["rerank"]:
            query_config["rerank"]["text"] = {"enabled": False, "top_k": 3}

        if "image" not in query_config["rerank"]:
            query_config["rerank"]["image"] = {"enabled": True, "top_k": 10}

        if "relevance_thresholds" not in query_config:
            query_config["relevance_thresholds"] = {"text": 0.4, "image": 0.3}

        # Ensure top_k exists
        if "top_k" not in query_config:
            query_config["top_k"] = 5

        return query_config

    def get_query_top_k(self) -> int:
        """Get the top_k setting for queries."""
        return self.get_query_config().get("top_k", 5)

    def get_query_text_rerank_enabled(self) -> bool:
        """Get whether text reranking is enabled."""
        return (
            self.get_query_config()
            .get("rerank", {})
            .get("text", {})
            .get("enabled", False)
        )

    def get_query_text_rerank_top_k(self) -> int:
        """Get the top_k setting for text reranking."""
        return self.get_query_config().get("rerank", {}).get("text", {}).get("top_k", 3)

    def get_query_image_rerank_enabled(self) -> bool:
        """Get whether image reranking is enabled."""
        return (
            self.get_query_config()
            .get("rerank", {})
            .get("image", {})
            .get("enabled", True)
        )

    def get_query_image_rerank_top_k(self) -> int:
        """Get the top_k setting for image reranking."""
        return (
            self.get_query_config().get("rerank", {}).get("image", {}).get("top_k", 10)
        )

    def get_query_text_relevance_threshold(self) -> float:
        """Get the text relevance threshold."""
        return self.get_query_config().get("relevance_thresholds", {}).get("text", 0.4)

    def get_query_image_relevance_threshold(self) -> float:
        """Get the image relevance threshold."""
        return self.get_query_config().get("relevance_thresholds", {}).get("image", 0.3)

    def get_authentication_config(self) -> dict[str, Any]:
        """Get authentication configuration."""
        return self.get("authentication", {})

    def is_login_bypassed(self) -> bool:
        """Check if login is bypassed."""
        return self.get("authentication.bypass_login", False)

    def get_oauth_config(self) -> dict[str, Any]:
        """Get OAuth configuration."""
        oauth_config = self.get("authentication.oauth", {})
        print(f"[DEBUG] get_oauth_config: {oauth_config}")
        return oauth_config

    def get_oauth_providers(self) -> dict[str, Any]:
        """Get OAuth providers configuration."""
        providers = self.get("authentication.oauth.providers", {})
        print(f"[DEBUG] get_oauth_providers: {providers}")
        return providers

    def get_oauth_provider_config(self, provider: str) -> dict[str, Any] | None:
        """Get configuration for a specific OAuth provider."""
        providers = self.get_oauth_providers()
        return providers.get(provider)

    def is_oauth_provider_enabled(self, provider: str) -> bool:
        """Check if an OAuth provider is enabled."""
        provider_config = self.get_oauth_provider_config(provider)
        return provider_config.get("enabled", False) if provider_config else False

    def get_session_config(self) -> dict[str, Any]:
        """Get session configuration."""
        return self.get("authentication.session", {})

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
