# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Configuration Manager for Integration Tests

This module handles backing up the original config.yaml, modifying it for tests,
and restoring it after tests complete to avoid polluting the developer's main collection.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import yaml


class TestConfigManager:
    """Manages configuration for integration tests to avoid polluting main collections."""

    def __init__(self, test_collection_name: str = "test_integration"):
        """
        Initialize the test configuration manager.

        Args:
            test_collection_name: Name of the test collection to use
        """
        self.test_collection_name = test_collection_name
        self.original_config_path = Path("config.yaml")
        self.backup_config_path = Path("config.yaml.test_backup")
        self.temp_config_path = Path("config.yaml.test_temp")
        self.env_file_path = Path(".env")
        self.env_backup_path = Path(".env.integration_backup")
        self.original_config = None
        self.modified_config = None
        self.env_modified = False

    def backup_config(self) -> bool:
        """
        Backup the original config.yaml file.

        Returns:
            True if backup was successful, False otherwise
        """
        try:
            if not self.original_config_path.exists():
                print(f"Warning: {self.original_config_path} does not exist")
                return False

            # Create backup
            shutil.copy2(self.original_config_path, self.backup_config_path)
            print(f"✅ Backed up config.yaml to {self.backup_config_path}")

            # Read original config
            with open(self.original_config_path, encoding="utf-8") as f:
                self.original_config = yaml.safe_load(f)

            return True

        except Exception as e:
            print(f"❌ Failed to backup config.yaml: {e}")
            return False

    def backup_and_modify_env_file(self) -> bool:
        """
        Backup and modify .env file to use test collection name.

        Returns:
            True if modification was successful, False otherwise
        """
        try:
            if not self.env_file_path.exists():
                print(f"Warning: {self.env_file_path} does not exist")
                return True  # Not an error if .env doesn't exist

            # Backup original .env
            shutil.copy2(self.env_file_path, self.env_backup_path)

            # Read and modify .env content
            with open(self.env_file_path) as f:
                env_content = f.read()

            # Replace VECTOR_DB_COLLECTION_NAME value
            # Prefer new env vars for collections; also set legacy for compatibility
            if re.search(r"^VECTOR_DB_TEXT_COLLECTION_NAME=", env_content, re.M):
                env_content = re.sub(
                    r"(VECTOR_DB_TEXT_COLLECTION_NAME=).*",
                    f"\\1{self.test_collection_name}",
                    env_content,
                )
            else:
                env_content += (
                    f"\nVECTOR_DB_TEXT_COLLECTION_NAME={self.test_collection_name}\n"
                )

            # Remove legacy collection name if present (migrating to new vars)
            env_content = re.sub(
                r"^VECTOR_DB_COLLECTION_NAME=.*\n?",
                "",
                env_content,
                flags=re.M,
            )

            # Write modified content back
            with open(self.env_file_path, "w") as f:
                f.write(env_content)

            self.env_modified = True
            print("🔧 Temporarily modified .env file with test collection name")
            return True

        except Exception as e:
            print(f"❌ Error modifying .env file: {e}")
            return False

    def modify_config_for_tests(self) -> bool:
        """
        Modify the config to use the test collection.

        Returns:
            True if modification was successful, False otherwise
        """
        try:
            if self.original_config is None:
                print("❌ No original config loaded. Call backup_config() first.")
                return False

            # Create a deep copy of the original config
            self.modified_config = yaml.safe_load(yaml.dump(self.original_config))

            # Modify all database configurations to use test collection
            if "vector_databases" in self.modified_config:
                databases = self.modified_config["vector_databases"].get(
                    "databases", []
                )
                for db_config in databases:
                    # Legacy key support
                    if "collection_name" in db_config:
                        print(
                            f"🔄 Modifying collection '{db_config['collection_name']}' to '{self.test_collection_name}'"
                        )
                        db_config["collection_name"] = self.test_collection_name

                    # New collections structure
                    collections = db_config.get("collections")
                    if isinstance(collections, list) and collections:
                        # Replace text collection name
                        updated = False
                        for col in collections:
                            if isinstance(col, dict) and col.get("type") == "text":
                                original = col.get("name", "")
                                col["name"] = self.test_collection_name
                                print(
                                    f"🔄 Modifying text collection '{original}' to '{self.test_collection_name}'"
                                )
                                updated = True
                                break
                        if not updated:
                            # If no text collection present, add one
                            collections.append(
                                {"name": self.test_collection_name, "type": "text"}
                            )
                            print(
                                f"➕ Added text collection '{self.test_collection_name}' to database config"
                            )

            # Enable bypass_delete_confirmation for tests
            if "features" in self.modified_config:
                if "bypass_delete_confirmation" not in self.modified_config["features"]:
                    self.modified_config["features"]["bypass_delete_confirmation"] = (
                        True
                    )
                else:
                    self.modified_config["features"]["bypass_delete_confirmation"] = (
                        True
                    )
                print("🔄 Enabling bypass_delete_confirmation for tests")

            # Write modified config to temporary file
            with open(self.temp_config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.modified_config, f, default_flow_style=False, sort_keys=False
                )

            # Replace original config with modified version
            shutil.copy2(self.temp_config_path, self.original_config_path)
            print(
                f"✅ Modified config.yaml to use test collection '{self.test_collection_name}'"
            )

            return True

        except Exception as e:
            print(f"❌ Failed to modify config for tests: {e}")
            return False

    def restore_config(self) -> bool:
        """
        Restore the original config.yaml from backup.

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            if not self.backup_config_path.exists():
                print(f"Warning: Backup file {self.backup_config_path} does not exist")
                return False

            # Restore original config
            shutil.copy2(self.backup_config_path, self.original_config_path)
            print("✅ Restored config.yaml from backup")

            # Clean up backup and temp files
            self.cleanup()

            return True

        except Exception as e:
            print(f"❌ Failed to restore config.yaml: {e}")
            return False

    def restore_env_file(self) -> bool:
        """
        Restore the original .env file from backup.

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            if not self.env_modified:
                return True  # Nothing to restore

            if self.env_backup_path.exists():
                shutil.copy2(self.env_backup_path, self.env_file_path)
                self.env_backup_path.unlink()
                print("🔧 Restored original .env file")
                self.env_modified = False
                return True
            else:
                print(f"Warning: .env backup file {self.env_backup_path} not found")
                # Still mark as restored to avoid repeated warnings
                self.env_modified = False
                return True  # Return True to not fail the cleanup

        except Exception as e:
            print(f"❌ Error restoring .env file: {e}")
            return False

    def cleanup(self):
        """Clean up temporary and backup files."""
        try:
            # Remove backup file
            if self.backup_config_path.exists():
                self.backup_config_path.unlink()
                print(f"🗑️ Removed backup file {self.backup_config_path}")

            # Remove temp file
            if self.temp_config_path.exists():
                self.temp_config_path.unlink()
                print(f"🗑️ Removed temp file {self.temp_config_path}")

            # Remove .env backup file
            if self.env_backup_path.exists():
                self.env_backup_path.unlink()
                print(f"🗑️ Removed .env backup file {self.env_backup_path}")

        except Exception as e:
            print(f"Warning: Failed to cleanup temporary files: {e}")

    def setup_for_tests(self) -> bool:
        """
        Complete setup for tests: backup and modify config.

        Returns:
            True if setup was successful, False otherwise
        """
        print("🔧 Setting up configuration for integration tests...")

        if not self.backup_config():
            return False

        if not self.modify_config_for_tests():
            # Try to restore if modification failed
            self.restore_config()
            return False

        if not self.backup_and_modify_env_file():
            # Try to restore if .env modification failed
            self.restore_config()
            return False

        print("✅ Configuration setup completed successfully")
        return True

    def teardown_after_tests(self) -> bool:
        """
        Complete teardown after tests: restore config and cleanup.

        Returns:
            True if teardown was successful, False otherwise
        """
        print("🧹 Cleaning up configuration after integration tests...")

        success = self.restore_config()
        env_success = self.restore_env_file()

        if success and env_success:
            print("✅ Configuration cleanup completed successfully")
        else:
            print("❌ Configuration cleanup failed")

        return success and env_success

    def get_test_collection_name(self) -> str:
        """Get the test collection name."""
        return self.test_collection_name

    def is_test_config_active(self) -> bool:
        """
        Check if the test configuration is currently active.

        Returns:
            True if test config is active, False otherwise
        """
        try:
            if not self.original_config_path.exists():
                return False

            with open(self.original_config_path, encoding="utf-8") as f:
                current_config = yaml.safe_load(f)

            # Check if any database is using the test collection name
            if "vector_databases" in current_config:
                databases = current_config["vector_databases"].get("databases", [])
                for db_config in databases:
                    # Legacy structure
                    if db_config.get("collection_name") == self.test_collection_name:
                        return True
                    # New structure
                    collections = db_config.get("collections", [])
                    for col in collections:
                        if (
                            isinstance(col, dict)
                            and col.get("type") == "text"
                            and col.get("name") == self.test_collection_name
                        ):
                            return True

            return False

        except Exception:
            return False


# Global instance for easy access
test_config_manager = TestConfigManager()


def setup_test_config() -> bool:
    """Setup test configuration (global function for easy access)."""
    return test_config_manager.setup_for_tests()


def teardown_test_config() -> bool:
    """Teardown test configuration (global function for easy access)."""
    return test_config_manager.teardown_after_tests()


def get_test_collection_name() -> str:
    """Get test collection name (global function for easy access)."""
    return test_config_manager.get_test_collection_name()


if __name__ == "__main__":
    # Test the configuration manager
    print("Testing Configuration Manager...")

    # Setup
    if setup_test_config():
        print("✅ Setup successful")

        # Check if test config is active
        if test_config_manager.is_test_config_active():
            print("✅ Test configuration is active")
        else:
            print("❌ Test configuration is not active")

        # Teardown
        if teardown_test_config():
            print("✅ Teardown successful")
        else:
            print("❌ Teardown failed")
    else:
        print("❌ Setup failed")
