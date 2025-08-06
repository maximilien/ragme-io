# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import unittest
from unittest.mock import patch

from src.ragme.utils.config_manager import ConfigManager


class TestConfigSecurity(unittest.TestCase):
    """Test configuration security to ensure no secrets are leaked."""

    def setUp(self):
        """Set up test configuration manager."""
        self.config = ConfigManager()

    def test_safe_config_filters_api_keys(self):
        """Test that safe configuration filters out API keys."""
        safe_config = self.config.get_safe_config()
        config_str = json.dumps(safe_config)

        # Check that no sensitive patterns are in the safe config
        # Note: We check for exact sensitive field names, not just words like "api"
        sensitive_patterns = [
            "api_key",
            "apikey",
            "auth_token",
            "access_token",
            "private_key",
            "client_secret",
            "webhook_secret",
            "bearer_token",
        ]

        # Additional patterns that should not appear as field names or values
        sensitive_values = ["sk-", "bearer ", "token:", "key:", "secret:", "password:"]

        for pattern in sensitive_patterns:
            self.assertNotIn(
                pattern,
                config_str.lower(),
                f"Sensitive pattern '{pattern}' found in safe configuration",
            )

        for pattern in sensitive_values:
            self.assertNotIn(
                pattern,
                config_str.lower(),
                f"Sensitive value pattern '{pattern}' found in safe configuration",
            )

    def test_safe_frontend_config_excludes_vector_db_secrets(self):
        """Test that frontend config excludes vector database secrets."""
        safe_config = self.config.get_safe_frontend_config()

        # Ensure vector database configurations are not included
        self.assertNotIn(
            "vector_databases",
            safe_config,
            "Vector database configurations should not be in frontend config",
        )

    def test_safe_frontend_config_excludes_environment_section(self):
        """Test that environment section is excluded from frontend config."""
        safe_config = self.config.get_safe_frontend_config()

        # Ensure environment section is not included
        self.assertNotIn(
            "environment",
            safe_config,
            "Environment section should not be in frontend config",
        )

    def test_mcp_servers_filtered_safely(self):
        """Test that MCP servers are filtered to remove sensitive data."""
        safe_config = self.config.get_safe_frontend_config()
        mcp_servers = safe_config.get("mcp_servers", [])

        for server in mcp_servers:
            # Check that sensitive fields are not present
            self.assertNotIn(
                "api_key", server, f"API key found in MCP server: {server.get('name')}"
            )
            self.assertNotIn(
                "token", server, f"Token found in MCP server: {server.get('name')}"
            )
            self.assertNotIn(
                "authentication_type",
                server,
                f"Authentication type found in MCP server: {server.get('name')}",
            )

            # Check that only safe fields are present
            allowed_fields = {"name", "icon", "enabled", "description", "url"}
            for field in server.keys():
                self.assertIn(
                    field,
                    allowed_fields,
                    f"Unexpected field '{field}' in MCP server config",
                )

    def test_environment_variables_not_exposed(self):
        """Test that environment variable placeholders are filtered."""
        safe_config = self.config.get_safe_config()
        config_str = json.dumps(safe_config)

        # Check that environment variable patterns are replaced
        self.assertNotIn(
            "${", config_str, "Environment variable placeholders found in safe config"
        )

    def test_localhost_urls_allowed_external_filtered(self):
        """Test that only localhost URLs are allowed, external URLs filtered."""
        safe_config = self.config.get_safe_frontend_config()
        mcp_servers = safe_config.get("mcp_servers", [])

        for server in mcp_servers:
            if "url" in server:
                url = server["url"]
                self.assertTrue(
                    "localhost" in url or "127.0.0.1" in url,
                    f"Non-localhost URL found in MCP server: {url}",
                )

    def test_safe_config_contains_required_fields(self):
        """Test that safe config still contains required fields for frontend."""
        safe_config = self.config.get_safe_frontend_config()

        # Check that required sections are present
        required_sections = [
            "application",
            "frontend",
            "client",
            "mcp_servers",
            "features",
        ]
        for section in required_sections:
            self.assertIn(
                section,
                safe_config,
                f"Required section '{section}' missing from safe config",
            )

    def test_handles_malicious_config_data(self):
        """Test that malicious configuration data is properly filtered."""
        # Create a mock configuration manager with sensitive data
        config_manager = ConfigManager()

        # Mock the _config attribute directly
        config_manager._config = {
            "application": {"name": "Test"},
            "vector_databases": {
                "databases": [
                    {
                        "name": "malicious",
                        "api_key": "sk-malicious-key-12345",
                        "password": "secret123",
                        "token": "bearer-token-xyz",
                    }
                ]
            },
            "mcp_servers": [
                {
                    "name": "malicious-server",
                    "api_key": "malicious-api-key",
                    "secret_token": "secret-token-123",
                }
            ],
            "environment": {"required": ["MALICIOUS_SECRET"]},
        }

        safe_config = config_manager.get_safe_frontend_config()
        config_str = json.dumps(safe_config)

        # Ensure no sensitive data is leaked
        sensitive_data = [
            "sk-malicious-key-12345",
            "secret123",
            "bearer-token-xyz",
            "malicious-api-key",
            "secret-token-123",
            "MALICIOUS_SECRET",
        ]

        for sensitive_item in sensitive_data:
            self.assertNotIn(
                sensitive_item,
                config_str,
                f"Sensitive data '{sensitive_item}' found in safe config",
            )


if __name__ == "__main__":
    unittest.main()
