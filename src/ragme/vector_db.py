# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import warnings
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    def __init__(self, collection_name: str = "RagMeDocs"):
        """Initialize the vector database with a collection name."""
        self.collection_name = collection_name
    
    @property
    @abstractmethod
    def db_type(self) -> str:
        """Return the type/name of the vector database."""
        pass
    
    @abstractmethod
    def setup(self):
        """Set up the database and create collections if they don't exist."""
        pass
    
    @abstractmethod
    def write_documents(self, documents: List[Dict[str, Any]]):
        """
        Write documents to the vector database.
        
        Args:
            documents: List of documents with 'url', 'text', and 'metadata' fields
        """
        pass
    
    @abstractmethod
    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents from the vector database.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of documents with their properties
        """
        pass
    
    @abstractmethod
    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources and close connections."""
        pass


class WeaviateVectorDatabase(VectorDatabase):
    """Weaviate implementation of the vector database interface."""
    
    def __init__(self, collection_name: str = "RagMeDocs"):
        super().__init__(collection_name)
        self.client = None
        self._create_client()
    
    def _create_client(self):
        """Create the Weaviate client."""
        import os
        import weaviate
        from weaviate.auth import Auth
        
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        weaviate_url = os.getenv("WEAVIATE_URL")
        
        if not weaviate_api_key:
            raise ValueError("WEAVIATE_API_KEY is not set")
        if not weaviate_url:
            raise ValueError("WEAVIATE_URL is not set")
        
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )
    
    def setup(self):
        """Set up Weaviate collection if it doesn't exist."""
        from weaviate.classes.config import Configure, Property, DataType
        
        if not self.client.collections.exists(self.collection_name):
            self.client.collections.create(
                self.collection_name,
                description="A dataset with the contents of RagMe docs and website",
                vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                properties=[
                    Property(name="url", data_type=DataType.TEXT, description="the source URL of the webpage"),
                    Property(name="text", data_type=DataType.TEXT, description="the content of the webpage"),
                    Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
                ]
            )
    
    def write_documents(self, documents: List[Dict[str, Any]]):
        """Write documents to Weaviate."""
        collection = self.client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                metadata_text = json.dumps(doc.get("metadata", {}), ensure_ascii=False)
                batch.add_object(properties={
                    "url": doc.get("url", ""),
                    "text": doc.get("text", ""),
                    "metadata": metadata_text
                })
    
    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List documents from Weaviate."""
        collection = self.client.collections.get(self.collection_name)
        
        # Query the collection
        result = collection.query.fetch_objects(
            limit=limit,
            offset=offset,
            include_vector=False  # Don't include vector data in response
        )
        
        # Process the results
        documents = []
        for obj in result.objects:
            doc = {
                "id": obj.uuid,
                "url": obj.properties.get("url", ""),
                "text": obj.properties.get("text", ""),
                "metadata": obj.properties.get("metadata", "{}")
            }
            
            # Try to parse metadata if it's a JSON string
            try:
                doc["metadata"] = json.loads(doc["metadata"])
            except json.JSONDecodeError:
                pass
                
            documents.append(doc)
            
        return documents
    
    def create_query_agent(self):
        """Create a Weaviate query agent."""
        from weaviate.agents.query import QueryAgent
        return QueryAgent(client=self.client, collections=[self.collection_name])
    
    def cleanup(self):
        """Clean up Weaviate client."""
        if self.client:
            try:
                # Close any open connections
                if hasattr(self.client, 'close'):
                    self.client.close()
                # Also try to close the underlying connection if it exists
                if hasattr(self.client, '_connection') and self.client._connection:
                    if hasattr(self.client._connection, 'close'):
                        try:
                            self.client._connection.close()
                        except TypeError:
                            # Some connection objects don't take arguments
                            pass
            except Exception as e:
                # Log the error but don't raise it to avoid breaking shutdown
                import warnings
                warnings.warn(f"Error during Weaviate cleanup: {e}")
            finally:
                self.client = None

    @property
    def db_type(self) -> str:
        return "weaviate"


class MilvusVectorDatabase(VectorDatabase):
    """Milvus implementation of the vector database interface."""
    def __init__(self, collection_name: str = "RagMeDocs"):
        super().__init__(collection_name)
        self.client = None
        self.collection_name = collection_name
        self._client_created = False

    def _ensure_client(self):
        """Ensure the client is created, handling import-time issues."""
        if not self._client_created:
            self._create_client()
            self._client_created = True
    
    def _create_client(self):
        import os
        import sys
        import warnings
        
        # Temporarily unset MILVUS_URI to prevent pymilvus from auto-connecting during import
        original_milvus_uri = os.environ.pop("MILVUS_URI", None)
        
        try:
            # Import pymilvus after unsetting the environment variable
            from pymilvus import MilvusClient
            from pymilvus.exceptions import MilvusException
            
            milvus_uri = original_milvus_uri or "milvus_demo.db"
            milvus_token = os.getenv("MILVUS_TOKEN", None)
            
            # For local Milvus Lite, try different URI formats
            try:
                if milvus_token:
                    self.client = MilvusClient(uri=milvus_uri, token=milvus_token)
                else:
                    self.client = MilvusClient(uri=milvus_uri)
            except Exception as e:
                # If the URI format fails, try with file:// prefix
                if not milvus_uri.startswith(('http://', 'https://', 'file://')):
                    file_uri = f"file://{milvus_uri}"
                    try:
                        if milvus_token:
                            self.client = MilvusClient(uri=file_uri, token=milvus_token)
                        else:
                            self.client = MilvusClient(uri=file_uri)
                    except Exception as file_e:
                        # If both attempts fail, create a mock client that warns about connection issues
                        warnings.warn(f"Failed to connect to Milvus at {milvus_uri} or {file_uri}. "
                                    f"Milvus operations will be disabled. Error: {file_e}")
                        self.client = None
                else:
                    # For HTTP URIs, if connection fails, create a mock client
                    warnings.warn(f"Failed to connect to Milvus server at {milvus_uri}. "
                                f"Milvus operations will be disabled. Error: {e}")
                    self.client = None
        finally:
            # Restore the environment variable
            if original_milvus_uri:
                os.environ["MILVUS_URI"] = original_milvus_uri

    def setup(self):
        """Set up Milvus collection if it doesn't exist."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Setup skipped.")
            return
            
        # Create collection if it doesn't exist
        if not self.client.has_collection(self.collection_name):
            # Use the correct API for MilvusClient
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=1536,  # Vector dimension
                primary_field_name="id",
                vector_field_name="vector"
            )

    def write_documents(self, documents: List[Dict[str, Any]]):
        """Write documents to Milvus."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Documents not written.")
            return
            
        # Each document should have 'url', 'text', 'metadata', and 'vector' (list of floats)
        data = []
        for i, doc in enumerate(documents):
            if "vector" not in doc:
                raise ValueError("Milvus requires a 'vector' field in each document.")
            data.append({
                "id": i,
                "url": doc.get("url", ""),
                "text": doc.get("text", ""),
                "metadata": json.dumps(doc.get("metadata", {}), ensure_ascii=False),
                "vector": doc["vector"]
            })
        self.client.insert(self.collection_name, data)

    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List documents from Milvus."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Returning empty list.")
            return []
            
        # Query all documents, paginated
        results = self.client.query(
            self.collection_name,
            output_fields=["id", "url", "text", "metadata"],
            limit=limit,
            offset=offset
        )
        
        docs = []
        for doc in results:
            try:
                metadata = json.loads(doc.get("metadata", "{}"))
            except Exception:
                metadata = {}
            docs.append({
                "id": doc.get("id"),
                "url": doc.get("url", ""),
                "text": doc.get("text", ""),
                "metadata": metadata
            })
        return docs

    def create_query_agent(self):
        """Create a query agent for Milvus."""
        # Placeholder: Milvus does not have a built-in query agent like Weaviate
        # You would implement your own search logic here
        return self

    def cleanup(self):
        """Clean up Milvus client."""
        # No explicit cleanup needed for MilvusClient
        if self.client is not None:
            self.client = None

    @property
    def db_type(self) -> str:
        return "milvus"

# Factory function to create vector database instances

def create_vector_database(db_type: str = None, collection_name: str = "RagMeDocs") -> VectorDatabase:
    """
    Factory function to create vector database instances.
    Args:
        db_type: Type of vector database ("weaviate", "milvus", etc.)
        collection_name: Name of the collection to use
    Returns:
        VectorDatabase instance
    """
    import os
    if db_type is None:
        db_type = os.getenv("VECTOR_DB_TYPE", "weaviate")
    if db_type.lower() == "weaviate":
        return WeaviateVectorDatabase(collection_name)
    elif db_type.lower() == "milvus":
        return MilvusVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}") 