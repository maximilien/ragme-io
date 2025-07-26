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

from src.ragme.vector_db_milvus import MilvusVectorDatabase

# Check if pymilvus is available
try:
    import pymilvus

    PYMILVUS_AVAILABLE = True
except ImportError:
    PYMILVUS_AVAILABLE = False


@pytest.mark.skipif(not PYMILVUS_AVAILABLE, reason="pymilvus not available")
class TestMilvusVectorDatabase:
    """Test cases for the MilvusVectorDatabase implementation."""

    @patch("pymilvus.MilvusClient")
    def test_init_with_collection_name(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase("TestCollection")
        assert db.collection_name == "TestCollection"
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
        db = MilvusVectorDatabase()
        db.setup()
        mock_client.create_collection.assert_not_called()

    @patch("pymilvus.MilvusClient")
    def test_setup_collection_not_exists(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        db.setup()
        mock_client.create_collection.assert_called_once()

    @patch("pymilvus.MilvusClient")
    def test_write_documents(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
                "vector": [0.1] * 768,
            },
            {
                "url": "http://test2.com",
                "text": "test content 2",
                "metadata": {"type": "webpage"},
                "vector": [0.2] * 768,
            },
        ]
        db.write_documents(documents)
        assert mock_client.insert.called

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

        db = MilvusVectorDatabase()
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
            }
        ]
        # With automatic vector generation, this should work without raising an error
        # The vector will be generated automatically
        db.write_documents(documents)
        assert mock_client.insert.called

    @patch("pymilvus.MilvusClient")
    def test_write_documents_missing_vector_generation_fails(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        documents = [
            {
                "url": "http://test1.com",
                "text": "test content 1",
                "metadata": {"type": "webpage"},
            }
        ]
        # Mock the OpenAI client to raise an exception
        with patch("openai.OpenAI") as mock_openai:
            mock_openai.side_effect = Exception("API key invalid")
            # Should continue without inserting documents since vector generation failed
            db.write_documents(documents)
            # Since vector generation failed, no documents should be inserted
            mock_client.insert.assert_not_called()

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
        db = MilvusVectorDatabase()
        docs = db.list_documents(limit=2)
        assert len(docs) == 2
        assert docs[0]["id"] == 1
        assert docs[0]["url"] == "http://test1.com"

    @patch("pymilvus.MilvusClient")
    def test_cleanup(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        db.cleanup()
        assert db.client is None

    def test_db_type_property(self):
        """Test the db_type property."""
        db = MilvusVectorDatabase()
        assert db.db_type == "milvus"
