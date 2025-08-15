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

from src.ragme.vdbs.vector_db_base import CollectionConfig
from src.ragme.vdbs.vector_db_weaviate import WeaviateVectorDatabase


class TestWeaviateVectorDatabase:
    """Test cases for the WeaviateVectorDatabase implementation."""

    def _create_test_collections(self):
        """Create test collection configurations."""
        return [CollectionConfig("TestCollection", "text")]

    def test_init_with_collection_name(self):
        """Test WeaviateVectorDatabase initialization with custom collection name."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)

            assert db.text_collection.name == "TestCollection"
            assert db.text_collection.type == "text"
            assert db.client == mock_client

    def test_init_default_collection_name(self):
        """Test WeaviateVectorDatabase initialization with default collection name."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)

            assert db.text_collection.name == "TestCollection"
            assert db.text_collection.type == "text"
            assert db.client == mock_client

    def test_setup_collection_exists(self):
        """Test setup when collection already exists."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_client.collections.exists.return_value = True
            mock_connect.return_value = mock_client

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
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

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
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

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
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

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
            documents = db.list_documents()
            assert len(documents) == 2
            assert documents[0]["url"] == "http://test1.com"
            assert documents[1]["url"] == "http://test2.com"

    def test_create_query_agent(self):
        """Test creating a query agent."""
        with (
            patch("weaviate.connect_to_weaviate_cloud") as mock_connect,
            patch("src.ragme.agents.query_agent.QueryAgent") as mock_query_agent,
        ):
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            mock_agent = MagicMock()
            mock_query_agent.return_value = mock_agent

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
            agent = db.create_query_agent()

            assert agent == mock_agent

    def test_cleanup(self):
        """Test cleanup method."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
            db.cleanup()

            mock_client.close.assert_called_once()

    def test_db_type_property(self):
        """Test the db_type property."""
        with patch("weaviate.connect_to_weaviate_cloud") as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client

            collections = self._create_test_collections()
            db = WeaviateVectorDatabase(collections)
            assert db.db_type == "weaviate"
