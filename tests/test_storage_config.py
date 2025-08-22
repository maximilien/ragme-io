"""Unit tests for storage configuration in ConfigManager"""

from unittest.mock import Mock, patch

import pytest

from src.ragme.utils.config_manager import ConfigManager


class TestStorageConfig:
    """Test cases for storage configuration methods"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config_data = {
            "storage": {
                "type": "minio",
                "copy_uploaded_docs": True,
                "copy_uploaded_images": False,
                "minio": {
                    "endpoint": "localhost:9000",
                    "access_key": "minioadmin",
                    "secret_key": "minioadmin",
                    "secure": False,
                    "bucket_name": "test-bucket",
                    "region": "us-east-1",
                },
                "s3": {
                    "endpoint": "https://s3.amazonaws.com",
                    "access_key": "test-access-key",
                    "secret_key": "test-secret-key",
                    "bucket_name": "test-s3-bucket",
                    "region": "us-west-2",
                    "secure": True,
                },
                "local": {"path": "local_storage/"},
            }
        }

        # Create a new ConfigManager instance and directly set the config
        config = ConfigManager()
        config._config = config_data
        return config

    def test_get_storage_config(self, mock_config):
        """Test getting storage configuration"""
        storage_config = mock_config.get_storage_config()

        assert storage_config["type"] == "minio"
        assert storage_config["copy_uploaded_docs"] is True
        assert storage_config["copy_uploaded_images"] is False
        assert "minio" in storage_config
        assert "s3" in storage_config
        assert "local" in storage_config

    def test_get_storage_type(self, mock_config):
        """Test getting storage type"""
        storage_type = mock_config.get_storage_type()
        assert storage_type == "minio"

    def test_get_storage_type_default(self):
        """Test getting storage type with default value"""
        config = ConfigManager()
        config._config = {}
        storage_type = config.get_storage_type()
        assert storage_type == "minio"

    def test_get_storage_backend_config_minio(self, mock_config):
        """Test getting MinIO backend configuration"""
        minio_config = mock_config.get_storage_backend_config("minio")

        assert minio_config["endpoint"] == "localhost:9000"
        assert minio_config["access_key"] == "minioadmin"
        assert minio_config["secret_key"] == "minioadmin"
        assert minio_config["secure"] is False
        assert minio_config["bucket_name"] == "test-bucket"
        assert minio_config["region"] == "us-east-1"

    def test_get_storage_backend_config_s3(self, mock_config):
        """Test getting S3 backend configuration"""
        s3_config = mock_config.get_storage_backend_config("s3")

        assert s3_config["endpoint"] == "https://s3.amazonaws.com"
        assert s3_config["access_key"] == "test-access-key"
        assert s3_config["secret_key"] == "test-secret-key"
        assert s3_config["bucket_name"] == "test-s3-bucket"
        assert s3_config["region"] == "us-west-2"
        assert s3_config["secure"] is True

    def test_get_storage_backend_config_local(self, mock_config):
        """Test getting local backend configuration"""
        local_config = mock_config.get_storage_backend_config("local")

        assert local_config["path"] == "local_storage/"

    def test_get_storage_backend_config_current_type(self, mock_config):
        """Test getting backend config for current storage type"""
        backend_config = mock_config.get_storage_backend_config()

        # Should return minio config since that's the current type
        assert backend_config["endpoint"] == "localhost:9000"
        assert backend_config["bucket_name"] == "test-bucket"

    def test_get_storage_bucket_name(self, mock_config):
        """Test getting storage bucket name"""
        bucket_name = mock_config.get_storage_bucket_name()
        assert bucket_name == "test-bucket"

    def test_get_storage_bucket_name_default(self):
        """Test getting storage bucket name with default value"""
        config = ConfigManager()
        config._config = {"storage": {"type": "minio", "minio": {}}}
        bucket_name = config.get_storage_bucket_name()
        assert bucket_name == "ragme-storage"

    def test_is_copy_uploaded_docs_enabled(self, mock_config):
        """Test checking if copying uploaded documents is enabled"""
        is_enabled = mock_config.is_copy_uploaded_docs_enabled()
        assert is_enabled is True

    def test_is_copy_uploaded_docs_disabled(self):
        """Test checking if copying uploaded documents is disabled"""
        config = ConfigManager()
        config._config = {"storage": {"type": "minio", "copy_uploaded_docs": False}}
        is_enabled = config.is_copy_uploaded_docs_enabled()
        assert is_enabled is False

    def test_is_copy_uploaded_docs_default(self):
        """Test checking if copying uploaded documents with default value"""
        config = ConfigManager()
        config._config = {"storage": {"type": "minio"}}
        is_enabled = config.is_copy_uploaded_docs_enabled()
        assert is_enabled is False

    def test_is_copy_uploaded_images_enabled(self):
        """Test checking if copying uploaded images is enabled"""
        config = ConfigManager()
        config._config = {"storage": {"type": "minio", "copy_uploaded_images": True}}
        is_enabled = config.is_copy_uploaded_images_enabled()
        assert is_enabled is True

    def test_is_copy_uploaded_images_disabled(self, mock_config):
        """Test checking if copying uploaded images is disabled"""
        is_enabled = mock_config.is_copy_uploaded_images_enabled()
        assert is_enabled is False

    def test_is_copy_uploaded_images_default(self):
        """Test checking if copying uploaded images with default value"""
        config = ConfigManager()
        config._config = {"storage": {"type": "minio"}}
        is_enabled = config.is_copy_uploaded_images_enabled()
        assert is_enabled is False

    def test_storage_config_not_present(self):
        """Test behavior when storage config is not present"""
        config = ConfigManager()
        config._config = {}

        # Should return default values
        assert config.get_storage_type() == "minio"
        assert config.get_storage_bucket_name() == "ragme-storage"
        assert config.is_copy_uploaded_docs_enabled() is False
        assert config.is_copy_uploaded_images_enabled() is False
        assert config.get_storage_config() == {}
        assert config.get_storage_backend_config() == {}

    def test_storage_config_partial(self):
        """Test behavior with partial storage configuration"""
        config = ConfigManager()
        config._config = {
            "storage": {
                "type": "s3",
                "copy_uploaded_docs": True,
                # Missing other config
            }
        }

        assert config.get_storage_type() == "s3"
        assert config.is_copy_uploaded_docs_enabled() is True
        assert config.is_copy_uploaded_images_enabled() is False
        assert config.get_storage_bucket_name() == "ragme-storage"  # Default
        assert config.get_storage_backend_config("s3") == {}  # Empty config
