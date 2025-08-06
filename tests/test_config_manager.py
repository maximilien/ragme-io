# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import yaml

from src.ragme.utils.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test configuration manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test configuration
        self.test_config = {
            "application": {
                "name": "TestRAGme",
                "version": "1.0.0",
                "title": "Test RAGme Assistant",
            },
            "network": {
                "api": {"host": "0.0.0.0", "port": 8021, "cors_origins": ["*"]},
                "mcp": {"host": "0.0.0.0", "port": 8022},
            },
            "vector_databases": {
                "default": "weaviate-local",
                "databases": [
                    {
                        "name": "weaviate-local",
                        "type": "weaviate-local",
                        "url": "http://localhost:8080",
                        "collection_name": "TestDocs",
                    },
                    {
                        "name": "weaviate-cloud",
                        "type": "weaviate",
                        "url": "${WEAVIATE_URL}",
                        "api_key": "${WEAVIATE_API_KEY}",
                        "collection_name": "TestDocs",
                    },
                ],
            },
            "agents": [
                {"name": "test-agent", "type": "ragme", "llm_model": "gpt-4o-mini"}
            ],
            "mcp_servers": [
                {
                    "name": "Test Server",
                    "icon": "fas fa-test",
                    "enabled": True,
                    "url": "http://localhost:8022",
                }
            ],
            "features": {"test_feature": True, "disabled_feature": False},
            "environment": {
                "required": ["TEST_REQUIRED_VAR"],
                "optional": ["TEST_OPTIONAL_VAR"],
            },
        }

    def test_singleton_pattern(self):
        """Test that ConfigManager follows singleton pattern."""
        config1 = ConfigManager()
        config2 = ConfigManager()
        self.assertIs(config1, config2)

    @patch("src.ragme.utils.config_manager.dotenv.load_dotenv")
    @patch("src.ragme.utils.config_manager.yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch.dict(os.environ, {"TEST_REQUIRED_VAR": "test_value"})
    def test_load_config_success(self, mock_exists, mock_file, mock_yaml, mock_dotenv):
        """Test successful configuration loading."""
        mock_exists.return_value = True
        mock_yaml.return_value = self.test_config

        # Create a fresh ConfigManager instance for testing
        with patch.object(ConfigManager, "_instance", None):
            config = ConfigManager()
            result = config._config

        self.assertEqual(result["application"]["name"], "TestRAGme")
        mock_yaml.assert_called()
        mock_dotenv.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_load_config_file_not_found(self, mock_exists):
        """Test configuration loading when file doesn't exist."""
        mock_exists.return_value = False

        config = ConfigManager()
        config._config = None  # Reset for testing

        with self.assertRaises(FileNotFoundError):
            config._load_config()

    @patch("src.ragme.utils.config_manager.dotenv.load_dotenv")
    @patch("src.ragme.utils.config_manager.yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_load_config_yaml_error(
        self, mock_exists, mock_file, mock_yaml, mock_dotenv
    ):
        """Test configuration loading with YAML parsing error."""
        mock_exists.return_value = True
        mock_yaml.side_effect = yaml.YAMLError("Invalid YAML")

        with patch.object(ConfigManager, "_instance", None):
            with self.assertRaises(ValueError) as context:
                ConfigManager()

        self.assertIn("Error parsing configuration file", str(context.exception))

    def test_environment_variable_substitution(self):
        """Test environment variable substitution."""
        config = ConfigManager()

        test_data = {
            "simple": "${TEST_VAR}",
            "nested": {"value": "${NESTED_VAR}"},
            "list": ["${LIST_VAR}", "static"],
            "mixed": "prefix-${MIXED_VAR}-suffix",
        }

        with patch.dict(
            os.environ,
            {
                "TEST_VAR": "test_value",
                "NESTED_VAR": "nested_value",
                "LIST_VAR": "list_value",
                "MIXED_VAR": "mixed_value",
            },
        ):
            result = config._substitute_env_vars(test_data)

        self.assertEqual(result["simple"], "test_value")
        self.assertEqual(result["nested"]["value"], "nested_value")
        self.assertEqual(result["list"][0], "list_value")
        self.assertEqual(result["mixed"], "prefix-mixed_value-suffix")

    def test_environment_variable_substitution_missing(self):
        """Test environment variable substitution with missing variables."""
        config = ConfigManager()

        test_data = {"missing": "${MISSING_VAR}"}

        # Test that missing environment variables are handled gracefully
        result = config._substitute_env_vars(test_data)

        # Should return original placeholder when var is missing
        self.assertEqual(result["missing"], "${MISSING_VAR}")

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_required_env_vars_missing(self):
        """Test validation with missing required environment variables."""
        config = ConfigManager()

        test_config = {"environment": {"required": ["MISSING_VAR1", "MISSING_VAR2"]}}

        with self.assertRaises(ValueError) as context:
            config._validate_required_env_vars(test_config)

        error_msg = str(context.exception)
        self.assertIn("Required environment variables not set", error_msg)
        self.assertIn("MISSING_VAR1", error_msg)
        self.assertIn("MISSING_VAR2", error_msg)

    @patch.dict(os.environ, {"REQUIRED_VAR": "value"})
    def test_validate_required_env_vars_success(self):
        """Test validation with all required environment variables present."""
        config = ConfigManager()

        test_config = {"environment": {"required": ["REQUIRED_VAR"]}}

        # Should not raise an exception
        config._validate_required_env_vars(test_config)

    def test_get_with_dot_notation(self):
        """Test getting configuration values with dot notation."""
        config = ConfigManager()
        config._config = self.test_config

        # Test simple access
        self.assertEqual(config.get("application.name"), "TestRAGme")

        # Test nested access
        self.assertEqual(config.get("network.api.port"), 8021)

        # Test with default value
        self.assertEqual(config.get("nonexistent.key", "default"), "default")

        # Test with None config
        config._config = None
        self.assertEqual(config.get("any.key", "default"), "default")

    def test_get_database_config(self):
        """Test getting database configuration."""
        config = ConfigManager()
        config._config = self.test_config

        # Test getting specific database
        db_config = config.get_database_config("weaviate-local")
        self.assertEqual(db_config["name"], "weaviate-local")
        self.assertEqual(db_config["url"], "http://localhost:8080")

        # Test getting default database
        default_db = config.get_database_config()
        self.assertEqual(default_db["name"], "weaviate-local")

        # Test non-existent database
        self.assertIsNone(config.get_database_config("nonexistent"))

    def test_get_agent_config(self):
        """Test getting agent configuration."""
        config = ConfigManager()
        config._config = self.test_config

        # Test existing agent
        agent_config = config.get_agent_config("test-agent")
        self.assertEqual(agent_config["name"], "test-agent")
        self.assertEqual(agent_config["llm_model"], "gpt-4o-mini")

        # Test non-existent agent
        self.assertIsNone(config.get_agent_config("nonexistent"))

    def test_get_mcp_server_config(self):
        """Test getting MCP server configuration."""
        config = ConfigManager()
        config._config = self.test_config

        # Test existing server
        server_config = config.get_mcp_server_config("Test Server")
        self.assertEqual(server_config["name"], "Test Server")
        self.assertEqual(server_config["url"], "http://localhost:8022")

        # Test non-existent server
        self.assertIsNone(config.get_mcp_server_config("nonexistent"))

    def test_get_all_mcp_servers(self):
        """Test getting all MCP server configurations."""
        config = ConfigManager()
        config._config = self.test_config

        servers = config.get_all_mcp_servers()
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["name"], "Test Server")

    def test_is_feature_enabled(self):
        """Test feature flag checking."""
        config = ConfigManager()
        config._config = self.test_config

        # Test enabled feature
        self.assertTrue(config.is_feature_enabled("test_feature"))

        # Test disabled feature
        self.assertFalse(config.is_feature_enabled("disabled_feature"))

        # Test non-existent feature (should default to False)
        self.assertFalse(config.is_feature_enabled("nonexistent_feature"))

    def test_get_network_config(self):
        """Test getting network configuration."""
        config = ConfigManager()
        config._config = self.test_config

        network_config = config.get_network_config()
        self.assertEqual(network_config["api"]["port"], 8021)
        self.assertEqual(network_config["mcp"]["port"], 8022)

    def test_get_frontend_config(self):
        """Test getting frontend configuration."""
        config = ConfigManager()
        config._config = {
            "frontend": {"settings": {"max_documents": 50}, "ui": {"theme": "dark"}}
        }

        frontend_config = config.get_frontend_config()
        self.assertEqual(frontend_config["settings"]["max_documents"], 50)
        self.assertEqual(frontend_config["ui"]["theme"], "dark")

    def test_get_client_config(self):
        """Test getting client configuration."""
        config = ConfigManager()
        config._config = {
            "client": {
                "branding": {"primary_color": "#blue"},
                "welcome_message": "Welcome!",
            }
        }

        client_config = config.get_client_config()
        self.assertEqual(client_config["branding"]["primary_color"], "#blue")
        self.assertEqual(client_config["welcome_message"], "Welcome!")

    def test_get_llm_config(self):
        """Test getting LLM configuration."""
        config = ConfigManager()
        config._config = {"llm": {"default_model": "gpt-4o-mini", "temperature": 0.7}}

        llm_config = config.get_llm_config()
        self.assertEqual(llm_config["default_model"], "gpt-4o-mini")
        self.assertEqual(llm_config["temperature"], 0.7)

    def test_get_logging_config(self):
        """Test getting logging configuration."""
        config = ConfigManager()
        config._config = {"logging": {"level": "DEBUG", "format": "%(message)s"}}

        logging_config = config.get_logging_config()
        self.assertEqual(logging_config["level"], "DEBUG")
        self.assertEqual(logging_config["format"], "%(message)s")

    def test_reload_config(self):
        """Test configuration reloading."""
        config = ConfigManager()
        original_config = config._config

        with patch.object(config, "_load_config", return_value={"new": "config"}):
            config.reload()

        self.assertEqual(config._config, {"new": "config"})
        self.assertNotEqual(config._config, original_config)

    def test_string_representations(self):
        """Test string representations of ConfigManager."""
        config = ConfigManager()
        config._config = {"test": "config"}

        # Test __str__
        str_repr = str(config)
        self.assertIn("ConfigManager", str_repr)
        self.assertIn("test", str_repr)

        # Test __repr__
        repr_str = repr(config)
        self.assertIn("ConfigManager", repr_str)
        self.assertIn("test", repr_str)

    def test_empty_config_handling(self):
        """Test handling of empty or None configuration."""
        config = ConfigManager()
        config._config = {}

        # Test with empty config
        self.assertEqual(config.get("any.key"), None)
        self.assertEqual(config.get_network_config(), {})
        self.assertEqual(config.get_all_mcp_servers(), [])
        self.assertFalse(config.is_feature_enabled("any_feature"))

        # Test with None config
        config._config = None
        self.assertEqual(config.get("any.key"), None)

    def test_malformed_config_sections(self):
        """Test handling of malformed configuration sections."""
        config = ConfigManager()

        # Test with non-list agents section
        config._config = {"agents": "invalid"}
        # Should handle gracefully and return None
        result = config.get_agent_config("test")
        self.assertIsNone(result)

        # Test with non-list mcp_servers section
        config._config = {"mcp_servers": "invalid"}
        # Should handle gracefully and return empty list
        result = config.get_all_mcp_servers()
        self.assertEqual(result, [])

        # Test with non-dict database in databases list
        config._config = {
            "vector_databases": {
                "databases": ["invalid", {"name": "valid", "type": "test"}]
            }
        }
        db_config = config.get_database_config("valid")
        self.assertEqual(db_config["name"], "valid")

    def test_complex_dot_notation_access(self):
        """Test complex dot notation access patterns."""
        config = ConfigManager()
        config._config = {
            "level1": {"level2": {"level3": {"value": "deep_value"}}},
            "array": [{"name": "item1"}, {"name": "item2"}],
        }

        # Test deep nesting
        self.assertEqual(config.get("level1.level2.level3.value"), "deep_value")

        # Test partial path
        level2 = config.get("level1.level2")
        self.assertEqual(level2["level3"]["value"], "deep_value")

        # Test invalid path
        self.assertIsNone(config.get("level1.invalid.path"))

        # Test accessing array (should work but return the array)
        array = config.get("array")
        self.assertEqual(len(array), 2)
        self.assertEqual(array[0]["name"], "item1")


if __name__ == "__main__":
    unittest.main()
