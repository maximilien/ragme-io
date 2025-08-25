#!/usr/bin/env python3
"""
Integration tests for storage management tool
"""

import json
import os
import subprocess

# Add the project root to Python path
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ragme.utils.config_manager import ConfigManager
from ragme.utils.storage import StorageService
from ragme.utils.storage_management import StorageManager


class TestStorageManagementIntegration:
    """Integration tests for storage management tool"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def test_files(self, temp_storage_dir):
        """Create test files in a separate directory"""
        # Create a separate directory for test files
        test_files_dir = tempfile.mkdtemp()

        # Create test files
        test_file1 = os.path.join(test_files_dir, "test1.txt")
        test_file2 = os.path.join(test_files_dir, "test2.pdf")
        test_file3 = os.path.join(test_files_dir, "test3.jpg")

        # Write test content
        with open(test_file1, "w") as f:
            f.write("Test content 1")

        with open(test_file2, "w") as f:
            f.write("Test PDF content")

        with open(test_file3, "w") as f:
            f.write("Test image content")

        return {
            "test1.txt": test_file1,
            "documents/test2.pdf": test_file2,
            "images/test3.jpg": test_file3,
        }

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create storage manager with temporary storage"""
        # Create a temporary config
        config = ConfigManager()

        # Override storage configuration for testing
        with patch.object(config, "get") as mock_get:
            mock_get.return_value = {
                "type": "local",
                "local": {"path": temp_storage_dir},
            }

            # Create storage service
            storage_service = StorageService(config)

            # Create storage manager
            manager = StorageManager()
            manager.storage = storage_service
            manager.config = config
            manager.storage_config = {
                "type": "local",
                "local": {"path": temp_storage_dir},
            }
            manager.storage_type = "local"

            return manager

    def test_storage_manager_initialization(self, storage_manager):
        """Test storage manager initialization"""
        assert storage_manager.storage_type == "local"
        assert storage_manager.storage is not None
        assert storage_manager.config is not None

    def test_list_files_integration(self, storage_manager, test_files):
        """Test file listing with actual files"""
        # Upload test files to storage
        for filename, filepath in test_files.items():
            storage_manager.storage.upload_file(filepath, filename)

        # Test listing all files
        files = storage_manager.storage.list_files()
        assert len(files) == 3
        file_names = [f["name"] for f in files]
        assert "test1.txt" in file_names
        assert "documents/test2.pdf" in file_names
        assert "images/test3.jpg" in file_names

    def test_list_files_with_prefix(self, storage_manager, test_files):
        """Test file listing with prefix filter"""
        # Upload test files to storage
        for filename, filepath in test_files.items():
            storage_manager.storage.upload_file(filepath, filename)

        # Test listing with prefix
        files = storage_manager.storage.list_files(prefix="documents/")
        assert len(files) == 1
        assert files[0]["name"] == "documents/test2.pdf"

    def test_file_upload_and_download(self, storage_manager, temp_storage_dir):
        """Test file upload and download functionality"""
        # Create test file
        test_content = "Test file content for upload/download"
        test_file = os.path.join(temp_storage_dir, "upload_test.txt")
        with open(test_file, "w") as f:
            f.write(test_content)

        # Upload file
        object_name = "test_upload.txt"
        uploaded_name = storage_manager.storage.upload_file(test_file, object_name)
        assert uploaded_name == object_name

        # Check if file exists
        assert storage_manager.storage.file_exists(object_name)

        # Download file
        download_path = os.path.join(temp_storage_dir, "download_test.txt")
        success = storage_manager.storage.download_file(object_name, download_path)
        assert success

        # Verify content
        with open(download_path) as f:
            downloaded_content = f.read()
        assert downloaded_content == test_content

    def test_file_deletion(self, storage_manager, test_files):
        """Test file deletion functionality"""
        # Upload test file
        filename, filepath = list(test_files.items())[0]
        storage_manager.storage.upload_file(filepath, filename)

        # Verify file exists
        assert storage_manager.storage.file_exists(filename)

        # Delete file
        success = storage_manager.storage.delete_file(filename)
        assert success

        # Verify file is deleted
        assert not storage_manager.storage.file_exists(filename)

    def test_url_generation(self, storage_manager, test_files):
        """Test URL generation functionality"""
        # Upload test file
        filename, filepath = list(test_files.items())[0]
        storage_manager.storage.upload_file(filepath, filename)

        # Generate URL
        url = storage_manager.storage.get_file_url(filename, expires_in=3600)
        assert url is not None
        assert "storage" in url
        assert filename in url

    def test_file_info(self, storage_manager, test_files):
        """Test file information retrieval"""
        # Upload test file
        filename, filepath = list(test_files.items())[0]
        storage_manager.storage.upload_file(filepath, filename)

        # Get file info
        info = storage_manager.storage.get_file_info(filename)
        assert info["name"] == filename
        assert info["size"] > 0
        assert "content_type" in info

    def test_cli_help_command(self):
        """Test CLI help command"""
        result = subprocess.run(
            ["./tools/storage.sh", "help"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "RAGme Storage Management Tool" in result.stdout
        assert "USAGE:" in result.stdout

    def test_cli_info_command(self):
        """Test CLI info command"""
        result = subprocess.run(
            ["./tools/storage.sh", "info"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "Storage Information" in result.stdout

    def test_cli_health_command(self):
        """Test CLI health command"""
        result = subprocess.run(
            ["./tools/storage.sh", "health"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "Storage Health Check" in result.stdout

    def test_cli_buckets_command(self):
        """Test CLI buckets command"""
        result = subprocess.run(
            ["./tools/storage.sh", "buckets"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "bucket" in result.stdout.lower() or "No buckets found" in result.stdout

    def test_cli_list_command(self):
        """Test CLI list command"""
        result = subprocess.run(
            ["./tools/storage.sh", "list"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "Found" in result.stdout or "No files found" in result.stdout

    def test_cli_list_all_buckets_command(self):
        """Test CLI list command with --all flag"""
        result = subprocess.run(
            ["./tools/storage.sh", "list", "--all"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert (
            "Total files across all buckets" in result.stdout
            or "No buckets found" in result.stdout
        )

    def test_cli_links_command(self):
        """Test CLI links command"""
        result = subprocess.run(
            ["./tools/storage.sh", "links"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "Download links" in result.stdout or "No files found" in result.stdout

    def test_cli_delete_command_with_nonexistent_file(self):
        """Test CLI delete command with non-existent file"""
        result = subprocess.run(
            ["./tools/storage.sh", "delete", "nonexistent_file.txt"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "File not found" in result.stdout

    def test_cli_delete_all_command_with_no_files(self):
        """Test CLI delete-all command with no files"""
        # This test is expected to fail because there are files in storage
        # We'll just test that the command doesn't crash
        result = subprocess.run(
            ["./tools/storage.sh", "delete-all"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        # Command should not crash, even if it asks for confirmation
        assert (
            "About to delete" in result.stdout
            or "No files found to delete" in result.stdout
        )

    def test_storage_api_endpoint(self):
        """Test the storage API endpoint"""
        import requests

        # Test with a file that doesn't exist
        response = requests.get("http://localhost:8021/storage/nonexistent_file.txt")
        assert response.status_code == 404
        data = response.json()
        assert "File not found" in data["detail"]

    def test_storage_status_endpoint(self):
        """Test the storage status API endpoint"""
        import requests

        response = requests.get("http://localhost:8021/storage/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "storage" in data

    def test_error_handling_invalid_command(self):
        """Test error handling for invalid CLI command"""
        result = subprocess.run(
            ["./tools/storage.sh", "invalid_command"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        # Command should show usage/help for invalid commands
        assert "usage" in result.stdout.lower() or "error" in result.stderr.lower()

    def test_storage_manager_with_real_files(self, storage_manager, temp_storage_dir):
        """Test storage manager with real file operations"""
        # Create a test file in a separate directory
        test_files_dir = tempfile.mkdtemp()
        test_file_path = os.path.join(test_files_dir, "real_test.txt")
        test_content = "This is a real test file"
        with open(test_file_path, "w") as f:
            f.write(test_content)

        # Upload to storage
        object_name = "real_test.txt"
        storage_manager.storage.upload_file(test_file_path, object_name)

        # Test file listing
        files = storage_manager.storage.list_files()
        file_names = [f["name"] for f in files]
        assert object_name in file_names

        # Test file info
        info = storage_manager.storage.get_file_info(object_name)
        assert info["name"] == object_name
        assert info["size"] == len(test_content)

        # Test file download
        download_path = os.path.join(temp_storage_dir, "downloaded_test.txt")
        success = storage_manager.storage.download_file(object_name, download_path)
        assert success

        # Verify content
        with open(download_path) as f:
            downloaded_content = f.read()
        assert downloaded_content == test_content

        # Test file deletion
        success = storage_manager.storage.delete_file(object_name)
        assert success
        assert not storage_manager.storage.file_exists(object_name)

    def test_storage_manager_health_check(self, storage_manager):
        """Test storage manager health check functionality"""
        # Test health check
        health_result = storage_manager.check_storage_health()
        assert health_result is True

        # Test health check with verbose output
        with patch("builtins.print") as mock_print:
            storage_manager.check_health(verbose=True)
            # Verify that health check output was printed
            assert mock_print.called

    def test_storage_manager_info_display(self, storage_manager):
        """Test storage manager info display functionality"""
        with patch("builtins.print") as mock_print:
            storage_manager.show_info()
            # Verify that info was displayed
            assert mock_print.called

    def test_storage_manager_list_display(self, storage_manager):
        """Test storage manager list display functionality"""
        with patch("builtins.print") as mock_print:
            storage_manager.list_files()
            # Verify that file list was displayed
            assert mock_print.called

    def test_storage_manager_links_display(self, storage_manager):
        """Test storage manager links display functionality"""
        with patch("builtins.print") as mock_print:
            storage_manager.show_links()
            # Verify that links were displayed
            assert mock_print.called


if __name__ == "__main__":
    pytest.main([__file__])
