"""Integration tests for storage upload functionality"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ragme.utils.config_manager import ConfigManager
from src.ragme.utils.storage import StorageService


class TestStorageUploadIntegration:
    """Integration tests for storage upload functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def test_config(self):
        """Create a test configuration with storage enabled"""
        config = ConfigManager()
        # Override storage config for testing
        config._config["storage"] = {
            "type": "minio",
            "copy_uploaded_docs": True,
            "copy_uploaded_images": True,
            "minio": {
                "endpoint": "localhost:9000",
                "access_key": "minioadmin",
                "secret_key": "minioadmin",
                "secure": False,
                "bucket_name": "testbucket",
                "region": "us-east-1",
            },
        }
        return config

    @pytest.fixture
    def storage_service(self, test_config):
        """Create a storage service instance for testing"""
        return StorageService(test_config)

    def test_upload_document_to_storage_when_enabled(self, storage_service, temp_dir):
        """Test that documents are uploaded to storage when copy_uploaded_docs is enabled"""
        # Create a test PDF file
        test_file_path = os.path.join(temp_dir, "test_document.pdf")
        test_content = b"%PDF-1.4\nTest PDF content for storage upload testing"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload the file to storage
            object_name = storage_service.upload_file(
                test_file_path, "test_document.pdf", "application/pdf"
            )
            assert object_name == "test_document.pdf"

            # Verify file exists in storage
            assert storage_service.file_exists("test_document.pdf")

            # Get file info
            file_info = storage_service.get_file_info("test_document.pdf")
            assert file_info["name"] == "test_document.pdf"
            assert file_info["content_type"] == "application/pdf"
            assert file_info["size"] > 0

            # Download and verify content
            downloaded_data = storage_service.get_file("test_document.pdf")
            assert downloaded_data == test_content

        finally:
            # Clean up
            if storage_service.file_exists("test_document.pdf"):
                storage_service.delete_file("test_document.pdf")

    def test_upload_image_to_storage_when_enabled(self, storage_service, temp_dir):
        """Test that images are uploaded to storage when copy_uploaded_images is enabled"""
        # Create a test PNG file
        test_file_path = os.path.join(temp_dir, "test_image.png")
        test_content = b"\x89PNG\r\n\x1a\nTest PNG content for storage upload testing"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload the file to storage
            object_name = storage_service.upload_file(
                test_file_path, "test_image.png", "image/png"
            )
            assert object_name == "test_image.png"

            # Verify file exists in storage
            assert storage_service.file_exists("test_image.png")

            # Get file info
            file_info = storage_service.get_file_info("test_image.png")
            assert file_info["name"] == "test_image.png"
            assert file_info["content_type"] == "image/png"
            assert file_info["size"] > 0

            # Download and verify content
            downloaded_data = storage_service.get_file("test_image.png")
            assert downloaded_data == test_content

        finally:
            # Clean up
            if storage_service.file_exists("test_image.png"):
                storage_service.delete_file("test_image.png")

    def test_upload_data_to_storage(self, storage_service):
        """Test uploading binary data to storage"""
        test_data = b"Test binary data for storage upload testing"

        try:
            # Upload data to storage
            object_name = storage_service.upload_data(
                test_data, "test_data.bin", "application/octet-stream"
            )
            assert object_name == "test_data.bin"

            # Verify file exists in storage
            assert storage_service.file_exists("test_data.bin")

            # Get file info
            file_info = storage_service.get_file_info("test_data.bin")
            assert file_info["name"] == "test_data.bin"
            assert file_info["content_type"] == "application/octet-stream"
            assert file_info["size"] == len(test_data)

            # Download and verify content
            downloaded_data = storage_service.get_file("test_data.bin")
            assert downloaded_data == test_data

        finally:
            # Clean up
            if storage_service.file_exists("test_data.bin"):
                storage_service.delete_file("test_data.bin")

    def test_upload_with_timestamped_paths(self, storage_service, temp_dir):
        """Test uploading files with timestamped paths to avoid conflicts"""
        from datetime import datetime

        # Create test files
        test_files = [
            ("document1.pdf", b"PDF content 1"),
            ("document2.pdf", b"PDF content 2"),
            ("image1.png", b"PNG content 1"),
            ("image2.png", b"PNG content 2"),
        ]

        uploaded_paths = []

        try:
            for filename, content in test_files:
                # Create timestamped path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                storage_path = f"documents/{timestamp}_{filename}"

                # Upload data
                object_name = storage_service.upload_data(
                    content, storage_path, "application/octet-stream"
                )
                assert object_name == storage_path
                uploaded_paths.append(storage_path)

                # Verify file exists
                assert storage_service.file_exists(storage_path)

                # Verify content
                downloaded_data = storage_service.get_file(storage_path)
                assert downloaded_data == content

            # List files with documents prefix
            doc_files = storage_service.list_files(prefix="documents/")
            assert len(doc_files) >= len(test_files)

            # Verify all uploaded files are in the list
            uploaded_names = [path.split("/")[-1] for path in uploaded_paths]
            listed_names = [f["name"].split("/")[-1] for f in doc_files]

            for uploaded_name in uploaded_names:
                assert uploaded_name in listed_names

        finally:
            # Clean up all uploaded files
            for path in uploaded_paths:
                if storage_service.file_exists(path):
                    storage_service.delete_file(path)

    def test_storage_configuration_access(self, test_config):
        """Test that storage configuration can be accessed through ConfigManager"""
        # Test storage type
        assert test_config.get_storage_type() == "minio"

        # Test copy flags
        assert test_config.is_copy_uploaded_docs_enabled() is True
        assert test_config.is_copy_uploaded_images_enabled() is True

        # Test bucket name
        assert test_config.get_storage_bucket_name() == "testbucket"

        # Test backend config
        minio_config = test_config.get_storage_backend_config("minio")
        assert minio_config["endpoint"] == "localhost:9000"
        assert minio_config["access_key"] == "minioadmin"
        assert minio_config["bucket_name"] == "testbucket"

    def test_storage_service_with_config_manager(self, test_config):
        """Test that StorageService works correctly with ConfigManager"""
        storage_service = StorageService(test_config)

        # Verify the service is configured correctly
        assert storage_service.storage_type == "minio"
        assert storage_service.bucket_name == "testbucket"

        # Test basic functionality
        test_data = b"Test data for config manager integration"
        try:
            object_name = storage_service.upload_data(
                test_data, "config_test.txt", "text/plain"
            )
            assert object_name == "config_test.txt"
            assert storage_service.file_exists("config_test.txt")

            # Verify content
            downloaded_data = storage_service.get_file("config_test.txt")
            assert downloaded_data == test_data

        finally:
            if storage_service.file_exists("config_test.txt"):
                storage_service.delete_file("config_test.txt")

    def test_error_handling_during_upload(self, storage_service):
        """Test error handling during upload operations"""
        # Test uploading non-existent file
        with pytest.raises(FileNotFoundError):
            storage_service.upload_file("/nonexistent/file.pdf")

        # Test uploading empty data
        empty_data = b""
        try:
            object_name = storage_service.upload_data(
                empty_data, "empty_file.txt", "text/plain"
            )
            assert object_name == "empty_file.txt"
            assert storage_service.file_exists("empty_file.txt")

            # Verify empty file
            downloaded_data = storage_service.get_file("empty_file.txt")
            assert downloaded_data == empty_data

        finally:
            if storage_service.file_exists("empty_file.txt"):
                storage_service.delete_file("empty_file.txt")

    def test_storage_cleanup_after_failure(self, storage_service, temp_dir):
        """Test cleanup after upload failure"""
        # Create a test file
        test_file_path = os.path.join(temp_dir, "cleanup_test.pdf")
        test_content = b"Test content for cleanup testing"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload file successfully
            storage_service.upload_file(test_file_path, "cleanup_test.pdf")
            assert storage_service.file_exists("cleanup_test.pdf")

            # Simulate a failure scenario
            raise Exception("Simulated failure")

        except Exception:
            # Ensure cleanup happens even after failure
            if storage_service.file_exists("cleanup_test.pdf"):
                storage_service.delete_file("cleanup_test.pdf")
            assert not storage_service.file_exists("cleanup_test.pdf")
            # Don't re-raise the exception since this test is about cleanup
