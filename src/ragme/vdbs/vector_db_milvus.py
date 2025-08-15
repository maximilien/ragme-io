# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import os
import warnings
from typing import Any

from .vector_db_base import CollectionConfig, VectorDatabase

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


class MilvusVectorDatabase(VectorDatabase):
    """Milvus implementation of the vector database interface."""

    def __init__(self, collections: list[CollectionConfig]):
        super().__init__(collections)
        self.client = None
        self._client_created = False

    def _ensure_client(self):
        """Ensure the client is created, handling import-time issues."""
        if not self._client_created:
            self._create_client()
            self._client_created = True

    def _create_client(self):
        import warnings

        # Temporarily unset MILVUS_URI to prevent pymilvus from auto-connecting during import
        original_milvus_uri = os.environ.pop("MILVUS_URI", None)

        try:
            # Import pymilvus after unsetting the environment variable
            from pymilvus import MilvusClient

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
                if not milvus_uri.startswith(("http://", "https://", "file://")):
                    file_uri = f"file://{milvus_uri}"
                    try:
                        if milvus_token:
                            self.client = MilvusClient(uri=file_uri, token=milvus_token)
                        else:
                            self.client = MilvusClient(uri=file_uri)
                    except Exception as file_e:
                        # If both attempts fail, create a mock client that warns about connection issues
                        warnings.warn(
                            f"Failed to connect to Milvus at {milvus_uri} or {file_uri}. "
                            f"Milvus operations will be disabled. Error: {file_e}"
                        )
                        self.client = None
                else:
                    # For HTTP URIs, if connection fails, create a mock client
                    warnings.warn(
                        f"Failed to connect to Milvus server at {milvus_uri}. "
                        f"Milvus operations will be disabled. Error: {e}"
                    )
                    self.client = None
        finally:
            # Restore the environment variable
            if original_milvus_uri:
                os.environ["MILVUS_URI"] = original_milvus_uri

    def setup(self):
        """Set up Milvus collections if they don't exist."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Setup skipped.")
            return

        for collection in self.collections:
            # Create collection if it doesn't exist
            if not self.client.has_collection(collection.name):
                # Use the correct API for MilvusClient
                self.client.create_collection(
                    collection_name=collection.name,
                    dimension=1536,  # Vector dimension
                    primary_field_name="id",
                    vector_field_name="vector",
                    metric_type="COSINE",
                )

    @property
    def db_type(self) -> str:
        """Return the type/name of the vector database."""
        return "milvus"

    def write_documents(self, documents: list[dict[str, Any]]):
        """Write documents to the text collection."""
        if not self.has_text_collection():
            raise ValueError("No text collection configured for this VDB")

        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Document writing skipped.")
            return

        # Prepare data for insertion
        data = []
        for doc in documents:
            # Generate embeddings for text
            embedding = self._get_text_embedding(doc.get("text", ""))

            data.append(
                {
                    "id": doc.get("id", f"doc_{len(data)}"),
                    "url": doc.get("url", ""),
                    "text": doc.get("text", ""),
                    "metadata": json.dumps(doc.get("metadata", {}), ensure_ascii=False),
                    "vector": embedding,
                }
            )

        # Insert into text collection
        self.client.insert(collection_name=self.text_collection.name, data=data)

    def write_images(self, images: list[dict[str, Any]]):
        """Write images to the image collection."""
        if not self.has_image_collection():
            raise ValueError("No image collection configured for this VDB")

        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Image writing skipped.")
            return

        # Prepare data for insertion
        data = []
        for img in images:
            # For images, we'll use metadata embedding since Milvus doesn't have native image support
            metadata = img.get("metadata", {})
            metadata_text = json.dumps(metadata, ensure_ascii=False)
            embedding = self._get_text_embedding(metadata_text)

            data.append(
                {
                    "id": img.get("id", f"img_{len(data)}"),
                    "url": img.get("url", ""),
                    "text": f"Image: {img.get('url', 'unknown')}",
                    "metadata": metadata_text,
                    "vector": embedding,
                }
            )

        # Insert into image collection
        self.client.insert(collection_name=self.image_collection.name, data=data)

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List documents from the text collection."""
        if not self.has_text_collection():
            return []

        self._ensure_client()
        if self.client is None:
            return []

        try:
            # Get documents from text collection
            response = self.client.query(
                collection_name=self.text_collection.name,
                filter="",
                output_fields=["id", "url", "text", "metadata"],
                limit=limit,
                offset=offset,
            )

            return self._convert_milvus_response(response)
        except Exception as e:
            warnings.warn(f"Error listing documents from Milvus: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the text collection by ID."""
        if not self.has_text_collection():
            return False

        self._ensure_client()
        if self.client is None:
            return False

        try:
            self.client.delete(
                collection_name=self.text_collection.name, pks=[document_id]
            )
            return True
        except Exception:
            return False

    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """Find a document by its URL in the text collection."""
        if not self.has_text_collection():
            return None

        self._ensure_client()
        if self.client is None:
            return None

        try:
            response = self.client.query(
                collection_name=self.text_collection.name,
                filter=f'url == "{url}"',
                output_fields=["id", "url", "text", "metadata"],
                limit=1,
            )

            results = self._convert_milvus_response(response)
            return results[0] if results else None
        except Exception:
            return None

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search both text and image collections in parallel."""
        results = []

        # Search text collection if available
        if self.has_text_collection():
            text_results = self.search_text_collection(query, limit)
            results.extend(text_results)

        # Search image collection if available
        if self.has_image_collection():
            image_results = self.search_image_collection(query, limit)
            results.extend(image_results)

        # Sort by score if available
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return results[:limit]

    def search_text_collection(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search only the text collection."""
        if not self.has_text_collection():
            return []

        self._ensure_client()
        if self.client is None:
            return []

        try:
            # Generate embedding for query
            query_embedding = self._get_text_embedding(query)

            # Search text collection
            response = self.client.search(
                collection_name=self.text_collection.name,
                data=[query_embedding],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=limit,
                output_fields=["id", "url", "text", "metadata"],
            )

            return self._convert_milvus_search_response(response)
        except Exception as e:
            warnings.warn(f"Error searching text collection in Milvus: {e}")
            return []

    def search_image_collection(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search only the image collection using metadata."""
        if not self.has_image_collection():
            return []

        self._ensure_client()
        if self.client is None:
            return []

        try:
            # Generate embedding for query
            query_embedding = self._get_text_embedding(query)

            # Search image collection
            response = self.client.search(
                collection_name=self.image_collection.name,
                data=[query_embedding],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"nprobe": 10}},
                limit=limit,
                output_fields=["id", "url", "text", "metadata"],
            )

            return self._convert_milvus_search_response(response)
        except Exception as e:
            warnings.warn(f"Error searching image collection in Milvus: {e}")
            return []

    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        from ..agents.query_agent import QueryAgent

        return QueryAgent(self)

    def count_documents(self, date_filter: str = "all") -> int:
        """Count documents in the text collection."""
        if not self.has_text_collection():
            return 0

        self._ensure_client()
        if self.client is None:
            return 0

        try:
            # Get total count from text collection
            response = self.client.query(
                collection_name=self.text_collection.name,
                filter="",
                output_fields=["id"],
                limit=1,
            )

            # This is a simplified count - in a real implementation you'd want to use aggregation
            return len(response) if response else 0
        except Exception:
            return 0

    def count_images(self, date_filter: str = "all") -> int:
        """Count images in the image collection."""
        if not self.has_image_collection():
            return 0

        self._ensure_client()
        if self.client is None:
            return 0

        try:
            # Get total count from image collection
            response = self.client.query(
                collection_name=self.image_collection.name,
                filter="",
                output_fields=["id"],
                limit=1,
            )

            # This is a simplified count - in a real implementation you'd want to use aggregation
            return len(response) if response else 0
        except Exception:
            return 0

    def list_images(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List images from the image collection."""
        if not self.has_image_collection():
            return []

        self._ensure_client()
        if self.client is None:
            return []

        try:
            response = self.client.query(
                collection_name=self.image_collection.name,
                filter="",
                output_fields=["id", "url", "text", "metadata"],
                limit=limit,
                offset=offset,
            )
            return self._convert_milvus_response(response)
        except Exception:
            return []

    def delete_image(self, image_id: str) -> bool:
        """Delete an image from the image collection by ID."""
        if not self.has_image_collection():
            return False

        self._ensure_client()
        if self.client is None:
            return False

        try:
            self.client.delete(
                collection_name=self.image_collection.name, pks=[image_id]
            )
            return True
        except Exception:
            return False

    def find_image_by_url(self, url: str) -> dict[str, Any] | None:
        """Find an image by its URL in the image collection."""
        if not self.has_image_collection():
            return None

        self._ensure_client()
        if self.client is None:
            return None

        try:
            response = self.client.query(
                collection_name=self.image_collection.name,
                filter=f'url == "{url}"',
                output_fields=["id", "url", "text", "metadata"],
                limit=1,
            )
            results = self._convert_milvus_response(response)
            return results[0] if results else None
        except Exception:
            return None

    def cleanup(self):
        """Clean up resources and close connections."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

    def supports_images(self) -> bool:
        """Check if this vector database implementation supports image storage."""
        return self.has_image_collection()

    def _get_text_embedding(self, text: str) -> list[float]:
        """Generate text embedding using OpenAI API."""
        try:
            import openai

            # Get API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")

            # Generate embedding
            response = openai.Embedding.create(
                model="text-embedding-3-large", input=text
            )

            return response["data"][0]["embedding"]
        except Exception as e:
            warnings.warn(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    def _convert_milvus_response(self, response) -> list[dict[str, Any]]:
        """Convert Milvus query response to standard format."""
        results = []
        for item in response:
            result = {
                "id": item.get("id", ""),
                "url": item.get("url", ""),
                "text": item.get("text", ""),
                "metadata": {},
            }

            # Parse metadata if it exists
            if "metadata" in item:
                try:
                    result["metadata"] = json.loads(item["metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["metadata"] = {}

            results.append(result)

        return results

    def _convert_milvus_search_response(self, response) -> list[dict[str, Any]]:
        """Convert Milvus search response to standard format."""
        results = []
        for hit in response[0]:  # response is a list of hits for each query
            result = {
                "id": hit.entity.get("id", ""),
                "url": hit.entity.get("url", ""),
                "text": hit.entity.get("text", ""),
                "metadata": {},
                "score": hit.score,
            }

            # Parse metadata if it exists
            if "metadata" in hit.entity:
                try:
                    result["metadata"] = json.loads(hit.entity["metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["metadata"] = {}

            results.append(result)

        return results
