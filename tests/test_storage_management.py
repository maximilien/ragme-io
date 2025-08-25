#!/usr/bin/env python3
"""
Unit tests for storage management tool
"""

import os

# Add the project root to Python path
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ragme.utils.storage_management import StorageManager


class TestStorageManager:
    """Test cases for StorageManager class"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        config = Mock()
        config.get.return_value = {
            "type": "local",
            "local": {"path": "/tmp/test_storage"},
        }
        return config

    @pytest.fixture
    def mock_storage_service(self):
        """Mock storage service"""
        storage = Mock()

        # Mock file listing
        storage.list_files.return_value = [
            {
                "name": "test1.pdf",
                "size": 1024,
                "last_modified": datetime(2023, 1, 1, 12, 0, 0),
                "etag": "abc123",
            },
            {
                "name": "test2.jpg",
                "size": 2048,
                "last_modified": datetime(2023, 1, 2, 12, 0, 0),
                "etag": "def456",
            },
        ]

        # Mock bucket listing
        storage.list_buckets.return_value = [
            {
                "name": "bucket1",
                "creation_date": datetime(2023, 1, 1, 10, 0, 0),
                "size": 1024,
            },
            {
                "name": "bucket2",
                "creation_date": datetime(2023, 1, 2, 10, 0, 0),
                "size": 2048,
            },
        ]

        # Mock file existence
        storage.file_exists.return_value = True

        # Mock bucket existence
        storage.bucket_exists.return_value = True

        # Mock file info
        storage.get_file_info.return_value = {
            "name": "test1.pdf",
            "size": 1024,
            "last_modified": datetime(2023, 1, 1, 12, 0, 0),
            "etag": "abc123",
            "content_type": "application/pdf",
        }

        # Mock URL generation
        storage.get_file_url.return_value = "http://localhost:8021/storage/test1.pdf"

        # Mock bucket-specific file operations
        storage.list_files_in_bucket.return_value = [
            {
                "name": "bucket1_file1.pdf",
                "size": 512,
                "last_modified": datetime(2023, 1, 1, 11, 0, 0),
                "etag": "xyz789",
            }
        ]

        storage.delete_file_from_bucket.return_value = True

        return storage

    @pytest.fixture
    def storage_manager(self, mock_config, mock_storage_service):
        """Create StorageManager instance with mocked dependencies"""
        with (
            patch(
                "ragme.utils.storage_management.ConfigManager", return_value=mock_config
            ),
            patch(
                "ragme.utils.storage_management.StorageService",
                return_value=mock_storage_service,
            ),
        ):
            manager = StorageManager()
            manager.storage = mock_storage_service
            manager.config = mock_config
            return manager

    def test_init_success(self, mock_config, mock_storage_service):
        """Test successful initialization"""
        with (
            patch(
                "ragme.utils.storage_management.ConfigManager", return_value=mock_config
            ),
            patch(
                "ragme.utils.storage_management.StorageService",
                return_value=mock_storage_service,
            ),
        ):
            manager = StorageManager()
            assert manager.storage_type == "local"
            assert manager.storage_config == {
                "type": "local",
                "local": {"path": "/tmp/test_storage"},
            }

    def test_init_failure(self):
        """Test initialization failure"""
        with patch(
            "ragme.utils.storage_management.ConfigManager",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises(SystemExit):
                StorageManager()

    def test_check_storage_health_success(self, storage_manager):
        """Test successful health check"""
        result = storage_manager.check_storage_health()
        assert result is True
        storage_manager.storage.list_files.assert_called_once_with(
            prefix="", recursive=False
        )

    def test_check_storage_health_failure(self, storage_manager):
        """Test health check failure"""
        storage_manager.storage.list_files.side_effect = Exception("Connection error")
        result = storage_manager.check_storage_health()
        assert result is False

    def test_list_buckets_success(self, storage_manager, capsys):
        """Test successful bucket listing"""
        storage_manager.list_buckets()
        captured = capsys.readouterr()
        assert "Found 2 bucket(s)" in captured.out
        assert "bucket1" in captured.out
        assert "bucket2" in captured.out

    def test_list_buckets_empty(self, storage_manager, capsys):
        """Test bucket listing with no buckets"""
        storage_manager.storage.list_buckets.return_value = []
        storage_manager.list_buckets()
        captured = capsys.readouterr()
        assert "No buckets found" in captured.out

    def test_list_buckets_with_details(self, storage_manager, capsys):
        """Test bucket listing with detailed information"""
        storage_manager.list_buckets(show_details=True)
        captured = capsys.readouterr()
        assert "Size:" in captured.out
        assert "Created:" in captured.out

    def test_list_files_success(self, storage_manager, capsys):
        """Test successful file listing"""
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "Found 2 file(s) in storage" in captured.out
        assert "test1.pdf" in captured.out
        assert "test2.jpg" in captured.out

    def test_list_files_empty(self, storage_manager, capsys):
        """Test file listing with no files"""
        storage_manager.storage.list_files.return_value = []
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "No files found in storage" in captured.out

    def test_list_files_with_prefix(self, storage_manager):
        """Test file listing with prefix"""
        storage_manager.list_files(prefix="test")
        storage_manager.storage.list_files.assert_called_with(
            prefix="test", recursive=True
        )

    def test_list_files_with_details(self, storage_manager, capsys):
        """Test file listing with detailed information"""
        storage_manager.list_files(show_details=True)
        captured = capsys.readouterr()
        assert "Size:" in captured.out
        assert "Modified:" in captured.out

    def test_list_files_specific_bucket(self, storage_manager, capsys):
        """Test file listing from specific bucket"""
        storage_manager.list_files(bucket_name="bucket1")
        captured = capsys.readouterr()
        assert "Found 1 file(s) in bucket 'bucket1'" in captured.out
        assert "bucket1_file1.pdf" in captured.out
        storage_manager.storage.list_files_in_bucket.assert_called_with(
            "bucket1", prefix="", recursive=True
        )

    def test_list_files_specific_bucket_not_found(self, storage_manager, capsys):
        """Test file listing from non-existent bucket"""
        storage_manager.storage.bucket_exists.return_value = False
        storage_manager.list_files(bucket_name="nonexistent")
        captured = capsys.readouterr()
        assert "Bucket not found: nonexistent" in captured.out

    def test_list_files_all_buckets(self, storage_manager, capsys):
        """Test file listing from all buckets"""
        storage_manager.list_files(all_buckets=True)
        captured = capsys.readouterr()
        assert "Bucket: bucket1" in captured.out
        assert "Bucket: bucket2" in captured.out
        assert "Total files across all buckets: 2" in captured.out

    def test_list_files_all_buckets_empty(self, storage_manager, capsys):
        """Test file listing from all buckets when no buckets exist"""
        storage_manager.storage.list_buckets.return_value = []
        storage_manager.list_files(all_buckets=True)
        captured = capsys.readouterr()
        assert "No buckets found" in captured.out

    def test_show_links_single_file(self, storage_manager, capsys):
        """Test showing links for single file"""
        storage_manager.show_links("test1.pdf")
        captured = capsys.readouterr()
        assert "Download link for 'test1.pdf'" in captured.out
        assert "http://localhost:8021/storage/test1.pdf" in captured.out

    def test_show_links_all_files(self, storage_manager, capsys):
        """Test showing links for all files"""
        storage_manager.show_links()
        captured = capsys.readouterr()
        assert "Download links for 2 file(s)" in captured.out
        assert "http://localhost:8021/storage/test1.pdf" in captured.out

    def test_show_links_file_not_found(self, storage_manager, capsys):
        """Test showing links for non-existent file"""
        storage_manager.storage.file_exists.return_value = False
        storage_manager.show_links("nonexistent.pdf")
        captured = capsys.readouterr()
        assert "File not found: nonexistent.pdf" in captured.out

    def test_delete_file_success(self, storage_manager, capsys):
        """Test successful file deletion"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_file("test1.pdf")
            captured = capsys.readouterr()
            assert "Deleted: test1.pdf" in captured.out
            storage_manager.storage.delete_file.assert_called_once_with("test1.pdf")

    def test_delete_file_cancelled(self, storage_manager, capsys):
        """Test cancelled file deletion"""
        with patch("builtins.input", return_value="no"):
            storage_manager.delete_file("test1.pdf")
            captured = capsys.readouterr()
            assert "Deletion cancelled" in captured.out
            storage_manager.storage.delete_file.assert_not_called()

    def test_delete_file_force(self, storage_manager, capsys):
        """Test forced file deletion"""
        storage_manager.delete_file("test1.pdf", force=True)
        captured = capsys.readouterr()
        assert "Deleted: test1.pdf" in captured.out
        storage_manager.storage.delete_file.assert_called_once_with("test1.pdf")

    def test_delete_file_not_found(self, storage_manager, capsys):
        """Test deletion of non-existent file"""
        storage_manager.storage.file_exists.return_value = False
        storage_manager.delete_file("nonexistent.pdf")
        captured = capsys.readouterr()
        assert "File not found: nonexistent.pdf" in captured.out

    def test_delete_file_from_bucket_success(self, storage_manager, capsys):
        """Test successful file deletion from specific bucket"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_file("bucket1_file1.pdf", bucket_name="bucket1")
            captured = capsys.readouterr()
            assert "Deleted: bucket1_file1.pdf from bucket bucket1" in captured.out
            storage_manager.storage.delete_file_from_bucket.assert_called_once_with(
                "bucket1", "bucket1_file1.pdf"
            )

    def test_delete_file_from_bucket_not_found(self, storage_manager, capsys):
        """Test deletion from non-existent bucket"""
        storage_manager.storage.bucket_exists.return_value = False
        storage_manager.delete_file("test1.pdf", bucket_name="nonexistent")
        captured = capsys.readouterr()
        assert "Bucket not found: nonexistent" in captured.out

    def test_delete_file_from_bucket_file_not_found(self, storage_manager, capsys):
        """Test deletion of non-existent file from bucket"""
        storage_manager.storage.list_files_in_bucket.return_value = []
        storage_manager.delete_file("nonexistent.pdf", bucket_name="bucket1")
        captured = capsys.readouterr()
        assert "File not found: nonexistent.pdf in bucket bucket1" in captured.out

    def test_delete_all_files_success(self, storage_manager, capsys):
        """Test successful bulk deletion"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_all_files()
            captured = capsys.readouterr()
            assert "Successfully deleted 2/2 files" in captured.out
            assert storage_manager.storage.delete_file.call_count == 2

    def test_delete_all_files_cancelled(self, storage_manager, capsys):
        """Test cancelled bulk deletion"""
        with patch("builtins.input", return_value="no"):
            storage_manager.delete_all_files()
            captured = capsys.readouterr()
            assert "Deletion cancelled" in captured.out
            storage_manager.storage.delete_file.assert_not_called()

    def test_delete_all_files_force(self, storage_manager, capsys):
        """Test forced bulk deletion"""
        storage_manager.delete_all_files(force=True)
        captured = capsys.readouterr()
        assert "Successfully deleted 2/2 files" in captured.out
        assert storage_manager.storage.delete_file.call_count == 2

    def test_delete_all_files_with_prefix(self, storage_manager):
        """Test bulk deletion with prefix"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_all_files(prefix="test")
            storage_manager.storage.list_files.assert_called_with(
                prefix="test", recursive=True
            )

    def test_delete_all_files_empty(self, storage_manager, capsys):
        """Test bulk deletion with no files"""
        storage_manager.storage.list_files.return_value = []
        storage_manager.delete_all_files()
        captured = capsys.readouterr()
        assert "No files found to delete" in captured.out

    def test_delete_all_files_from_bucket_success(self, storage_manager, capsys):
        """Test bulk deletion from specific bucket"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_all_files(bucket_name="bucket1")
            captured = capsys.readouterr()
            assert (
                "Successfully deleted 1/1 files from bucket 'bucket1'" in captured.out
            )
            storage_manager.storage.list_files_in_bucket.assert_called_with(
                "bucket1", prefix="", recursive=True
            )

    def test_delete_all_files_from_bucket_not_found(self, storage_manager, capsys):
        """Test bulk deletion from non-existent bucket"""
        storage_manager.storage.bucket_exists.return_value = False
        storage_manager.delete_all_files(bucket_name="nonexistent")
        captured = capsys.readouterr()
        assert "Bucket not found: nonexistent" in captured.out

    def test_delete_all_files_from_all_buckets_success(self, storage_manager, capsys):
        """Test bulk deletion from all buckets"""
        with patch("builtins.input", return_value="yes"):
            storage_manager.delete_all_files(all_buckets=True)
            captured = capsys.readouterr()
            assert "Successfully deleted 2/2 files from 2 bucket(s)" in captured.out

    def test_delete_all_files_from_all_buckets_empty(self, storage_manager, capsys):
        """Test bulk deletion from all buckets when no buckets exist"""
        storage_manager.storage.list_buckets.return_value = []
        storage_manager.delete_all_files(all_buckets=True)
        captured = capsys.readouterr()
        assert "No buckets found" in captured.out

    def test_show_info_success(self, storage_manager, capsys):
        """Test showing storage information"""
        storage_manager.show_info()
        captured = capsys.readouterr()
        assert "Storage Information" in captured.out
        assert "Type: local" in captured.out
        assert "Storage service is accessible" in captured.out

    def test_show_info_failure(self, storage_manager, capsys):
        """Test showing storage information with failure"""
        storage_manager.storage.list_files.side_effect = Exception("Connection error")
        storage_manager.show_info()
        captured = capsys.readouterr()
        assert "Storage service is not accessible" in captured.out

    def test_check_health_success(self, storage_manager, capsys):
        """Test successful health check"""
        storage_manager.check_health()
        captured = capsys.readouterr()
        assert "Storage Health Check" in captured.out
        assert "✅ Storage service is accessible" in captured.out
        assert "✅ List operation: OK" in captured.out
        assert "✅ Directory access: OK" in captured.out
        assert "✅ URL generation: OK" in captured.out
        assert "📦 Available buckets:" in captured.out

    def test_check_health_verbose(self, storage_manager, capsys):
        """Test verbose health check"""
        storage_manager.check_health(verbose=True)
        captured = capsys.readouterr()
        assert "Storage Health Check" in captured.out
        assert "Found 2 files" in captured.out
        assert "Test URL:" in captured.out

    def test_check_health_failure(self, storage_manager, capsys):
        """Test health check with failure"""
        storage_manager.storage.list_files.side_effect = Exception("Connection error")
        storage_manager.check_health()
        captured = capsys.readouterr()
        assert "❌ Storage service is not accessible" in captured.out
        assert "Troubleshooting tips:" in captured.out

    def test_size_formatting(self, storage_manager, capsys):
        """Test size formatting in different units"""
        # Test bytes
        storage_manager.storage.list_files.return_value = [
            {
                "name": "small.txt",
                "size": 512,
                "last_modified": datetime.now(),
                "etag": "abc",
            }
        ]
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "512 B" in captured.out

        # Test KB
        storage_manager.storage.list_files.return_value = [
            {
                "name": "medium.txt",
                "size": 1536,
                "last_modified": datetime.now(),
                "etag": "abc",
            }
        ]
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "1.5 KB" in captured.out

        # Test MB
        storage_manager.storage.list_files.return_value = [
            {
                "name": "large.txt",
                "size": 2097152,
                "last_modified": datetime.now(),
                "etag": "abc",
            }
        ]
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "2.0 MB" in captured.out

    def test_date_formatting(self, storage_manager, capsys):
        """Test date formatting"""
        test_date = datetime(2023, 12, 25, 14, 30, 45)
        storage_manager.storage.list_files.return_value = [
            {
                "name": "test.txt",
                "size": 1024,
                "last_modified": test_date,
                "etag": "abc",
            }
        ]
        storage_manager.list_files()
        captured = capsys.readouterr()
        assert "2023-12-25 14:30:45" in captured.out

    def test_error_handling_list_files(self, storage_manager, capsys):
        """Test error handling in list_files"""
        storage_manager.storage.list_files.side_effect = Exception("Storage error")
        with pytest.raises(SystemExit):
            storage_manager.list_files()
        captured = capsys.readouterr()
        assert "Error listing files" in captured.out

    def test_error_handling_list_buckets(self, storage_manager, capsys):
        """Test error handling in list_buckets"""
        storage_manager.storage.list_buckets.side_effect = Exception("Storage error")
        with pytest.raises(SystemExit):
            storage_manager.list_buckets()
        captured = capsys.readouterr()
        assert "Error listing buckets" in captured.out

    def test_error_handling_show_links(self, storage_manager, capsys):
        """Test error handling in show_links"""
        storage_manager.storage.get_file_url.side_effect = Exception(
            "URL generation error"
        )
        with pytest.raises(SystemExit):
            storage_manager.show_links()
        captured = capsys.readouterr()
        assert "Error generating links" in captured.out

    def test_error_handling_delete_file(self, storage_manager, capsys):
        """Test error handling in delete_file"""
        storage_manager.storage.delete_file.side_effect = Exception("Delete error")
        with pytest.raises(SystemExit):
            storage_manager.delete_file("test.pdf", force=True)
        captured = capsys.readouterr()
        assert "Error deleting file" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])
