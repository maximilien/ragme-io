# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.vector_db import VectorDatabase, WeaviateVectorDatabase, create_vector_database
from src.ragme.vector_db import MilvusVectorDatabase

# Check if pymilvus is available
try:
    import pymilvus
    PYMILVUS_AVAILABLE = True
except ImportError:
    PYMILVUS_AVAILABLE = False


class TestVectorDatabase:
    """Test cases for the VectorDatabase abstract base class."""
    
    def test_vector_database_abstract(self):
        """Test that VectorDatabase is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            VectorDatabase()


class TestWeaviateVectorDatabase:
    """Test cases for the WeaviateVectorDatabase implementation."""
    
    def test_init_with_collection_name(self):
        """Test WeaviateVectorDatabase initialization with custom collection name."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            db = WeaviateVectorDatabase("TestCollection")
            
            assert db.collection_name == "TestCollection"
            assert db.client == mock_client
    
    def test_init_default_collection_name(self):
        """Test WeaviateVectorDatabase initialization with default collection name."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            db = WeaviateVectorDatabase()
            
            assert db.collection_name == "RagMeDocs"
            assert db.client == mock_client
    
    def test_setup_collection_exists(self):
        """Test setup when collection already exists."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
            mock_client = MagicMock()
            mock_client.collections.exists.return_value = True
            mock_connect.return_value = mock_client
            
            db = WeaviateVectorDatabase()
            db.setup()
            
            # Should not create collection since it exists
            mock_client.collections.create.assert_not_called()
    
    def test_setup_collection_not_exists(self):
        """Test setup when collection doesn't exist."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect, \
             patch('weaviate.classes.config.Configure') as mock_configure, \
             patch('weaviate.classes.config.Property') as mock_property, \
             patch('weaviate.classes.config.DataType') as mock_datatype:
            
            mock_client = MagicMock()
            mock_client.collections.exists.return_value = False
            mock_connect.return_value = mock_client
            
            # Mock the configuration objects
            mock_configure.Vectorizer.text2vec_weaviate.return_value = "vectorizer_config"
            mock_property.return_value = "property"
            mock_datatype.TEXT = "TEXT"
            
            db = WeaviateVectorDatabase()
            db.setup()
            
            # Should create collection since it doesn't exist
            mock_client.collections.create.assert_called_once()
    
    def test_write_documents(self):
        """Test writing documents to Weaviate."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
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
                {"url": "http://test1.com", "text": "test content 1", "metadata": {"type": "webpage"}},
                {"url": "http://test2.com", "text": "test content 2", "metadata": {"type": "webpage"}}
            ]
            
            db.write_documents(documents)
            
            # Verify batch.add_object was called for each document
            assert mock_batch.add_object.call_count == 2
    
    def test_list_documents(self):
        """Test listing documents from Weaviate."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_result = MagicMock()
            mock_object1 = MagicMock()
            mock_object2 = MagicMock()
            
            # Mock the query result
            mock_object1.uuid = "uuid1"
            mock_object1.properties = {"url": "http://test1.com", "text": "content1", "metadata": '{"type": "webpage"}'}
            mock_object2.uuid = "uuid2"
            mock_object2.properties = {"url": "http://test2.com", "text": "content2", "metadata": '{"type": "webpage"}'}
            
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
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect, \
             patch('src.ragme.vector_db.WeaviateVectorDatabase.create_query_agent') as mock_create_agent:
            
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            mock_agent = MagicMock()
            mock_create_agent.return_value = mock_agent
            
            db = WeaviateVectorDatabase()
            agent = db.create_query_agent()
            
            assert agent == mock_agent
    
    def test_cleanup(self):
        """Test cleanup method."""
        with patch('weaviate.connect_to_weaviate_cloud') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            db = WeaviateVectorDatabase()
            db.cleanup()
            
            mock_client.close.assert_called_once()


# ---------------- MilvusVectorDatabase Tests ----------------
@pytest.mark.skipif(not PYMILVUS_AVAILABLE, reason="pymilvus not available")
class TestMilvusVectorDatabase:
    """Test cases for the MilvusVectorDatabase implementation."""

    @patch('pymilvus.MilvusClient')
    def test_init_with_collection_name(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase("TestCollection")
        assert db.collection_name == "TestCollection"
        assert db.client == mock_client

    @patch('pymilvus.MilvusClient')
    def test_setup_collection_exists(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        db.setup()
        mock_client.create_collection.assert_not_called()

    @patch('pymilvus.MilvusClient')
    def test_setup_collection_not_exists(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        db.setup()
        mock_client.create_collection.assert_called_once()

    @patch('pymilvus.MilvusClient')
    def test_write_documents(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        documents = [
            {"url": "http://test1.com", "text": "test content 1", "metadata": {"type": "webpage"}, "vector": [0.1]*768},
            {"url": "http://test2.com", "text": "test content 2", "metadata": {"type": "webpage"}, "vector": [0.2]*768}
        ]
        db.write_documents(documents)
        assert mock_client.insert.called

    @patch('pymilvus.MilvusClient')
    def test_write_documents_missing_vector(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        documents = [
            {"url": "http://test1.com", "text": "test content 1", "metadata": {"type": "webpage"}}
        ]
        with pytest.raises(ValueError, match="Milvus requires a 'vector' field in each document."):
            db.write_documents(documents)

    @patch('pymilvus.MilvusClient')
    def test_list_documents(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_client.query.return_value = {
            "data": [
                {"id": 1, "url": "http://test1.com", "text": "content1", "metadata": '{"type": "webpage"}'},
                {"id": 2, "url": "http://test2.com", "text": "content2", "metadata": '{"type": "webpage"}'}
            ]
        }
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        docs = db.list_documents(limit=2)
        assert len(docs) == 2
        assert docs[0]["id"] == 1
        assert docs[0]["url"] == "http://test1.com"

    @patch('pymilvus.MilvusClient')
    def test_cleanup(self, mock_milvus_client):
        mock_client = MagicMock()
        mock_milvus_client.return_value = mock_client
        db = MilvusVectorDatabase()
        db.cleanup()
        assert db.client is None


class TestCreateVectorDatabase:
    """Test cases for the create_vector_database factory function."""
    
    def test_create_weaviate_database(self):
        """Test creating a Weaviate vector database."""
        with patch('src.ragme.vector_db.WeaviateVectorDatabase') as mock_weaviate_db:
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance
            
            db = create_vector_database("weaviate", "TestCollection")
            
            mock_weaviate_db.assert_called_once_with("TestCollection")
            assert db == mock_instance

    def test_create_milvus_database(self):
        """Test creating a Milvus vector database."""
        with patch('src.ragme.vector_db.MilvusVectorDatabase') as mock_milvus_db:
            mock_instance = MagicMock()
            mock_milvus_db.return_value = mock_instance
            db = create_vector_database("milvus", "TestCollection")
            mock_milvus_db.assert_called_once_with("TestCollection")
            assert db == mock_instance
    
    def test_create_unsupported_database(self):
        """Test creating an unsupported database type."""
        with pytest.raises(ValueError, match="Unsupported vector database type: invalid"):
            create_vector_database("invalid")
    
    def test_create_database_case_insensitive(self):
        """Test that database type is case insensitive."""
        with patch('src.ragme.vector_db.WeaviateVectorDatabase') as mock_weaviate_db:
            mock_instance = MagicMock()
            mock_weaviate_db.return_value = mock_instance
            
            db = create_vector_database("WEAVIATE", "TestCollection")
            
            mock_weaviate_db.assert_called_once_with("TestCollection")
            assert db == mock_instance 