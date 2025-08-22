"""
Unit tests for the storage service
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ragme.utils.config_manager import ConfigManager
from src.ragme.utils.storage import StorageService


class TestStorageService:
    """Test cases for StorageService"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=ConfigManager)
        config.get.return_value = {
            "type": "minio",
            "minio": {
                "endpoint": "localhost:9000",
                "access_key": "minioadmin",
                "secret_key": "minioadmin",
                "secure": False,
                "bucket_name": "test_bucket",
                "region": "us-east-1",
            },
        }
        return config

    @pytest.fixture
    def storage_service(self, mock_config):
        """Create a storage service instance for testing"""
        with patch("src.ragme.utils.storage.Minio") as mock_minio:
            mock_client = Mock()
            mock_minio.return_value = mock_client
            mock_client.bucket_exists.return_value = True

            service = StorageService(mock_config)
            service.client = mock_client
            service.bucket_name = "test_bucket"
            return service

    def test_init_minio_client(self, mock_config):
        """Test MinIO client initialization"""
        with patch("src.ragme.utils.storage.Minio") as mock_minio:
            mock_client = Mock()
            mock_minio.return_value = mock_client
            mock_client.bucket_exists.return_value = False

            StorageService(mock_config)

            mock_minio.assert_called_once_with(
                endpoint="localhost:9000",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
                region="us-east-1",
            )
            mock_client.make_bucket.assert_called_once_with("test_bucket")

    def test_upload_file(self, storage_service, temp_dir):
        """Test file upload functionality"""
        # Create a test file
        test_file_path = os.path.join(temp_dir, "test.pdf")
        test_content = b"Test PDF content"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        # Mock the MinIO client response
        storage_service.client.put_object.return_value = None

        # Test upload
        result = storage_service.upload_file(
            test_file_path, "test.pdf", "application/pdf"
        )

        assert result == "test.pdf"
        storage_service.client.put_object.assert_called_once()
        call_args = storage_service.client.put_object.call_args
        assert call_args[0][0] == "test_bucket"  # bucket name
        assert call_args[0][1] == "test.pdf"  # object name
        assert call_args[1]["content_type"] == "application/pdf"

    def test_upload_data(self, storage_service):
        """Test data upload functionality"""
        test_data = b"Test image data"

        # Mock the MinIO client response
        storage_service.client.put_object.return_value = None

        # Test upload
        result = storage_service.upload_data(test_data, "test.png", "image/png")

        assert result == "test.png"
        storage_service.client.put_object.assert_called_once()
        call_args = storage_service.client.put_object.call_args
        assert call_args[0][0] == "test_bucket"  # bucket name
        assert call_args[0][1] == "test.png"  # object name
        assert call_args[1]["content_type"] == "image/png"

    def test_download_file(self, storage_service, temp_dir):
        """Test file download functionality"""
        download_path = os.path.join(temp_dir, "downloaded.pdf")

        # Mock the MinIO client response
        storage_service.client.fget_object.return_value = None

        # Test download
        result = storage_service.download_file("test.pdf", download_path)

        assert result is True
        storage_service.client.fget_object.assert_called_once_with(
            "test_bucket", "test.pdf", download_path
        )

    def test_get_file(self, storage_service):
        """Test getting file data"""
        test_data = b"Test file content"

        # Mock the MinIO client response
        mock_response = Mock()
        mock_response.read.return_value = test_data
        mock_response.close.return_value = None
        mock_response.release_conn.return_value = None
        storage_service.client.get_object.return_value = mock_response

        # Test get file
        result = storage_service.get_file("test.pdf")

        assert result == test_data
        storage_service.client.get_object.assert_called_once_with(
            "test_bucket", "test.pdf"
        )
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_list_files(self, storage_service):
        """Test listing files"""
        # Mock the MinIO client response
        mock_objects = [
            Mock(
                object_name="test1.pdf",
                size=1024,
                last_modified="2024-01-01",
                etag="abc123",
            ),
            Mock(
                object_name="test2.png",
                size=2048,
                last_modified="2024-01-02",
                etag="def456",
            ),
        ]
        storage_service.client.list_objects.return_value = mock_objects

        # Test list files
        result = storage_service.list_files(prefix="test", recursive=True)

        assert len(result) == 2
        assert result[0]["name"] == "test1.pdf"
        assert result[0]["size"] == 1024
        assert result[1]["name"] == "test2.png"
        assert result[1]["size"] == 2048

        storage_service.client.list_objects.assert_called_once_with(
            "test_bucket", prefix="test", recursive=True
        )

    def test_delete_file(self, storage_service):
        """Test file deletion"""
        # Mock the MinIO client response
        storage_service.client.remove_object.return_value = None

        # Test delete
        result = storage_service.delete_file("test.pdf")

        assert result is True
        storage_service.client.remove_object.assert_called_once_with(
            "test_bucket", "test.pdf"
        )

    def test_file_exists(self, storage_service):
        """Test file existence check"""
        # Mock the MinIO client response
        storage_service.client.stat_object.return_value = Mock()

        # Test file exists
        result = storage_service.file_exists("test.pdf")

        assert result is True
        storage_service.client.stat_object.assert_called_once_with(
            "test_bucket", "test.pdf"
        )

    def test_file_not_exists(self, storage_service):
        """Test file existence check when file doesn't exist"""
        from minio.error import S3Error

        # Mock the MinIO client to raise S3Error for non-existent file
        mock_error = S3Error(
            "NoSuchKey",
            "The specified key does not exist.",
            "test_bucket",
            "test_request_id",
            "test_host_id",
            "test_response",
        )
        storage_service.client.stat_object.side_effect = mock_error

        # Test file doesn't exist
        result = storage_service.file_exists("nonexistent.pdf")

        assert result is False

    def test_get_file_url(self, storage_service):
        """Test getting presigned URL"""
        expected_url = "http://localhost:9000/test_bucket/test.pdf?signature=abc123"

        # Mock the MinIO client response
        storage_service.client.presigned_get_object.return_value = expected_url

        # Test get URL
        result = storage_service.get_file_url("test.pdf", expires_in=3600)

        assert result == expected_url
        from datetime import timedelta

        storage_service.client.presigned_get_object.assert_called_once_with(
            "test_bucket", "test.pdf", expires=timedelta(seconds=3600)
        )

    def test_get_file_info(self, storage_service):
        """Test getting file information"""
        # Mock the MinIO client response
        mock_stat = Mock(
            size=1024,
            last_modified="2024-01-01",
            etag="abc123",
            content_type="application/pdf",
        )
        storage_service.client.stat_object.return_value = mock_stat

        # Test get file info
        result = storage_service.get_file_info("test.pdf")

        assert result["name"] == "test.pdf"
        assert result["size"] == 1024
        assert result["last_modified"] == "2024-01-01"
        assert result["etag"] == "abc123"
        assert result["content_type"] == "application/pdf"

        storage_service.client.stat_object.assert_called_once_with(
            "test_bucket", "test.pdf"
        )

    def test_upload_file_with_auto_content_type(self, storage_service, temp_dir):
        """Test file upload with automatic content type detection"""
        # Create a test PDF file
        test_file_path = os.path.join(temp_dir, "test.pdf")
        test_content = b"%PDF-1.4 Test PDF content"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        # Mock the MinIO client response
        storage_service.client.put_object.return_value = None

        # Test upload without specifying content type
        result = storage_service.upload_file(test_file_path, "test.pdf")

        assert result == "test.pdf"
        storage_service.client.put_object.assert_called_once()
        call_args = storage_service.client.put_object.call_args
        assert call_args[1]["content_type"] == "application/pdf"

    def test_upload_image_file(self, storage_service, temp_dir):
        """Test image file upload"""
        # Create a test image file
        test_file_path = os.path.join(temp_dir, "test.png")
        test_content = b"\x89PNG\r\n\x1a\nTest PNG content"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        # Mock the MinIO client response
        storage_service.client.put_object.return_value = None

        # Test upload
        result = storage_service.upload_file(test_file_path, "test.png", "image/png")

        assert result == "test.png"
        storage_service.client.put_object.assert_called_once()
        call_args = storage_service.client.put_object.call_args
        assert call_args[0][0] == "test_bucket"  # bucket name
        assert call_args[0][1] == "test.png"  # object name
        assert call_args[1]["content_type"] == "image/png"

    def test_list_files_with_prefix(self, storage_service):
        """Test listing files with specific prefix"""
        # Mock the MinIO client response
        mock_objects = [
            Mock(
                object_name="documents/test1.pdf",
                size=1024,
                last_modified="2024-01-01",
                etag="abc123",
            ),
            Mock(
                object_name="documents/test2.pdf",
                size=2048,
                last_modified="2024-01-02",
                etag="def456",
            ),
        ]
        storage_service.client.list_objects.return_value = mock_objects

        # Test list files with prefix
        result = storage_service.list_files(prefix="documents/", recursive=True)

        assert len(result) == 2
        assert result[0]["name"] == "documents/test1.pdf"
        assert result[1]["name"] == "documents/test2.pdf"

        storage_service.client.list_objects.assert_called_once_with(
            "test_bucket", prefix="documents/", recursive=True
        )

    def test_error_handling_upload_nonexistent_file(self, storage_service):
        """Test error handling when uploading non-existent file"""
        with pytest.raises(FileNotFoundError):
            storage_service.upload_file("/nonexistent/file.pdf")

    def test_error_handling_upload_file_exception(self, storage_service, temp_dir):
        """Test error handling when upload fails"""
        # Create a test file
        test_file_path = os.path.join(temp_dir, "test.pdf")
        test_content = b"Test PDF content"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        # Mock the MinIO client to raise an exception
        storage_service.client.put_object.side_effect = Exception("Upload failed")

        # Test upload failure
        with pytest.raises(Exception, match="Upload failed"):
            storage_service.upload_file(test_file_path, "test.pdf")

    def test_error_handling_delete_file_exception(self, storage_service):
        """Test error handling when delete fails"""
        # Mock the MinIO client to raise an exception
        storage_service.client.remove_object.side_effect = Exception("Delete failed")

        # Test delete failure
        with pytest.raises(Exception, match="Delete failed"):
            storage_service.delete_file("test.pdf")
