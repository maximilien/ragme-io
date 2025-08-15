# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.vdbs.vector_db_base import CollectionConfig, VectorDatabase
from src.ragme.vdbs.vector_db_milvus import MilvusVectorDatabase
from src.ragme.vdbs.vector_db_weaviate import WeaviateVectorDatabase
from src.ragme.vdbs.vector_db_weaviate_local import WeaviateLocalVectorDatabase


class TestVectorDatabaseImageMethods:
    """Test the new image methods added to vector databases."""

    def _create_test_collections(self):
        """Create test collection configurations."""
        return [
            CollectionConfig("TestTextCollection", "text"),
            CollectionConfig("TestImageCollection", "image"),
        ]

    def test_collection_config_initialization(self):
        """Test CollectionConfig initialization."""
        config = CollectionConfig("test_collection", "text")
        assert config.name == "test_collection"
        assert config.type == "text"

    def test_vector_database_collection_setup(self):
        """Test that VectorDatabase properly sets up text and image collections."""
        collections = self._create_test_collections()

        # Create a mock VDB class that inherits from VectorDatabase
        class MockVectorDatabase(VectorDatabase):
            @property
            def db_type(self) -> str:
                return "mock"

            def setup(self):
                pass

            def write_documents(self, documents):
                pass

            def list_documents(self, limit=10, offset=0):
                return []

            def delete_document(self, document_id):
                return True

            def find_document_by_url(self, url):
                return None

            def search(self, query, limit=5):
                return []

            def search_text_collection(self, query, limit=5):
                return []

            def search_image_collection(self, query, limit=5):
                return []

            def create_query_agent(self):
                return Mock()

            def count_documents(self, date_filter="all"):
                return 0

            def count_images(self, date_filter="all"):
                return 0

            def cleanup(self):
                pass

            def write_images(self, images):
                pass

            def list_images(self, limit=10, offset=0):
                return []

            def delete_image(self, image_id):
                return True

            def find_image_by_url(self, url):
                return None

            def supports_images(self):
                return True

        vdb = MockVectorDatabase(collections)

        assert vdb.has_text_collection() is True
        assert vdb.has_image_collection() is True
        assert vdb.get_text_collection_name() == "TestTextCollection"
        assert vdb.get_image_collection_name() == "TestImageCollection"
        assert vdb.text_collection.type == "text"
        assert vdb.image_collection.type == "image"

    def test_vector_database_text_only_setup(self):
        """Test VectorDatabase with only text collection."""
        collections = [CollectionConfig("TestTextCollection", "text")]

        class MockVectorDatabase(VectorDatabase):
            @property
            def db_type(self) -> str:
                return "mock"

            def setup(self):
                pass

            def write_documents(self, documents):
                pass

            def list_documents(self, limit=10, offset=0):
                return []

            def delete_document(self, document_id):
                return True

            def find_document_by_url(self, url):
                return None

            def search(self, query, limit=5):
                return []

            def search_text_collection(self, query, limit=5):
                return []

            def search_image_collection(self, query, limit=5):
                return []

            def create_query_agent(self):
                return Mock()

            def count_documents(self, date_filter="all"):
                return 0

            def count_images(self, date_filter="all"):
                return 0

            def cleanup(self):
                pass

            def write_images(self, images):
                pass

            def list_images(self, limit=10, offset=0):
                return []

            def delete_image(self, image_id):
                return True

            def find_image_by_url(self, url):
                return None

            def supports_images(self):
                return False

        vdb = MockVectorDatabase(collections)

        assert vdb.has_text_collection() is True
        assert vdb.has_image_collection() is False
        assert vdb.get_text_collection_name() == "TestTextCollection"
        assert vdb.get_image_collection_name() is None


