# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import warnings
from typing import List, Dict, Any

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")

from .vector_db_base import VectorDatabase


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