# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import warnings
from typing import Any

from .vector_db_base import VectorDatabase

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

        # Add timeout configuration to prevent hanging connections
        try:
            # Try to use timeout configuration if available
            try:
                from weaviate.classes.config import Config

                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=weaviate_url,
                    auth_credentials=Auth.api_key(weaviate_api_key),
                    additional_config=Config(
                        timeout=Config.Timeout(
                            init=10,  # 10 second timeout for initialization
                            query=30,  # 30 second timeout for queries
                            insert=30,  # 30 second timeout for inserts
                        )
                    ),
                )
            except ImportError:
                # Fallback to basic connection if Config is not available
                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=weaviate_url,
                    auth_credentials=Auth.api_key(weaviate_api_key),
                )
        except Exception as e:
            # Provide more helpful error message
            raise ConnectionError(
                f"Failed to connect to Weaviate at {weaviate_url}: {str(e)}"
            ) from e

    def setup(self):
        """Set up Weaviate collection if it doesn't exist."""
        from weaviate.classes.config import Configure, DataType, Property

        if not self.client.collections.exists(self.collection_name):
            self.client.collections.create(
                self.collection_name,
                description="A dataset with the contents of RagMe docs and website",
                vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                properties=[
                    Property(
                        name="url",
                        data_type=DataType.TEXT,
                        description="the source URL of the webpage",
                    ),
                    Property(
                        name="text",
                        data_type=DataType.TEXT,
                        description="the content of the webpage",
                    ),
                    Property(
                        name="metadata",
                        data_type=DataType.TEXT,
                        description="additional metadata in JSON format",
                    ),
                ],
            )

    def write_documents(self, documents: list[dict[str, Any]]):
        """Write documents to Weaviate."""
        collection = self.client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                metadata_text = json.dumps(doc.get("metadata", {}), ensure_ascii=False)
                batch.add_object(
                    properties={
                        "url": doc.get("url", ""),
                        "text": doc.get("text", ""),
                        "metadata": metadata_text,
                    }
                )

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List documents from Weaviate."""
        collection = self.client.collections.get(self.collection_name)

        # Query the collection
        result = collection.query.fetch_objects(
            limit=limit,
            offset=offset,
            include_vector=False,  # Don't include vector data in response
        )

        # Process the results
        documents = []
        for obj in result.objects:
            doc = {
                "id": obj.uuid,
                "url": obj.properties.get("url", ""),
                "text": obj.properties.get("text", ""),
                "metadata": obj.properties.get("metadata", "{}"),
            }

            # Try to parse metadata if it's a JSON string
            try:
                doc["metadata"] = json.loads(doc["metadata"])
            except json.JSONDecodeError:
                pass

            documents.append(doc)

        # Sort by creation time (most recent first) - Weaviate doesn't support sorting in query
        # So we'll sort the results after fetching
        documents.sort(
            key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
        )

        return documents

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from Weaviate by ID."""
        try:
            collection = self.client.collections.get(self.collection_name)
            collection.data.delete_by_id(document_id)
            return True
        except Exception as e:
            warnings.warn(f"Failed to delete document {document_id}: {e}")
            return False

    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """Find a document by its URL."""
        try:
            collection = self.client.collections.get(self.collection_name)

            # Get all documents and search manually since the where clause doesn't work
            all_docs = collection.query.fetch_objects(
                limit=100,  # Get more documents to search through
                include_vector=False,
            )

            # Search through all documents for a matching URL
            for obj in all_docs.objects:
                stored_url = obj.properties.get("url", "")

                # Try exact match first
                if stored_url == url:
                    doc = {
                        "id": obj.uuid,
                        "url": stored_url,
                        "text": obj.properties.get("text", ""),
                        "metadata": obj.properties.get("metadata", "{}"),
                    }

                    # Try to parse metadata if it's a JSON string
                    try:
                        doc["metadata"] = json.loads(doc["metadata"])
                    except json.JSONDecodeError:
                        pass

                    return doc

                # Try matching without fragments (remove everything after #)
                stored_url_base = stored_url.split("#")[0]
                url_base = url.split("#")[0]

                if stored_url_base == url_base:
                    doc = {
                        "id": obj.uuid,
                        "url": stored_url,
                        "text": obj.properties.get("text", ""),
                        "metadata": obj.properties.get("metadata", "{}"),
                    }

                    # Try to parse metadata if it's a JSON string
                    try:
                        doc["metadata"] = json.loads(doc["metadata"])
                    except json.JSONDecodeError:
                        pass

                    return doc

                # Try matching filename only (for file:// URLs)
                if stored_url.startswith("file://"):
                    # Extract filename from stored URL (remove file:// and fragments)
                    stored_filename = stored_url.replace("file://", "").split("#")[0]
                    # If user provided just filename, try to match
                    if stored_filename == url or stored_filename.endswith("/" + url):
                        doc = {
                            "id": obj.uuid,
                            "url": stored_url,
                            "text": obj.properties.get("text", ""),
                            "metadata": obj.properties.get("metadata", "{}"),
                        }

                        # Try to parse metadata if it's a JSON string
                        try:
                            doc["metadata"] = json.loads(doc["metadata"])
                        except json.JSONDecodeError:
                            pass

                        return doc

            return None

        except Exception as e:
            warnings.warn(f"Failed to find document by URL {url}: {e}")
            return None

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for documents using Weaviate's vector similarity search.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            List of documents sorted by relevance
        """
        try:
            collection = self.client.collections.get(self.collection_name)

            # Use Weaviate's near_text search for vector similarity
            result = collection.query.near_text(
                query=query,
                limit=limit,
                include_vector=False,
            )

            documents = []
            for obj in result.objects:
                doc = {
                    "id": obj.uuid,
                    "url": obj.properties.get("url", ""),
                    "text": obj.properties.get("text", ""),
                    "metadata": obj.properties.get("metadata", "{}"),
                }

                # Try to parse metadata if it's a JSON string
                try:
                    doc["metadata"] = json.loads(doc["metadata"])
                except json.JSONDecodeError:
                    pass

                documents.append(doc)

            return documents

        except Exception as e:
            warnings.warn(f"Failed to perform vector search for query '{query}': {e}")
            # Fallback to simple keyword matching if vector search fails
            return self._fallback_keyword_search(query, limit)

    def _fallback_keyword_search(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Fallback to simple keyword matching if vector search fails.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            List of documents sorted by relevance
        """
        try:
            # Get all documents and perform keyword matching
            documents = self.list_documents(limit=100, offset=0)

            query_lower = query.lower()
            query_words = query_lower.split()
            relevant_docs = []

            for doc in documents:
                text = doc.get("text", "").lower()
                url = doc.get("url", "").lower()
                metadata = doc.get("metadata", {})
                metadata_text = str(metadata).lower()

                # Count how many query words match
                matches = 0
                for word in query_words:
                    if word in text or word in url or word in metadata_text:
                        matches += 1

                # If at least one word matches, consider it relevant
                if matches > 0:
                    relevant_docs.append(
                        {"doc": doc, "matches": matches, "text_length": len(text)}
                    )

            if relevant_docs:
                # Sort by relevance (more matches first, then by text length)
                relevant_docs.sort(key=lambda x: (-x["matches"], -x["text_length"]))

                # Return the top results
                return [item["doc"] for item in relevant_docs[:limit]]

            return []

        except Exception as e:
            warnings.warn(f"Fallback keyword search also failed: {e}")
            return []

    def create_query_agent(self):
        """Create a Weaviate query agent."""
        from weaviate.agents.query import QueryAgent

        return QueryAgent(client=self.client, collections=[self.collection_name])

    def cleanup(self):
        """Clean up Weaviate client."""
        if self.client:
            try:
                # Close any open connections
                if hasattr(self.client, "close"):
                    self.client.close()
                # Also try to close the underlying connection if it exists
                if hasattr(self.client, "_connection") and self.client._connection:
                    if hasattr(self.client._connection, "close"):
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
