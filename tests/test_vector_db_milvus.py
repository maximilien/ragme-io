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

# Suppress Milvus connection warnings during tests
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Failed to connect to Milvus.*"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Milvus client is not available.*"
)
# Suppress vector generation failure warnings during tests
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Failed to generate vector for document.*"
)

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.vdbs.vector_db_base import CollectionConfig
from src.ragme.vdbs.vector_db_milvus import MilvusVectorDatabase

# Check if pymilvus is available
try:
    import pymilvus

    PYMILVUS_AVAILABLE = True
except ImportError:
    PYMILVUS_AVAILABLE = False


@pytest.mark.skipif(not PYMILVUS_AVAILABLE, reason="pymilvus not available")
class TestMilvusVectorDatabase:
    """Test cases for the MilvusVectorDatabase implementation."""

    def _create_test_collections(self):
        """Create test collection configurations."""
        return [CollectionConfig("TestCollection", "text")]

    @patch("pymilvus.MilvusClient")
    def test_init_with_collection_name(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        assert db.text_collection.name == "TestCollection"
        assert db.text_collection.type == "text"
        # Client is not created until needed due to lazy initialization
        assert db.client is None
        # Trigger client creation
        db._ensure_client()
        assert db.client == mock_client

    @patch("pymilvus.MilvusClient")
    def test_setup_collection_exists(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        db.setup()
        mock_client.create_collection.assert_not_called()

    @patch("pymilvus.MilvusClient")
    def test_setup_collection_not_exists(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        db.setup()
        mock_client.create_collection.assert_called_once()

    @patch("pymilvus.MilvusClient")
    def test_write_documents(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
                "vector": [0.1] * 1536,
            },
            {
                "url": "http://test2.com",
                "text": "test content 2",
                "metadata": {"type": "webpage"},
                "vector": [0.2] * 1536,
            },
        ]
        db.write_documents(documents)
        mock_client.insert.assert_called_once()

    @patch("pymilvus.MilvusClient")
    @patch("openai.OpenAI")
    def test_write_documents_missing_vector(self, mock_openai, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client

        # Mock OpenAI client and embeddings response
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        mock_openai_instance.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536)
        ]

        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
            }
        ]
        db.write_documents(documents)
        mock_client.insert.assert_called_once()

    @patch("pymilvus.MilvusClient")
    def test_write_documents_missing_vector_generation_fails(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client

        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
            }
        ]
        # Should not raise an exception, but should log a warning
        db.write_documents(documents)
        mock_client.insert.assert_called_once()

    @patch("pymilvus.MilvusClient")
    def test_list_documents(self, mock_milvus_client):
        mock_client = MagicMock()
        # Milvus query returns a list of dictionaries directly
        mock_client.query.return_value = [
            {
                "id": 1,
                "url": "http://test1.com",
                "text": "content1",
                "metadata": '{"type": "webpage"}',
            },
            {
                "id": 2,
                "url": "http://test2.com",
                "text": "content2",
                "metadata": '{"type": "webpage"}',
            },
        ]
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        documents = db.list_documents()
        assert len(documents) == 2
        assert documents[0]["url"] == "http://test1.com"
        assert documents[1]["url"] == "http://test2.com"

    @patch("pymilvus.MilvusClient")
    def test_cleanup(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        db._ensure_client()
        db.cleanup()
        mock_client.close.assert_called_once()

    def test_db_type_property(self):
        """Test the db_type property."""
        collections = self._create_test_collections()
        db = MilvusVectorDatabase(collections)
        assert db.db_type == "milvus"
