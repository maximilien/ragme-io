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

    def __init__(
        self,
        test_collection_name: str = "test_integration",
        test_image_collection_name: str = "test_integration_images",
    ):
        """
        Initialize the test configuration manager.

        Args:
            test_collection_name: Name of the test text collection to use
            test_image_collection_name: Name of the test image collection to use
        """
        self.test_collection_name = test_collection_name
        self.test_image_collection_name = test_image_collection_name
        self.original_config_path = Path("config.yaml")
        self.backup_config_path = Path("config.yaml.test_backup")
        self.temp_config_path = Path("config.yaml.test_temp")
        self.env_file_path = Path(".env")
        self.env_backup_path = Path(".env.integration_backup")
        self.original_config = None
        self.modified_config = None
        self.env_modified = False

    def _find_latest_backup(self, pattern: str) -> Path | None:
        """
        Find the latest backup file matching the pattern.

        Args:
            pattern: Glob pattern to match backup files

        Returns:
            Path to the latest backup file, or None if not found
        """
        try:
            backup_files = list(Path(".").glob(pattern))
            if backup_files:
                # Return the most recent backup file
                latest = max(backup_files, key=lambda x: x.stat().st_mtime)
                print(f"  🔍 Found backup file: {latest}")
                return latest
            else:
                print(f"  🔍 No backup files found matching pattern: {pattern}")
                return None
        except Exception as e:
            print(f"  ⚠️ Error finding backup files: {e}")
            return None

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

    def cleanup_test_collections(self) -> bool:
        """
        Clean up test collections before running tests.

        This ensures the test collections are empty when tests start.

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            print("🧹 Cleaning up test collections before tests...")

            # Import here to avoid circular imports
            import sys
            from pathlib import Path

            # Add src to path for imports
            src_path = Path(__file__).parent.parent.parent / "src"
            sys.path.insert(0, str(src_path))

            from ragme.utils.config_manager import config
            from ragme.vdbs.vdb_management import VDBManager

            # Force reload the config to ensure we have the test collection names
            try:
                config.reload()
                print("  🔄 Reloaded config to ensure test collection names are used")
            except Exception as e:
                print(f"  ⚠️ Warning: Could not reload config: {e}")

            # Ensure environment variables are set before creating VDBManager
            import os

            os.environ["VECTOR_DB_TEXT_COLLECTION_NAME"] = self.test_collection_name
            os.environ["VECTOR_DB_IMAGE_COLLECTION_NAME"] = (
                self.test_image_collection_name
            )
            print("  🔧 Set environment variables for test collections")
            print(
                f"  🔧 VECTOR_DB_TEXT_COLLECTION_NAME={os.environ.get('VECTOR_DB_TEXT_COLLECTION_NAME')}"
            )
            print(
                f"  🔧 VECTOR_DB_IMAGE_COLLECTION_NAME={os.environ.get('VECTOR_DB_IMAGE_COLLECTION_NAME')}"
            )

            # Create VDB manager with test configuration
            manager = VDBManager()

            # Force reload configuration to ensure test collection names are used
            manager.reload_config()

            # Verify we're using the correct collection names
            config_info = manager.show_config()
            print(f"  📋 Using text collection: {config_info['text_collection']}")
            print(f"  📋 Using image collection: {config_info['image_collection']}")

            # Safety check: ensure we're not cleaning up main collections
            if (
                config_info["text_collection"] != self.test_collection_name
                or config_info["image_collection"] != self.test_image_collection_name
            ):
                print("  ⚠️ Warning: VDBManager is not using test collections!")
                print(
                    f"     Expected: {self.test_collection_name}, {self.test_image_collection_name}"
                )
                print(
                    f"     Actual: {config_info['text_collection']}, {config_info['image_collection']}"
                )
                print("  🛑 Skipping cleanup to avoid affecting main collections")
                manager.cleanup()
                return True

            # Clean up text collection
            print(f"  🧹 Cleaning up text collection: {self.test_collection_name}")
            text_result = manager.delete_text_collection_content()
            if text_result["status"] == "success":
                print(f"    ✅ {text_result['message']}")
            else:
                print(
                    f"    ⚠️ Text collection cleanup: {text_result.get('error', 'Unknown error')}"
                )

            # Clean up image collection
            print(
                f"  🧹 Cleaning up image collection: {self.test_image_collection_name}"
            )
            image_result = manager.delete_image_collection_content()
            if image_result["status"] == "success":
                print(f"    ✅ {image_result['message']}")
            else:
                print(
                    f"    ⚠️ Image collection cleanup: {image_result.get('error', 'Unknown error')}"
                )

            # Clean up VDB resources
            manager.cleanup()

            print("✅ Test collections cleaned up successfully")
            return True

        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup test collections: {e}")
            import traceback

            traceback.print_exc()
            # Don't fail the test setup if cleanup fails
            return True

    def backup_and_modify_env_file(self) -> bool:
        """
        Backup and modify .env file to use test collection name.

        Returns:
            True if modification was successful, False otherwise
        """
        try:
            if not self.env_file_path.exists():
                print(
                    "⚠️ .env file does not exist, creating one with test collection name"
                )
                # Create a new .env file with the test collection name
                env_content = (
                    f"VECTOR_DB_TEXT_COLLECTION_NAME={self.test_collection_name}\n"
                )
                with open(self.env_file_path, "w") as f:
                    f.write(env_content)
                self.env_modified = True
                print("🔧 Created .env file with test collection name")
                return True

            # Backup original .env
            shutil.copy2(self.env_file_path, self.env_backup_path)

            # Read and modify .env content
            with open(self.env_file_path) as f:
                env_content = f.read()

            # Replace VECTOR_DB_TEXT_COLLECTION_NAME value
            # Prefer new env vars for collections; also set legacy for compatibility
            if re.search(r"^VECTOR_DB_TEXT_COLLECTION_NAME=", env_content, re.M):
                env_content = re.sub(
                    r"(VECTOR_DB_TEXT_COLLECTION_NAME=).*",
                    f"\\1{self.test_collection_name}",
                    env_content,
                )
                print(
                    f"🔧 Updated existing VECTOR_DB_TEXT_COLLECTION_NAME to {self.test_collection_name}"
                )
            else:
                env_content += (
                    f"\nVECTOR_DB_TEXT_COLLECTION_NAME={self.test_collection_name}\n"
                )
                print(
                    f"🔧 Added VECTOR_DB_TEXT_COLLECTION_NAME={self.test_collection_name} to .env file"
                )

            # Replace VECTOR_DB_IMAGE_COLLECTION_NAME value
            if re.search(r"^VECTOR_DB_IMAGE_COLLECTION_NAME=", env_content, re.M):
                env_content = re.sub(
                    r"(VECTOR_DB_IMAGE_COLLECTION_NAME=).*",
                    f"\\1{self.test_image_collection_name}",
                    env_content,
                )
                print(
                    f"🔧 Updated existing VECTOR_DB_IMAGE_COLLECTION_NAME to {self.test_image_collection_name}"
                )
            else:
                env_content += f"\nVECTOR_DB_IMAGE_COLLECTION_NAME={self.test_image_collection_name}\n"
                print(
                    f"🔧 Added VECTOR_DB_IMAGE_COLLECTION_NAME={self.test_image_collection_name} to .env file"
                )

            # Remove legacy collection name if present (migrating to new vars)
            if re.search(r"^VECTOR_DB_COLLECTION_NAME=", env_content, re.M):
                env_content = re.sub(
                    r"^VECTOR_DB_COLLECTION_NAME=.*\n?",
                    "",
                    env_content,
                    flags=re.M,
                )
                print("🔧 Removed legacy VECTOR_DB_COLLECTION_NAME from .env file")

            # Write modified content back
            with open(self.env_file_path, "w") as f:
                f.write(env_content)

            self.env_modified = True
            print("🔧 Temporarily modified .env file with test collection name")
            return True

        except Exception as e:
            print(f"❌ Error modifying .env file: {e}")
            import traceback

            traceback.print_exc()
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
                        text_updated = False
                        image_updated = False
                        for col in collections:
                            if isinstance(col, dict) and col.get("type") == "text":
                                original = col.get("name", "")
                                col["name"] = self.test_collection_name
                                print(
                                    f"🔄 Modifying text collection '{original}' to '{self.test_collection_name}'"
                                )
                                text_updated = True
                            elif isinstance(col, dict) and col.get("type") == "image":
                                original = col.get("name", "")
                                col["name"] = self.test_image_collection_name
                                print(
                                    f"🔄 Modifying image collection '{original}' to '{self.test_image_collection_name}'"
                                )
                                image_updated = True

                        # Add missing collections if not present
                        if not text_updated:
                            collections.append(
                                {"name": self.test_collection_name, "type": "text"}
                            )
                            print(
                                f"➕ Added text collection '{self.test_collection_name}' to database config"
                            )
                        if not image_updated:
                            collections.append(
                                {
                                    "name": self.test_image_collection_name,
                                    "type": "image",
                                }
                            )
                            print(
                                f"➕ Added image collection '{self.test_image_collection_name}' to database config"
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
                f"✅ Modified config.yaml to use test collections '{self.test_collection_name}' and '{self.test_image_collection_name}'"
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
            print("  🔄 Attempting to restore config.yaml...")

            # First try to find the exact backup files created by test-with-backup.sh
            # These are created with timestamped names like config.yaml.backup_20250831_104752
            timestamped_backup = self._find_latest_backup("config.yaml.backup_*")
            if timestamped_backup:
                print(f"  📁 Found timestamped backup file: {timestamped_backup}")
                shutil.copy2(timestamped_backup, self.original_config_path)
                print("  ✅ Restored config.yaml from timestamped backup")
                # Don't delete the backup file - let test-with-backup.sh handle cleanup
                return True

            # Fall back to the config manager's own backup
            if self.backup_config_path.exists():
                print(f"  📁 Found config manager backup: {self.backup_config_path}")
                shutil.copy2(self.backup_config_path, self.original_config_path)
                print("  ✅ Restored config.yaml from config manager backup")
                return True

            print("  ⚠️ No backup files found, cannot restore config.yaml")
            # List what files are actually present for debugging
            config_backups = list(Path(".").glob("config.yaml*"))
            if config_backups:
                print(
                    f"  📋 Available config files: {[f.name for f in config_backups]}"
                )
            return False

        except Exception as e:
            print(f"  ❌ Failed to restore config.yaml: {e}")
            return False

    def restore_env_file(self) -> bool:
        """
        Restore the original .env file from backup.

        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            if not self.env_modified:
                print("🔧 .env file was not modified, nothing to restore")
                return True  # Nothing to restore

            # First try to find the exact backup files created by test-with-backup.sh
            # These are created with timestamped names like .env.backup_20250831_104752
            timestamped_backup = self._find_latest_backup(".env.backup_*")
            if timestamped_backup:
                print(f"  📁 Found timestamped .env backup file: {timestamped_backup}")
                shutil.copy2(timestamped_backup, self.env_file_path)
                print("  ✅ Restored original .env file from timestamped backup")
                # Don't delete the backup file - let test-with-backup.sh handle cleanup
                self.env_modified = False
                return True

            # Fall back to the config manager's own backup
            if self.env_backup_path.exists():
                # Restore from backup
                shutil.copy2(self.env_backup_path, self.env_file_path)
                self.env_backup_path.unlink()
                print("🔧 Restored original .env file from config manager backup")
                self.env_modified = False
                return True

            print("⚠️ No .env backup files found")
            return False

        except Exception as e:
            print(f"❌ Failed to restore .env file: {e}")
            return False

    def cleanup(self):
        """Clean up temporary and backup files."""
        try:
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

    def cleanup_backup(self):
        """Clean up backup files after successful restoration."""
        try:
            # Remove backup file only after successful restoration
            if self.backup_config_path.exists():
                self.backup_config_path.unlink()
                print(f"🗑️ Removed backup file {self.backup_config_path}")
        except Exception as e:
            print(f"Warning: Failed to cleanup backup file: {e}")

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

        # Clean up test collections after config is set up
        if not self.cleanup_test_collections():
            # Try to restore if cleanup failed
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

        # Clean up test collections BEFORE restoring config
        # This ensures we're cleaning up the test collections, not the main ones
        self.cleanup_test_collections_after_tests()

        # Always try to restore both config and .env file
        config_success = self.restore_config()
        env_success = self.restore_env_file()

        # Clean up backup files only after successful restoration
        if config_success:
            self.cleanup_backup()

        if config_success and env_success:
            print("✅ Configuration cleanup completed successfully")
            return True
        else:
            print("❌ Configuration cleanup had issues:")
            if not config_success:
                print("  - Failed to restore config.yaml")
            if not env_success:
                print("  - Failed to restore .env file")
            print("⚠️ Please check your configuration files manually")
            return False

    def cleanup_test_collections_after_tests(self) -> bool:
        """
        Clean up test collections after tests complete.

        This ensures the test collections are cleaned up even if tests fail.

        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            print("🧹 Cleaning up test collections after tests...")

            # Import here to avoid circular imports
            import sys
            from pathlib import Path

            # Add src to path for imports
            src_path = Path(__file__).parent.parent.parent / "src"
            sys.path.insert(0, str(src_path))

            from ragme.utils.config_manager import config
            from ragme.vdbs.vdb_management import VDBManager

            # Force reload the config to ensure we have the test collection names
            try:
                config.reload()
                print("  🔄 Reloaded config to ensure test collection names are used")
            except Exception as e:
                print(f"  ⚠️ Warning: Could not reload config: {e}")

            # Create VDB manager with test configuration
            manager = VDBManager()

            # Verify we're using the correct collection names
            config_info = manager.show_config()
            print(f"  📋 Using text collection: {config_info['text_collection']}")
            print(f"  📋 Using image collection: {config_info['image_collection']}")

            # Only proceed if we're using test collections
            if (
                config_info["text_collection"] != self.test_collection_name
                or config_info["image_collection"] != self.test_image_collection_name
            ):
                print("  ⚠️ Warning: VDBManager is not using test collections!")
                print(
                    f"     Expected: {self.test_collection_name}, {self.test_image_collection_name}"
                )
                print(
                    f"     Actual: {config_info['text_collection']}, {config_info['image_collection']}"
                )
                print("  🛑 Skipping cleanup to avoid affecting main collections")
                return True

            # Clean up text collection
            print(f"  🧹 Cleaning up text collection: {self.test_collection_name}")
            text_result = manager.delete_text_collection_content()
            if text_result["status"] == "success":
                print(f"    ✅ {text_result['message']}")
            else:
                print(
                    f"    ⚠️ Text collection cleanup: {text_result.get('error', 'Unknown error')}"
                )

            # Clean up image collection
            print(
                f"  🧹 Cleaning up image collection: {self.test_image_collection_name}"
            )
            image_result = manager.delete_image_collection_content()
            if image_result["status"] == "success":
                print(f"    ✅ {image_result['message']}")
            else:
                print(
                    f"    ⚠️ Image collection cleanup: {image_result.get('error', 'Unknown error')}"
                )

            # Clean up VDB resources
            manager.cleanup()

            print("✅ Test collections cleaned up after tests")
            return True

        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup test collections after tests: {e}")
            # Don't fail the teardown if cleanup fails
            return True

    def get_test_collection_name(self) -> str:
        """Get the test text collection name."""
        return self.test_collection_name

    def get_test_image_collection_name(self) -> str:
        """Get the test image collection name."""
        return self.test_image_collection_name

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

            # Check if any database is using the test collection names
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
                        if (
                            isinstance(col, dict)
                            and col.get("type") == "image"
                            and col.get("name") == self.test_image_collection_name
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
    """Get test text collection name (global function for easy access)."""
    return test_config_manager.get_test_collection_name()


def get_test_image_collection_name() -> str:
    """Get test image collection name (global function for easy access)."""
    return test_config_manager.get_test_image_collection_name()


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
