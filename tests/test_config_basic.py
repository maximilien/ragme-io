# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import unittest
from pathlib import Path

from src.ragme.utils.config_manager import ConfigManager


class TestConfigBasic(unittest.TestCase):
    """Basic configuration tests that work regardless of config loading issues."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_path = Path(__file__).parent.parent / "config.yaml"

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
                self.assertGreater(len(config_data), 0, "Configuration file is empty")
            except yaml.YAMLError as e:
                self.fail(f"Configuration file contains invalid YAML: {e}")

    def test_config_manager_can_be_instantiated(self):
        """Test that ConfigManager can be instantiated."""
        try:
            config_manager = ConfigManager()
            self.assertIsInstance(config_manager, ConfigManager)
        except Exception as e:
            self.fail(f"Failed to instantiate ConfigManager: {e}")

    def test_config_manager_singleton_pattern(self):
        """Test that ConfigManager follows singleton pattern."""
        config1 = ConfigManager()
        config2 = ConfigManager()
        self.assertIs(config1, config2, "ConfigManager should be a singleton")

    def test_config_has_basic_structure(self):
        """Test that loaded config has basic expected structure."""
        import yaml

        with open(self.config_path, encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        # Test basic sections exist
        expected_sections = ["application", "network", "vector_databases"]
        for section in expected_sections:
            self.assertIn(
                section,
                config_data,
                f"Basic section '{section}' missing from config file",
            )

    def test_application_section_in_file(self):
        """Test application section structure in file."""
        import yaml

        with open(self.config_path, encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        if "application" in config_data:
            app_config = config_data["application"]
            required_fields = ["name", "version"]
            for field in required_fields:
                self.assertIn(
                    field, app_config, f"Application section missing field: {field}"
                )

    def test_network_section_in_file(self):
        """Test network section structure in file."""
        import yaml

        with open(self.config_path, encoding="utf-8") as file:
            config_data = yaml.safe_load(file)

        if "network" in config_data:
            network_config = config_data["network"]
            self.assertIn("api", network_config, "Network section missing API config")
            if "api" in network_config:
                api_config = network_config["api"]
                self.assertIn("port", api_config, "API config missing port")
                self.assertIsInstance(
                    api_config["port"], int, "API port should be integer"
                )

    def test_config_manager_basic_methods(self):
        """Test basic ConfigManager methods work."""
        try:
            config_manager = ConfigManager()

            # Test get method doesn't crash
            result = config_manager.get("nonexistent.key", "default")
            self.assertEqual(result, "default")

            # Test other methods don't crash
            config_manager.get_network_config()
            config_manager.get_frontend_config()
            config_manager.get_client_config()
            config_manager.is_feature_enabled("test_feature")

        except Exception as e:
            self.fail(f"Basic ConfigManager methods failed: {e}")

    def test_safe_config_methods(self):
        """Test that safe configuration methods work."""
        try:
            config_manager = ConfigManager()

            # Test safe config methods
            safe_config = config_manager.get_safe_config()
            self.assertIsInstance(safe_config, dict)

            safe_frontend_config = config_manager.get_safe_frontend_config()
            self.assertIsInstance(safe_frontend_config, dict)

            # Test that safe config has expected structure
            expected_sections = [
                "application",
                "frontend",
                "client",
                "mcp_servers",
                "features",
            ]
            for section in expected_sections:
                if section in safe_frontend_config:
                    self.assertIsInstance(safe_frontend_config[section], (dict, list))

        except Exception as e:
            self.fail(f"Safe configuration methods failed: {e}")


if __name__ == "__main__":
    unittest.main()
