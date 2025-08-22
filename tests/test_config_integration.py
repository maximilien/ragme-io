# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ragme.utils.config_manager import ConfigManager, config


class TestConfigIntegration(unittest.TestCase):
    """Test configuration integration with actual config.yaml file."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_path = Path(__file__).parent.parent / "config.yaml"

        # Check if config is loaded - if not, many tests will be skipped
        self.config_loaded = config._config is not None and bool(config._config)

    def test_config_file_exists(self):
        """Test that the configuration file exists."""
        self.assertTrue(
            self.config_path.exists(),
            f"Configuration file not found at {self.config_path}",
        )

    def test_config_file_is_valid_yaml(self):
        """Test that the configuration file is valid YAML."""
        import yaml

        with open(self.config_path, encoding="utf-8") as file:
            try:
                config_data = yaml.safe_load(file)
                self.assertIsInstance(config_data, dict)
            except yaml.YAMLError as e:
                self.fail(f"Configuration file contains invalid YAML: {e}")

    def test_config_has_required_sections(self):
        """Test that configuration has all required sections."""
        if not self.config_loaded:
            self.skipTest("Configuration not loaded - skipping section tests")

        required_sections = [
            "application",
            "network",
            "vector_databases",
            "agents",
            "mcp_servers",
            "frontend",
            "features",
            "environment",
        ]

        for section in required_sections:
            with self.subTest(section=section):
                section_data = config.get(section)
                self.assertIsNotNone(
                    section_data, f"Required section '{section}' missing from config"
                )

    def test_application_section_structure(self):
        """Test application section structure."""
        if config._config is None:
            self.skipTest("Configuration not loaded")

        app_config = config.get("application", {})
        if not app_config:
            self.skipTest("Application section not found in config")

        required_fields = ["name", "version", "title", "description"]
        for field in required_fields:
            with self.subTest(field=field):
                self.assertIn(
                    field,
                    app_config,
                    f"Application section missing required field: {field}",
                )
                self.assertIsInstance(
                    app_config[field], str, f"Application.{field} should be a string"
                )

    def test_network_section_structure(self):
        """Test network section structure."""
        network_config = config.get_network_config()

        # Test API configuration
        self.assertIn("api", network_config)
        api_config = network_config["api"]
        self.assertIn("host", api_config)
        self.assertIn("port", api_config)
        self.assertIsInstance(api_config["port"], int)

        # Test MCP configuration
        self.assertIn("mcp", network_config)
        mcp_config = network_config["mcp"]
        self.assertIn("host", mcp_config)
        self.assertIn("port", mcp_config)
        self.assertIsInstance(mcp_config["port"], int)

    def test_vector_databases_section_structure(self):
        """Test vector databases section structure."""
        vdb_config = config.get("vector_databases", {})

        # Test default database is specified
        self.assertIn("default", vdb_config)
        self.assertIsInstance(vdb_config["default"], str)

        # Test databases list exists
        self.assertIn("databases", vdb_config)
        self.assertIsInstance(vdb_config["databases"], list)
        self.assertGreater(len(vdb_config["databases"]), 0)

        # Test each database has required fields
        for db in vdb_config["databases"]:
            with self.subTest(db=db.get("name", "unknown")):
                required_fields = ["name", "type", "collections"]
                for field in required_fields:
                    self.assertIn(
                        field, db, f"Database missing required field: {field}"
                    )

                # Test that collections is a list and has at least one collection
                collections = db.get("collections", [])
                self.assertIsInstance(collections, list, "collections should be a list")
                self.assertGreater(
                    len(collections), 0, "Database should have at least one collection"
                )

                # Test each collection has required fields
                for collection in collections:
                    self.assertIn(
                        "name", collection, "Collection missing required field: name"
                    )
                    self.assertIn(
                        "type", collection, "Collection missing required field: type"
                    )

    def test_default_database_exists_in_list(self):
        """Test that default database exists in databases list."""
        vdb_config = config.get("vector_databases", {})
        default_db = vdb_config.get("default")
        databases = vdb_config.get("databases", [])

        db_names = [db.get("name") for db in databases]
        self.assertIn(
            default_db,
            db_names,
            f"Default database '{default_db}' not found in databases list",
        )

    def test_agents_section_structure(self):
        """Test agents section structure."""
        agents = config.get("agents", [])

        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0, "No agents configured")

        # Test each agent has required fields
        for agent in agents:
            with self.subTest(agent=agent.get("name", "unknown")):
                required_fields = ["name", "type", "llm_model"]
                for field in required_fields:
                    self.assertIn(
                        field, agent, f"Agent missing required field: {field}"
                    )

    def test_mcp_servers_section_structure(self):
        """Test MCP servers section structure."""
        mcp_servers = config.get_all_mcp_servers()

        self.assertIsInstance(mcp_servers, list)
        self.assertGreater(len(mcp_servers), 0, "No MCP servers configured")

        # Test each server has required fields
        for server in mcp_servers:
            with self.subTest(server=server.get("name", "unknown")):
                required_fields = ["name", "icon"]
                for field in required_fields:
                    self.assertIn(
                        field, server, f"MCP server missing required field: {field}"
                    )

    def test_features_section_structure(self):
        """Test features section structure."""
        features = config.get("features", {})

        self.assertIsInstance(features, dict)

        # Test common features exist and are boolean
        common_features = [
            "document_summarization",
            "mcp_integration",
            "real_time_updates",
            "file_upload",
            "url_crawling",
            "json_ingestion",
        ]

        for feature in common_features:
            with self.subTest(feature=feature):
                if feature in features:
                    self.assertIsInstance(
                        features[feature],
                        bool,
                        f"Feature '{feature}' should be boolean",
                    )

    def test_environment_section_structure(self):
        """Test environment section structure."""
        env_config = config.get("environment", {})

        # Test required environment variables
        if "required" in env_config:
            required_vars = env_config["required"]
            self.assertIsInstance(required_vars, list)
            # Should at least require OPENAI_API_KEY
            self.assertIn("OPENAI_API_KEY", required_vars)

        # Test optional environment variables
        if "optional" in env_config:
            optional_vars = env_config["optional"]
            self.assertIsInstance(optional_vars, list)

    def test_config_manager_methods_work_with_real_config(self):
        """Test that ConfigManager methods work with the real configuration."""
        # Test database access
        default_db_config = config.get_database_config()
        self.assertIsNotNone(default_db_config)
        self.assertIn("name", default_db_config)

        # Test agent access
        agents = config.get("agents", [])
        if agents:
            first_agent = agents[0]
            agent_config = config.get_agent_config(first_agent["name"])
            self.assertIsNotNone(agent_config)
            self.assertEqual(agent_config["name"], first_agent["name"])

        # Test MCP server access
        mcp_servers = config.get_all_mcp_servers()
        if mcp_servers:
            first_server = mcp_servers[0]
            server_config = config.get_mcp_server_config(first_server["name"])
            self.assertIsNotNone(server_config)
            self.assertEqual(server_config["name"], first_server["name"])

    def test_feature_flags_work(self):
        """Test that feature flag checking works with real config."""
        # Test a feature that should exist
        features = config.get("features", {})
        if features:
            # Pick any feature from the config
            feature_name = list(features.keys())[0]
            expected_value = features[feature_name]
            actual_value = config.is_feature_enabled(feature_name)
            self.assertEqual(actual_value, expected_value)

        # Test a feature that doesn't exist (should return False)
        self.assertFalse(config.is_feature_enabled("nonexistent_feature"))

    def test_dot_notation_access_works_with_real_config(self):
        """Test dot notation access with real configuration."""
        # Test application name
        app_name = config.get("application.name")
        self.assertIsNotNone(app_name)
        self.assertIsInstance(app_name, str)

        # Test network port
        api_port = config.get("network.api.port")
        self.assertIsNotNone(api_port)
        self.assertIsInstance(api_port, int)

        # Test default database
        default_db = config.get("vector_databases.default")
        self.assertIsNotNone(default_db)
        self.assertIsInstance(default_db, str)

    def test_config_sections_contain_expected_data_types(self):
        """Test that configuration sections contain expected data types."""
        # Test that ports are integers
        api_port = config.get("network.api.port")
        if api_port is not None:
            self.assertIsInstance(api_port, int)
            self.assertGreater(api_port, 0)
            self.assertLess(api_port, 65536)

        # Test that boolean features are actually boolean
        features = config.get("features", {})
        for feature_name, feature_value in features.items():
            with self.subTest(feature=feature_name):
                self.assertIsInstance(
                    feature_value,
                    bool,
                    f"Feature '{feature_name}' should be boolean, got {type(feature_value)}",
                )

    @patch.dict(os.environ, {"TEST_ENV_VAR": "test_value"})
    def test_environment_variable_substitution_in_real_config(self):
        """Test environment variable substitution with real config."""
        # Create a test config manager to test substitution
        test_config = ConfigManager()

        # Test data with environment variable
        test_data = {"test_value": "${TEST_ENV_VAR}"}
        result = test_config._substitute_env_vars(test_data)

        self.assertEqual(result["test_value"], "test_value")

    def test_safe_config_excludes_sensitive_data(self):
        """Test that safe configuration excludes sensitive data from real config."""
        safe_config = config.get_safe_frontend_config()

        # Should include safe sections
        expected_safe_sections = [
            "application",
            "frontend",
            "client",
            "mcp_servers",
            "features",
        ]
        for section in expected_safe_sections:
            with self.subTest(section=section):
                self.assertIn(
                    section,
                    safe_config,
                    f"Safe config missing expected section: {section}",
                )

        # Should exclude sensitive sections
        sensitive_sections = ["vector_databases", "environment", "network", "agents"]
        for section in sensitive_sections:
            with self.subTest(section=section):
                self.assertNotIn(
                    section,
                    safe_config,
                    f"Safe config should not include sensitive section: {section}",
                )

    def test_global_config_instance_works(self):
        """Test that the global config instance works correctly."""
        from src.ragme.utils.config_manager import config as global_config

        # Test that it's a ConfigManager instance
        self.assertIsInstance(global_config, ConfigManager)

        # Test that it has loaded configuration
        self.assertIsNotNone(global_config._config)

        # Test that methods work
        app_name = global_config.get("application.name")
        self.assertIsNotNone(app_name)


if __name__ == "__main__":
    unittest.main()
