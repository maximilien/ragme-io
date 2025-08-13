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

        # Get environment variables
        weaviate_url = os.getenv("WEAVIATE_URL")
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")

        if not weaviate_url or not weaviate_api_key:
            raise ValueError(
                "WEAVIATE_URL and WEAVIATE_API_KEY environment variables are required"
            )

        # Ensure URL has proper scheme
        if not weaviate_url.startswith(("http://", "https://")):
            weaviate_url = f"https://{weaviate_url}"

        # Remove trailing slash if present
        weaviate_url = weaviate_url.rstrip("/")

        try:
            # Connect to Weaviate using the v4 client
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
            )

        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Weaviate at {weaviate_url}: {str(e)}"
            ) from e

    def setup(self):
        """Set up Weaviate collection if it doesn't exist."""
        from weaviate.classes.config import Configure, DataType, Property

        if not self.client.collections.exists(self.collection_name):
            # Determine if this is an image collection based on collection name
            is_image_collection = self._is_image_collection()

            if is_image_collection:
                # Create image collection with BLOB support
                try:
                    self.client.collections.create(
                        self.collection_name,
                        description="A dataset with image content for RagMe",
                        vectorizer_config=Configure.Vectorizer.multi2vec_google(
                            image_fields=["image"]
                        ),
                        properties=[
                            Property(
                                name="url",
                                data_type=DataType.TEXT,
                                description="the source URL or filename of the image",
                            ),
                            Property(
                                name="image",
                                data_type=DataType.BLOB,
                                description="the base64 encoded image",
                            ),
                            Property(
                                name="metadata",
                                data_type=DataType.TEXT,
                                description="additional metadata in JSON format",
                            ),
                        ],
                    )
                except Exception:
                    # Fallback to text vectorizer if multi2vec-google is not available
                    print(
                        "multi2vec-google not available for images, "
                        "falling back to text2vec-weaviate."
                    )
                    self.client.collections.create(
                        self.collection_name,
                        description="A dataset with image content for RagMe",
                        vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                        properties=[
                            Property(
                                name="image",
                                data_type=DataType.TEXT,
                                description="the base64 encoded image",
                            ),
                            Property(
                                name="metadata",
                                data_type=DataType.TEXT,
                                description="additional metadata in JSON format",
                            ),
                        ],
                    )
            else:
                # Create text collection
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

    def _is_image_collection(self) -> bool:
        """Check if this collection is configured for images."""
        from ..utils.config_manager import config

        # Check if this collection name matches any image collection in config
        collections = config.get_collections_config()
        for collection in collections:
            if (
                isinstance(collection, dict)
                and collection.get("name") == self.collection_name
                and collection.get("type") == "image"
            ):
                return True

        # Also check common image collection naming patterns
        image_patterns = ["image", "images", "ragmeimages"]
        return any(
            pattern.lower() in self.collection_name.lower()
            for pattern in image_patterns
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

    def write_images(self, images: list[dict[str, Any]]):
        """Write images to Weaviate."""
        collection = self.client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for img in images:
                # Get image data and metadata
                image_data = img.get("image_data", "")
                metadata = img.get("metadata", {})

                # Remove image_data from metadata to avoid duplication
                if "image_data" in metadata:
                    del metadata["image_data"]

                metadata_text = json.dumps(metadata, ensure_ascii=False)

                print(f"Writing image with data length: {len(image_data)}")
                print(
                    f"Image data starts with: {image_data[:50] if image_data else 'None'}"
                )
                print(
                    f"Classification data: {metadata.get('classification', {}).get('top_prediction', {})}"
                )

                try:
                    batch.add_object(
                        properties={
                            "url": img.get("url", ""),  # Store URL/filename
                            "image": image_data,  # Store in BLOB field
                            "metadata": metadata_text,  # Store classification in metadata
                        }
                    )
                    print("Image object added to batch successfully")
                except Exception as e:
                    print(f"Error writing image to Weaviate: {e}")
                    import traceback

                    traceback.print_exc()

    def supports_images(self) -> bool:
        """Check if this Weaviate implementation supports images."""
        return True

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

            # For image collections, include the image data from BLOB field
            if self._is_image_collection():
                doc["image_data"] = obj.properties.get("image", "")

            # Try to parse metadata if it's a JSON string
            try:
                if doc["metadata"] is not None:
                    doc["metadata"] = json.loads(doc["metadata"])
                else:
                    doc["metadata"] = {}
            except json.JSONDecodeError:
                doc["metadata"] = {}

            documents.append(doc)

        # Sort by creation time (most recent first) - Weaviate doesn't support
        # sorting in query. So we'll sort the results after fetching
        documents.sort(
            key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
        )

        return documents

    def count_documents(self, date_filter: str = "all") -> int:
        """Count documents in Weaviate efficiently using aggregation."""
        try:
            collection = self.client.collections.get(self.collection_name)

            # Build date filter condition if needed
            where_filter = None
            if date_filter != "all":
                import datetime

                now = datetime.datetime.now()

                if date_filter == "current":
                    # Current week
                    start_of_week = now - datetime.timedelta(days=now.weekday())
                    start_date = start_of_week.isoformat()
                elif date_filter == "month":
                    # Current month
                    start_date = now.replace(day=1).isoformat()
                elif date_filter == "year":
                    # Current year
                    start_date = now.replace(month=1, day=1).isoformat()
                else:
                    start_date = None

                if start_date:
                    where_filter = {
                        "path": ["metadata", "date_added"],
                        "operator": "GreaterThanEqual",
                        "valueDate": start_date,
                    }

            # Use efficient aggregation to count
            if where_filter:
                result = collection.aggregate.over_all(
                    total_count=True, where=where_filter
                )
            else:
                result = collection.aggregate.over_all(total_count=True)

            return result.total_count or 0

        except Exception as e:
            print(f"Error counting documents in Weaviate: {str(e)}")
            # Fallback to list_documents approach
            try:
                # Import the filter function from the API module where it's defined
                import os
                import sys

                sys.path.append(os.path.join(os.path.dirname(__file__), "..", "apis"))
                from api import filter_documents_by_date

                all_docs = self.list_documents(limit=10000, offset=0)
                filtered_docs = filter_documents_by_date(all_docs, date_filter)
                return len(filtered_docs)
            except Exception:
                return 0

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
                limit=1000,  # Increased limit to search more documents
                include_vector=False,
            )

            # Normalize URL for comparison (remove protocol and fragments)
            def normalize_url(url_str):
                """Normalize URL by removing protocol and fragments."""
                if not url_str:
                    return ""
                # Remove protocol
                url_without_protocol = url_str.replace("https://", "").replace(
                    "http://", ""
                )
                # Remove fragments
                return url_without_protocol.split("#")[0]

            target_normalized = normalize_url(url)

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

                # Try normalized URL match (ignoring protocol and fragments)
                stored_normalized = normalize_url(stored_url)
                if stored_normalized == target_normalized:
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