class TestWeaviateImageMethods:
    """Test image methods in Weaviate implementation."""

    def _create_test_collections(self):
        """Create test collection configurations."""
        return [
            CollectionConfig("TestTextCollection", "text"),
            CollectionConfig("TestImageCollection", "image"),
        ]

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_list_images(self, mock_connect):
        """Test list_images method in Weaviate implementation."""
        collections = self._create_test_collections()

        # Mock Weaviate client
        mock_client = Mock()
        mock_collection = Mock()
        mock_response = Mock()
        mock_response.objects = [
            Mock(
                uuid="img1",
                properties={
                    "url": "https://example.com/image1.jpg",
                    "text": "Image 1 description",
                    "metadata": '{"filename": "image1.jpg"}',
                },
            )
        ]

        mock_collection.query.fetch_objects.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection

        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.list_images(limit=5, offset=0)

        assert len(result) == 1
        assert result[0]["id"] == "img1"
        assert result[0]["url"] == "https://example.com/image1.jpg"
        assert result[0]["text"] == "Image 1 description"
        assert result[0]["metadata"]["filename"] == "image1.jpg"

        mock_collection.query.fetch_objects.assert_called_once_with(
            limit=5, offset=0, include_vector=False
        )

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_list_images_no_collection(self, mock_connect):
        """Test list_images when no image collection is configured."""
        collections = [CollectionConfig("TestTextCollection", "text")]

        mock_client = Mock()
        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.list_images()

        assert result == []
        mock_client.collections.get.assert_not_called()

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_delete_image(self, mock_connect):
        """Test delete_image method in Weaviate implementation."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_collection = Mock()
        mock_client.collections.get.return_value = mock_collection

        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.delete_image("img1")

        assert result is True
        mock_collection.data.delete_by_id.assert_called_once_with("img1")

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_delete_image_exception(self, mock_connect):
        """Test delete_image when an exception occurs."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.data.delete_by_id.side_effect = Exception("Delete failed")
        mock_client.collections.get.return_value = mock_collection

        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.delete_image("img1")

        assert result is False

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_find_image_by_url(self, mock_connect):
        """Test find_image_by_url method in Weaviate implementation."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_collection = Mock()
        mock_response = Mock()
        mock_response.objects = [
            Mock(
                uuid="img1",
                properties={
                    "url": "https://example.com/image1.jpg",
                    "text": "Image 1 description",
                    "metadata": '{"filename": "image1.jpg"}',
                },
            )
        ]

        mock_collection.query.fetch_objects.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection

        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.find_image_by_url("https://example.com/image1.jpg")

        assert result is not None
        assert result["id"] == "img1"
        assert result["url"] == "https://example.com/image1.jpg"

        mock_collection.query.fetch_objects.assert_called_once_with(
            limit=1000,
            include_vector=False,
        )

    @patch("weaviate.connect_to_weaviate_cloud")
    def test_weaviate_find_image_by_url_not_found(self, mock_connect):
        """Test find_image_by_url when image is not found."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_collection = Mock()
        mock_response = Mock()
        mock_response.objects = []

        mock_collection.query.fetch_objects.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection

        mock_connect.return_value = mock_client

        vdb = WeaviateVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.find_image_by_url("https://example.com/nonexistent.jpg")

        assert result is None


class TestMilvusImageMethods:
    """Test image methods in Milvus implementation."""

    def _create_test_collections(self):
        """Create test collection configurations."""
        return [
            CollectionConfig("TestTextCollection", "text"),
            CollectionConfig("TestImageCollection", "image"),
        ]

    @patch("pymilvus.MilvusClient")
    def test_milvus_list_images(self, mock_milvus_client):
        """Test list_images method in Milvus implementation."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_response = [
            {
                "id": "img1",
                "url": "https://example.com/image1.jpg",
                "text": "Image 1 description",
                "metadata": '{"filename": "image1.jpg"}',
            }
        ]
        mock_client.query.return_value = mock_response
        mock_milvus_client.return_value = mock_client

        vdb = MilvusVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.list_images(limit=5, offset=0)

        assert len(result) == 1
        assert result[0]["id"] == "img1"
        assert result[0]["url"] == "https://example.com/image1.jpg"
        assert result[0]["text"] == "Image 1 description"
        assert result[0]["metadata"]["filename"] == "image1.jpg"

        mock_client.query.assert_called_once_with(
            collection_name="TestImageCollection",
            filter="",
            output_fields=["id", "url", "text", "metadata"],
            limit=5,
            offset=0,
        )

    @patch("pymilvus.MilvusClient")
    def test_milvus_delete_image(self, mock_milvus_client):
        """Test delete_image method in Milvus implementation."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_milvus_client.return_value = mock_client

        vdb = MilvusVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.delete_image("img1")

        assert result is True
        mock_client.delete.assert_called_once_with(
            collection_name="TestImageCollection", pks=["img1"]
        )

    @patch("pymilvus.MilvusClient")
    def test_milvus_find_image_by_url(self, mock_milvus_client):
        """Test find_image_by_url method in Milvus implementation."""
        collections = self._create_test_collections()

        mock_client = Mock()
        mock_response = [
            {
                "id": "img1",
                "url": "https://example.com/image1.jpg",
                "text": "Image 1 description",
                "metadata": '{"filename": "image1.jpg"}',
            }
        ]
        mock_client.query.return_value = mock_response
        mock_milvus_client.return_value = mock_client

        vdb = MilvusVectorDatabase(collections)
        vdb.client = mock_client

        result = vdb.find_image_by_url("https://example.com/image1.jpg")

        assert result is not None
        assert result["id"] == "img1"
        assert result["url"] == "https://example.com/image1.jpg"

        mock_client.query.assert_called_once_with(
            collection_name="TestImageCollection",
            filter='url == "https://example.com/image1.jpg"',
            output_fields=["id", "url", "text", "metadata"],
            limit=1,
        )


