# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based `config`.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Support for class-based `config`.*",
)

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.vdbs.vector_db_base import CollectionConfig
from src.ragme.vdbs.vector_db_factory import create_vector_database


class TestCreateVectorDatabase:
    """Test cases for the create_vector_database factory function."""

    def test_create_weaviate_database(self):
        """Test creating a Weaviate vector database."""
        with (
            patch(
                "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
            ) as mock_weaviate_db,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_database_config"
            ) as mock_get_db_config,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_collections_config"
            ) as mock_get_collections_config,
        ):
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            # Mock database config with credentials
            mock_get_db_config.return_value = {
                "type": "weaviate",
                "api_key": "test_key",
                "url": "test_url",
            }

            # Mock collections config - return single text collection
            mock_get_collections_config.return_value = [
                {"name": "TestCollection", "type": "text"}
            ]

            db = create_vector_database("weaviate", "TestCollection")

            # Check that WeaviateVectorDatabase was called with a list of CollectionConfig objects
            mock_weaviate_db.assert_called_once()
            args, kwargs = mock_weaviate_db.call_args
            assert len(args) == 1
            collections = args[0]
            assert isinstance(collections, list)
            assert len(collections) == 1
            assert isinstance(collections[0], CollectionConfig)
            assert collections[0].name == "TestCollection"
            assert collections[0].type == "text"
            assert db == mock_instance

    def test_create_milvus_database(self):
        """Test creating a Milvus vector database."""
        with (
            patch(
                "src.ragme.vdbs.vector_db_factory.MilvusVectorDatabase"
            ) as mock_milvus_db,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_database_config"
            ) as mock_get_db_config,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_collections_config"
            ) as mock_get_collections_config,
        ):
            mock_instance = MagicMock()
            mock_milvus_db.return_value = mock_instance

            # Mock database config
            mock_get_db_config.return_value = {"type": "milvus"}

            # Mock collections config - return single text collection
            mock_get_collections_config.return_value = [
                {"name": "TestCollection", "type": "text"}
            ]

            db = create_vector_database("milvus", "TestCollection")

            # Check that MilvusVectorDatabase was called with a list of CollectionConfig objects
            mock_milvus_db.assert_called_once()
            args, kwargs = mock_milvus_db.call_args
            assert len(args) == 1
            collections = args[0]
            assert isinstance(collections, list)
            assert len(collections) == 1
            assert isinstance(collections[0], CollectionConfig)
            assert collections[0].name == "TestCollection"
            assert collections[0].type == "text"
            assert db == mock_instance

    def test_create_unsupported_database(self):
        """Test creating an unsupported database type."""
        with patch(
            "src.ragme.vdbs.vector_db_factory.config.get_database_config"
        ) as mock_get_db_config:
            mock_get_db_config.return_value = None

            with pytest.raises(
                ValueError, match="Unsupported vector database type: invalid"
            ):
                create_vector_database("invalid")

    def test_create_database_case_insensitive(self):
        """Test that database type is case insensitive."""
        with (
            patch(
                "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
            ) as mock_weaviate_db,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_database_config"
            ) as mock_get_db_config,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_collections_config"
            ) as mock_get_collections_config,
        ):
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            # Mock database config with credentials
            mock_get_db_config.return_value = {
                "type": "weaviate",
                "api_key": "test_key",
                "url": "test_url",
            }

            # Mock collections config - return single text collection
            mock_get_collections_config.return_value = [
                {"name": "TestCollection", "type": "text"}
            ]

            db = create_vector_database("WEAVIATE", "TestCollection")

            # Check that WeaviateVectorDatabase was called with a list of CollectionConfig objects
            mock_weaviate_db.assert_called_once()
            args, kwargs = mock_weaviate_db.call_args
            assert len(args) == 1
            collections = args[0]
            assert isinstance(collections, list)
            assert len(collections) == 1
            assert isinstance(collections[0], CollectionConfig)
            assert collections[0].name == "TestCollection"
            assert collections[0].type == "text"
            assert db == mock_instance

    def test_create_database_with_environment_default(self):
        """Test creating a database with environment variable default."""
        with (
            patch(
                "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
            ) as mock_weaviate_db,
            patch.dict("os.environ", {"VECTOR_DB_TYPE": "weaviate"}),
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_database_config"
            ) as mock_get_db_config,
            patch(
                "src.ragme.vdbs.vector_db_factory.config.get_collections_config"
            ) as mock_get_collections_config,
        ):
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            # Mock database config with credentials
            mock_get_db_config.return_value = {
                "type": "weaviate",
                "api_key": "test_key",
                "url": "test_url",
            }

            # Mock collections config - return both text and image collections
            mock_get_collections_config.return_value = [
                {"name": "TestCollection", "type": "text"},
                {"name": "TestImages", "type": "image"},
            ]

            db = create_vector_database(collection_name="TestCollection")

            # Check that WeaviateVectorDatabase was called with a list of CollectionConfig objects
            mock_weaviate_db.assert_called_once()
            args, kwargs = mock_weaviate_db.call_args
            assert len(args) == 1
            collections = args[0]
            assert isinstance(collections, list)
            assert len(collections) == 2
            # Should have both text and image collections from config
            assert any(
                c.name == "TestCollection" and c.type == "text" for c in collections
            )
            assert any(
                c.name == "TestImages" and c.type == "image" for c in collections
            )
            assert db == mock_instance
