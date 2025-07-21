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
            self.client.close()


# Factory function to create vector database instances
def create_vector_database(db_type: str = "weaviate", collection_name: str = "RagMeDocs") -> VectorDatabase:
    """
    Factory function to create vector database instances.
    
    Args:
        db_type: Type of vector database ("weaviate", "pinecone", "chroma", etc.)
        collection_name: Name of the collection to use
        
    Returns:
        VectorDatabase instance
    """
    if db_type.lower() == "weaviate":
        return WeaviateVectorDatabase(collection_name)
    # Add other database types here as they are implemented
    # elif db_type.lower() == "pinecone":
    #     return PineconeVectorDatabase(collection_name)
    # elif db_type.lower() == "chroma":
    #     return ChromaVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}") 