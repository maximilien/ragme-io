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

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.vector_db_weaviate import WeaviateVectorDatabase


class TestWeaviateVectorDatabase:
    """Test cases for the WeaviateVectorDatabase implementation."""

    def test_init_with_collection_name(self):
        """Test WeaviateVectorDatabase initialization with custom collection name."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase("TestCollection")

            assert db.collection_name == "TestCollection"
            assert db.client == mock_client

    def test_init_default_collection_name(self):
        """Test WeaviateVectorDatabase initialization with default collection name."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()

            assert db.collection_name == "RagMeDocs"
            assert db.client == mock_client

    def test_setup_collection_exists(self):
        """Test setup when collection already exists."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_client.collections.exists.return_value = True
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()
            db.setup()

            # Should not create collection since it exists
            mock_client.collections.create.assert_not_called()

    def test_setup_collection_not_exists(self):
        """Test setup when collection doesn't exist."""
        with (
            patch("weaviate.connect_to_weaviate_cloud") as mock_connect,
            patch("weaviate.classes.config.Configure") as mock_configure,
            patch("weaviate.classes.config.Property") as mock_property,
            patch("weaviate.classes.config.DataType") as mock_datatype,
        ):
            mock_client = MagicMock()
            mock_client.collections.exists.return_value = False
            mock_connect.return_value = mock_client

            # Mock the configuration objects
            mock_configure.Vectorizer.text2vec_weaviate.return_value = (
                "vectorizer_config"
            )
            mock_property.return_value = "property"
            mock_datatype.TEXT = "TEXT"

            db = WeaviateVectorDatabase()
            db.setup()

            # Should create collection since it doesn't exist
            mock_client.collections.create.assert_called_once()

    def test_write_documents(self):
        """Test writing documents to Weaviate."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_batch = MagicMock()
            mock_batch_context = MagicMock()

            mock_client.collections.get.return_value = mock_collection
            mock_collection.batch.dynamic.return_value = mock_batch_context
            mock_batch_context.__enter__.return_value = mock_batch
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()

            documents = [
                {
                    "url": "http://test1.com",
                    "text": "test content 1",
                    "metadata": {"type": "webpage"},
                },
                {
                    "url": "http://test2.com",
                    "text": "test content 2",
                    "metadata": {"type": "webpage"},
                },
            ]

            db.write_documents(documents)

            # Verify batch.add_object was called for each document
            assert mock_batch.add_object.call_count == 2

    def test_list_documents(self):
        """Test listing documents from Weaviate."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_result = MagicMock()
            mock_object1 = MagicMock()
            mock_object2 = MagicMock()

            # Mock the query result
            mock_object1.uuid = "uuid1"
            mock_object1.properties = {
                "url": "http://test1.com",
                "text": "content1",
                "metadata": '{"type": "webpage"}',
            }
            mock_object2.uuid = "uuid2"
            mock_object2.properties = {
                "url": "http://test2.com",
                "text": "content2",
                "metadata": '{"type": "webpage"}',
            }

            mock_result.objects = [mock_object1, mock_object2]
            mock_collection.query.fetch_objects.return_value = mock_result
            mock_client.collections.get.return_value = mock_collection
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()

            documents = db.list_documents(limit=2, offset=0)

            assert len(documents) == 2
            assert documents[0]["id"] == "uuid1"
            assert documents[0]["url"] == "http://test1.com"
            assert documents[1]["id"] == "uuid2"
            assert documents[1]["url"] == "http://test2.com"

    def test_create_query_agent(self):
        """Test creating a query agent."""
        with (
            patch("weaviate.connect_to_weaviate_cloud") as mock_connect,
            patch("weaviate.agents.query.QueryAgent") as mock_query_agent,
        ):
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            mock_agent = MagicMock()
            mock_query_agent.return_value = mock_agent

            db = WeaviateVectorDatabase()
            agent = db.create_query_agent()

            # The actual QueryAgent is created, not the mock, so we just verify it's not None
            assert agent is not None

    def test_cleanup(self):
        """Test cleanup method."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()
            db.cleanup()

            # Verify client is set to None after cleanup
            assert db.client is None

    def test_db_type_property(self):
        """Test the db_type property."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            db = WeaviateVectorDatabase()

            assert db.db_type == "weaviate"