class TestQueryAgentRefactoring:
    """Test the QueryAgent refactoring changes."""

    def test_query_agent_accepts_vector_db_directly(self):
        """Test that QueryAgent can be initialized with a vector_db directly."""
        from src.ragme.agents.query_agent import QueryAgent

        # Create a mock vector_db
        mock_vector_db = Mock()
        mock_vector_db.has_text_collection.return_value = True
        mock_vector_db.has_image_collection.return_value = False

        # Test that QueryAgent can be created with vector_db directly
        agent = QueryAgent(mock_vector_db)

        assert agent.vector_db == mock_vector_db
        assert hasattr(agent, "llm")
        assert hasattr(agent, "top_k")

    @pytest.mark.asyncio
    @patch("src.ragme.agents.query_agent.OpenAI")
    async def test_query_agent_uses_vector_db_methods(self, mock_openai):
        """Test that QueryAgent uses vector_db methods correctly."""
        from src.ragme.agents.query_agent import QueryAgent

        # Create a mock vector_db
        mock_vector_db = Mock()
        mock_vector_db.has_text_collection.return_value = True
        mock_vector_db.has_image_collection.return_value = False
        mock_vector_db.search_text_collection.return_value = []
        mock_vector_db.search_image_collection.return_value = []

        # Mock LLM
        mock_llm = Mock()
        mock_openai.return_value = mock_llm

        agent = QueryAgent(mock_vector_db)

        # Test that the agent calls the correct vector_db methods
        await agent.run("test query")

        mock_vector_db.has_text_collection.assert_called_once()
        mock_vector_db.has_image_collection.assert_called_once()
        mock_vector_db.search_text_collection.assert_called_once_with(
            "test query", limit=5
        )


class TestVDBFactoryRefactoring:
    """Test the VDB factory refactoring changes."""

    @patch("src.ragme.vdbs.vector_db_factory.config")
    def test_factory_creates_vdb_with_collections(self, mock_config):
        """Test that factory creates VDB with CollectionConfig objects."""
        from src.ragme.vdbs.vector_db_factory import create_vector_database

        # Mock config
        mock_config.get_database_config.return_value = {
            "type": "weaviate",
            "url": "test_url",
            "api_key": "test_key",
        }
        mock_config.get_collections_config.return_value = [
            {"name": "TestTextCollection", "type": "text"},
            {"name": "TestImageCollection", "type": "image"},
        ]

        with patch(
            "src.ragme.vdbs.vector_db_factory.WeaviateVectorDatabase"
        ) as mock_weaviate:
            mock_instance = Mock()
            mock_weaviate.return_value = mock_instance

            create_vector_database("weaviate")

            # Check that WeaviateVectorDatabase was called with CollectionConfig objects
            mock_weaviate.assert_called_once()
            args, kwargs = mock_weaviate.call_args
            collections = args[0]  # First argument should be collections list

            assert len(collections) == 2
            assert collections[0].name == "TestTextCollection"
            assert collections[0].type == "text"
            assert collections[1].name == "TestImageCollection"
            assert collections[1].type == "image"
