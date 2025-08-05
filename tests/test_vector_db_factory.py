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

from src.ragme.vdbs.vector_db_factory import create_vector_database


class TestCreateVectorDatabase:
    """Test cases for the create_vector_database factory function."""

    def test_create_weaviate_database(self):
        """Test creating a Weaviate vector database."""
        with patch(
            "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
        ) as mock_weaviate_db:
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            db = create_vector_database("weaviate", "TestCollection")

            mock_weaviate_db.assert_called_once_with("TestCollection")
            assert db == mock_instance

    def test_create_milvus_database(self):
        """Test creating a Milvus vector database."""
        with patch(
            "src.ragme.vdbs.vector_db_factory.MilvusVectorDatabase"
        ) as mock_milvus_db:
            mock_instance = MagicMock()
            mock_milvus_db.return_value = mock_instance
            db = create_vector_database("milvus", "TestCollection")
            mock_milvus_db.assert_called_once_with("TestCollection")
            assert db == mock_instance

    def test_create_unsupported_database(self):
        """Test creating an unsupported database type."""
        with pytest.raises(
            ValueError, match="Unsupported vector database type: invalid"
        ):
            create_vector_database("invalid")

    def test_create_database_case_insensitive(self):
        """Test that database type is case insensitive."""
        with patch(
            "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
        ) as mock_weaviate_db:
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            db = create_vector_database("WEAVIATE", "TestCollection")

            mock_weaviate_db.assert_called_once_with("TestCollection")
            assert db == mock_instance

    def test_create_database_with_environment_default(self):
        """Test creating a database with environment variable default."""
        with (
            patch(
                "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
            ) as mock_weaviate_db,
            patch.dict("os.environ", {"VECTOR_DB_TYPE": "weaviate"}),
        ):
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance

            db = create_vector_database(collection_name="TestCollection")

            mock_weaviate_db.assert_called_once_with("TestCollection")
            assert db == mock_instance
