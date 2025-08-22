"""
Integration tests for the storage service with MinIO
"""

import os
import tempfile
import time
from pathlib import Path

import pytest

from src.ragme.utils.config_manager import ConfigManager
from src.ragme.utils.storage import StorageService


class TestStorageIntegration:
    """Integration tests for StorageService with MinIO"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def test_config(self):
        """Create test configuration for MinIO"""
        config = ConfigManager()
        # Override storage config for testing
        config._config["storage"] = {
            "type": "minio",
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
        """Create storage service instance for integration testing"""
        return StorageService(test_config)

    def test_minio_connection(self, storage_service):
        """Test connection to MinIO server"""
        # This test assumes MinIO is running on localhost:9000
        # If MinIO is not running, this test will be skipped
        try:
            # Try to list files to test connection
            files = storage_service.list_files()
            assert isinstance(files, list)
        except Exception as e:
            pytest.skip(f"MinIO not available: {e}")

    def test_upload_and_download_pdf(self, storage_service, temp_dir):
        """Test uploading and downloading a PDF file"""
        # Create a test PDF file
        test_file_path = os.path.join(temp_dir, "test_document.pdf")
        test_content = b"%PDF-1.4\nTest PDF content for integration testing"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload the file
            object_name = storage_service.upload_file(
                test_file_path, "test_document.pdf", "application/pdf"
            )
            assert object_name == "test_document.pdf"

            # Verify file exists
            assert storage_service.file_exists("test_document.pdf")

            # Get file info
            file_info = storage_service.get_file_info("test_document.pdf")
            assert file_info["name"] == "test_document.pdf"
            assert file_info["content_type"] == "application/pdf"
            assert file_info["size"] > 0

            # Download the file
            download_path = os.path.join(temp_dir, "downloaded_document.pdf")
            result = storage_service.download_file("test_document.pdf", download_path)
            assert result is True

            # Verify downloaded content
            with open(download_path, "rb") as f:
                downloaded_content = f.read()
            assert downloaded_content == test_content

            # Get file data directly
            file_data = storage_service.get_file("test_document.pdf")
            assert file_data == test_content

        finally:
            # Clean up
            if storage_service.file_exists("test_document.pdf"):
                storage_service.delete_file("test_document.pdf")

    def test_upload_and_download_image(self, storage_service, temp_dir):
        """Test uploading and downloading an image file"""
        # Create a test PNG file
        test_file_path = os.path.join(temp_dir, "test_image.png")
        test_content = b"\x89PNG\r\n\x1a\nTest PNG content for integration testing"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload the file
            object_name = storage_service.upload_file(
                test_file_path, "test_image.png", "image/png"
            )
            assert object_name == "test_image.png"

            # Verify file exists
            assert storage_service.file_exists("test_image.png")

            # Get file info
            file_info = storage_service.get_file_info("test_image.png")
            assert file_info["name"] == "test_image.png"
            assert file_info["content_type"] == "image/png"
            assert file_info["size"] > 0

            # Download the file
            download_path = os.path.join(temp_dir, "downloaded_image.png")
            result = storage_service.download_file("test_image.png", download_path)
            assert result is True

            # Verify downloaded content
            with open(download_path, "rb") as f:
                downloaded_content = f.read()
            assert downloaded_content == test_content

        finally:
            # Clean up
            if storage_service.file_exists("test_image.png"):
                storage_service.delete_file("test_image.png")

    def test_upload_data_and_delete(self, storage_service):
        """Test uploading binary data and deleting"""
        test_data = b"Test binary data for integration testing"

        try:
            # Upload data
            object_name = storage_service.upload_data(
                test_data, "test_data.bin", "application/octet-stream"
            )
            assert object_name == "test_data.bin"

            # Verify file exists
            assert storage_service.file_exists("test_data.bin")

            # Get file data
            retrieved_data = storage_service.get_file("test_data.bin")
            assert retrieved_data == test_data

            # Delete file
            result = storage_service.delete_file("test_data.bin")
            assert result is True

            # Verify file is deleted
            assert not storage_service.file_exists("test_data.bin")

        except Exception:
            # Clean up on failure
            if storage_service.file_exists("test_data.bin"):
                storage_service.delete_file("test_data.bin")
            raise

    def test_list_files_with_prefix(self, storage_service, temp_dir):
        """Test listing files with prefix"""
        # Create test files
        test_files = [
            ("documents/test1.pdf", b"PDF content 1"),
            ("documents/test2.pdf", b"PDF content 2"),
            ("images/test1.png", b"PNG content 1"),
            ("images/test2.png", b"PNG content 2"),
        ]

        uploaded_files = []

        try:
            # Upload test files
            for file_name, content in test_files:
                file_path = os.path.join(temp_dir, os.path.basename(file_name))
                with open(file_path, "wb") as f:
                    f.write(content)

                storage_service.upload_file(file_path, file_name)
                uploaded_files.append(file_name)

            # List all files
            all_files = storage_service.list_files()
            assert len(all_files) >= len(test_files)

            # List files with documents prefix
            doc_files = storage_service.list_files(prefix="documents/")
            assert len(doc_files) == 2
            doc_names = [f["name"] for f in doc_files]
            assert "documents/test1.pdf" in doc_names
            assert "documents/test2.pdf" in doc_names

            # List files with images prefix
            img_files = storage_service.list_files(prefix="images/")
            assert len(img_files) == 2
            img_names = [f["name"] for f in img_files]
            assert "images/test1.png" in img_names
            assert "images/test2.png" in img_names

        finally:
            # Clean up
            for file_name in uploaded_files:
                if storage_service.file_exists(file_name):
                    storage_service.delete_file(file_name)

    def test_file_url_generation(self, storage_service, temp_dir):
        """Test generating presigned URLs"""
        # Create a test file
        test_file_path = os.path.join(temp_dir, "test_url.pdf")
        test_content = b"Test content for URL generation"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload file
            storage_service.upload_file(test_file_path, "test_url.pdf")

            # Generate URL
            url = storage_service.get_file_url("test_url.pdf", expires_in=3600)
            assert url.startswith("http://")
            assert "test_url.pdf" in url

        finally:
            # Clean up
            if storage_service.file_exists("test_url.pdf"):
                storage_service.delete_file("test_url.pdf")

    def test_multiple_operations_sequence(self, storage_service, temp_dir):
        """Test a sequence of multiple operations"""
        test_files = [
            ("sequence_test1.pdf", b"PDF content 1"),
            ("sequence_test2.png", b"PNG content 2"),
            ("sequence_test3.txt", b"Text content 3"),
        ]

        uploaded_files = []

        try:
            # Upload multiple files
            for file_name, content in test_files:
                file_path = os.path.join(temp_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(content)

                storage_service.upload_file(file_path, file_name)
                uploaded_files.append(file_name)

                # Verify each file exists
                assert storage_service.file_exists(file_name)

            # List all files
            all_files = storage_service.list_files()
            assert len(all_files) >= len(test_files)

            # Update one file
            updated_content = b"Updated content for sequence test"
            storage_service.upload_data(
                updated_content, "sequence_test1.pdf", "application/pdf"
            )

            # Verify updated content
            retrieved_content = storage_service.get_file("sequence_test1.pdf")
            assert retrieved_content == updated_content

            # Delete files one by one
            for file_name in uploaded_files:
                result = storage_service.delete_file(file_name)
                assert result is True
                assert not storage_service.file_exists(file_name)

        except Exception:
            # Clean up on failure
            for file_name in uploaded_files:
                if storage_service.file_exists(file_name):
                    storage_service.delete_file(file_name)
            raise

    def test_error_handling_nonexistent_file(self, storage_service):
        """Test error handling for non-existent files"""
        # Try to get info for non-existent file
        with pytest.raises((FileNotFoundError, Exception)):
            storage_service.get_file_info("nonexistent_file.pdf")

        # Try to download non-existent file
        with pytest.raises((FileNotFoundError, Exception)):
            storage_service.download_file("nonexistent_file.pdf", "/tmp/test.pdf")

        # Try to get non-existent file data
        with pytest.raises((FileNotFoundError, Exception)):
            storage_service.get_file("nonexistent_file.pdf")

        # Check if non-existent file exists
        assert not storage_service.file_exists("nonexistent_file.pdf")

    def test_cleanup_after_failure(self, storage_service, temp_dir):
        """Test cleanup after operation failure"""
        # Create a test file
        test_file_path = os.path.join(temp_dir, "cleanup_test.pdf")
        test_content = b"Test content for cleanup"
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        try:
            # Upload file
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
