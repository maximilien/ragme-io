# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import logging
import warnings
from typing import Any

import weaviate
from weaviate.classes.query import MetadataQuery

from .vector_db_base import CollectionConfig, VectorDatabase

# Set up logging
logger = logging.getLogger(__name__)

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

# Suppress weaviate connection warnings
warnings.filterwarnings("ignore", message=".*Con004.*")
warnings.filterwarnings(
    "ignore", message=".*connection to Weaviate was not closed properly.*"
)


class WeaviateVectorDatabase(VectorDatabase):
    """Weaviate implementation of the vector database interface."""

    def __init__(self, collections: list[CollectionConfig]):
        super().__init__(collections)
        self.client = None
        self._create_client()

    def _create_client(self):
        """Create the Weaviate client."""
        import os

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

    def close(self):
        """Close the Weaviate client connection."""
        if self.client is not None:
            try:
                self.client.close()
                self.client = None
            except Exception as e:
                logger.warning(f"Error closing Weaviate client: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.close()

    def setup(self):
        """Set up Weaviate collections if they don't exist."""
        from weaviate.classes.config import Configure, DataType, Property

        for collection in self.collections:
            if not self.client.collections.exists(collection.name):
                if collection.type == "image":
                    # Create image collection with BLOB support
                    try:
                        self.client.collections.create(
                            collection.name,
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
                                    data_type=DataType.TEXT,
                                    description="the image reference (truncated base64 or URL)",
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
                            collection.name,
                            description="A dataset with image content for RagMe",
                            vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                            properties=[
                                Property(
                                    name="url",
                                    data_type=DataType.TEXT,
                                    description="the source URL or filename of the image",
                                ),
                                Property(
                                    name="image",
                                    data_type=DataType.TEXT,
                                    description="the image reference (truncated base64 or URL)",
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
                        collection.name,
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

    @property
    def db_type(self) -> str:
        """Return the type/name of the vector database."""
        return "weaviate"

    def write_documents(self, documents: list[dict[str, Any]]):
        """Write documents to the text collection."""
        if not self.has_text_collection():
            raise ValueError("No text collection configured for this VDB")

        collection = self.client.collections.get(self.text_collection.name)
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
        """Write images to the image collection."""
        if not self.has_image_collection():
            raise ValueError("No image collection configured for this VDB")

        collection = self.client.collections.get(self.image_collection.name)

        # Process images in smaller batches to avoid Weaviate embed API limits
        batch_size = 10  # Reduced batch size for large images
        total_images = len(images)
        successful_insertions = 0
        failed_insertions = 0

        print(f"Processing {total_images} images in batches of {batch_size}")

        for i in range(0, total_images, batch_size):
            batch_images = images[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_images + batch_size - 1) // batch_size

            print(
                f"Processing batch {batch_num}/{total_batches} with {len(batch_images)} images"
            )

            try:
                with collection.batch.dynamic() as batch:
                    for img in batch_images:
                        # Get image data and metadata
                        image_data = img.get("image_data", "")
                        metadata = img.get("metadata", {})

                        # Remove image_data from metadata to avoid duplication
                        if "image_data" in metadata:
                            del metadata["image_data"]

                        # Store image data in metadata for API access, but not in the main image field
                        # This avoids Weaviate cloud UI display issues with large BLOB data
                        metadata["base64_data"] = image_data

                        metadata_text = json.dumps(metadata, ensure_ascii=False)

                        print(f"Writing image with data length: {len(image_data)}")
                        print(
                            f"Image metadata: {metadata.get('filename', 'unknown')} "
                            f"({metadata.get('size', 'unknown')} bytes)"
                        )

                        batch.add_object(
                            properties={
                                "url": img.get("url", ""),
                                "image": f"data:image/jpeg;base64,{image_data[:100]}...",  # Store truncated reference
                                "metadata": metadata_text,
                            }
                        )

                # If we get here, the batch was successful
                successful_insertions += len(batch_images)
                print(f"Batch {batch_num} completed successfully")

            except Exception as e:
                print(f"Batch {batch_num} failed: {str(e)}")
                failed_insertions += len(batch_images)

                # Try to insert images one by one as fallback
                print(f"Attempting individual insertions for batch {batch_num}")
                for img in batch_images:
                    try:
                        with collection.batch.dynamic() as single_batch:
                            image_data = img.get("image_data", "")
                            metadata = img.get("metadata", {})

                            if "image_data" in metadata:
                                del metadata["image_data"]

                            metadata["base64_data"] = image_data
                            metadata_text = json.dumps(metadata, ensure_ascii=False)

                            single_batch.add_object(
                                properties={
                                    "url": img.get("url", ""),
                                    "image": f"data:image/jpeg;base64,{image_data[:100]}...",
                                    "metadata": metadata_text,
                                }
                            )

                        successful_insertions += 1
                        print(
                            f"Individual insertion successful for image: {metadata.get('filename', 'unknown')}"
                        )

                    except Exception as single_error:
                        failed_insertions += 1
                        print(
                            f"Individual insertion failed for image: {metadata.get('filename', 'unknown')} - {str(single_error)}"
                        )

        print(
            f"Image insertion completed: {successful_insertions} successful, {failed_insertions} failed out of {total_images} total"
        )

        if failed_insertions > 0:
            print(
                f"Warning: {failed_insertions} images failed to insert due to Weaviate embed API issues"
            )

        return successful_insertions > 0

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List documents from the text collection."""
        if not self.has_text_collection():
            return []

        collection = self.client.collections.get(self.text_collection.name)
        response = collection.query.fetch_objects(
            limit=limit, offset=offset, include_vector=False
        )
        return self._convert_weaviate_response(response)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the text collection by ID."""
        if not self.has_text_collection():
            return False

        collection = self.client.collections.get(self.text_collection.name)
        try:
            collection.data.delete_by_id(document_id)
            return True
        except Exception:
            return False

    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """Find a document by its URL in the text collection."""
        if not self.has_text_collection():
            return None

        collection = self.client.collections.get(self.text_collection.name)
        try:
            # Use fetch_objects with a high limit and filter in Python
            response = collection.query.fetch_objects(limit=1000, include_vector=False)
            results = self._convert_weaviate_response(response)

            # Filter by URL in Python
            for result in results:
                if result.get("url") == url:
                    return result
            return None
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
        """Search only the text collection using multiple search strategies."""
        if not self.has_text_collection():
            return []

        collection = self.client.collections.get(self.text_collection.name)
        all_results = []

        # Strategy 1: BM25 search (best for keyword matching)
        try:
            response = collection.query.bm25(
                query=query,
                limit=limit * 2,  # Get more results to combine
                include_vector=False,
                return_metadata=MetadataQuery(
                    score=True,  # Request BM25F score
                    explain_score=True,  # Get detailed score explanation
                ),
            )
            bm25_results = self._convert_weaviate_response(response)
            if bm25_results:
                logger.info(
                    f"BM25 search successful, found {len(bm25_results)} results"
                )
                # Tag BM25 results
                for result in bm25_results:
                    result["search_method"] = "bm25"
                all_results.extend(bm25_results)
        except Exception as e:
            logger.warning(f"BM25 search failed: {e}")

        # Strategy 2: Hybrid search (combines dense and sparse signals)
        try:
            response = collection.query.hybrid(
                query=query,
                limit=limit * 2,  # Get more results to combine
                include_vector=False,
                return_metadata=MetadataQuery(
                    distance=True,  # Request vector distance
                    score=True,  # Request BM25F score
                    explain_score=True,  # Get detailed score explanation
                ),
            )
            hybrid_results = self._convert_weaviate_response(response)
            if hybrid_results:
                logger.info(
                    f"Hybrid search successful, found {len(hybrid_results)} results"
                )
                # Tag hybrid results
                for result in hybrid_results:
                    result["search_method"] = "hybrid"
                all_results.extend(hybrid_results)
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}")

        # Strategy 3: Near-text search (vector-based)
        try:
            response = collection.query.near_text(
                query=query,
                limit=limit * 2,  # Get more results to combine
                include_vector=True,  # Include vectors for better scoring
                return_metadata=MetadataQuery(
                    distance=True,  # Request vector distance
                ),
            )
            near_text_results = self._convert_weaviate_response(response)
            if near_text_results:
                logger.info(
                    f"Near-text search successful, found {len(near_text_results)} results"
                )
                # Tag near-text results
                for result in near_text_results:
                    result["search_method"] = "near_text"
                all_results.extend(near_text_results)
        except Exception as e:
            logger.warning(f"Near-text search failed: {e}")

        # Combine and deduplicate results
        if not all_results:
            return []

        # Deduplicate by document ID and combine scores
        combined_results = {}
        for result in all_results:
            doc_id = result.get("id")
            if doc_id not in combined_results:
                combined_results[doc_id] = result
            else:
                # Combine scores from different search methods
                existing = combined_results[doc_id]
                existing_score = existing.get("score", 0)
                new_score = result.get("score", 0)

                # Take the best score and track search methods
                if new_score > existing_score:
                    existing["score"] = new_score

                # Track all search methods that found this document
                if "search_methods" not in existing:
                    existing["search_methods"] = [
                        existing.get("search_method", "unknown")
                    ]
                existing["search_methods"].append(
                    result.get("search_method", "unknown")
                )
                existing["search_methods"] = list(
                    set(existing["search_methods"])
                )  # Remove duplicates

                # Boost score if multiple search methods found this document
                if len(existing["search_methods"]) > 1:
                    # Boost by 10% for each additional search method (up to 50% max)
                    boost_factor = min(
                        1.5, 1.0 + (len(existing["search_methods"]) - 1) * 0.1
                    )
                    existing["score"] = min(1.0, existing["score"] * boost_factor)
                    logger.debug(
                        f"Boosted score for {doc_id} by {boost_factor:.2f}x due to {len(existing['search_methods'])} search methods"
                    )

        # Convert back to list and sort by score
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"Combined search found {len(final_results)} unique results")

        # Debug: Log top results with scores
        logger.info("=== TOP SEARCH RESULTS ===")
        for i, result in enumerate(final_results[:limit]):
            doc_id = str(result.get("id", "unknown"))
            url = result.get("url", "unknown")
            score = result.get("score", 0)
            search_methods = result.get(
                "search_methods", [result.get("search_method", "unknown")]
            )
            logger.info(
                f"#{i + 1}: ID={doc_id[:8]}... URL={url[:50]}... Score={score:.4f} Methods={search_methods}"
            )
        logger.info("=== END SEARCH RESULTS ===")

        return final_results[:limit]

    def search_image_collection(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search only the image collection using metadata.

        Strategy:
        - First try to search in filenames (most reliable for image content)
        - Then try hybrid search to leverage both dense and sparse signals
        - Fallback to BM25 (sparse, robust for plain keywords in metadata)
        - Final fallback to near_text if others are unavailable
        """
        if not self.has_image_collection():
            return []

        collection = self.client.collections.get(self.image_collection.name)

        # First, try to search in filenames using BM25 with specific field targeting
        try:
            # Use BM25 to search specifically in the filename field
            response = collection.query.bm25(
                query=query,
                limit=limit,
                include_vector=False,
                properties=["metadata.filename"],
            )
            results = self._convert_weaviate_response(response)
            if results:
                return results
        except Exception:
            pass

        # Try hybrid search with score
        try:
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                include_vector=False,
                return_metadata=MetadataQuery(
                    distance=True,  # Request vector distance
                    score=True,  # Request BM25F score
                ),
            )
            results = self._convert_weaviate_response(response)
            if results:
                return results
        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to BM25: {e}")

        # Fallback to BM25 (general search) with score
        try:
            response = collection.query.bm25(
                query=query,
                limit=limit,
                include_vector=False,
                return_metadata=MetadataQuery(
                    score=True,  # Request BM25F score
                ),
            )
            results = self._convert_weaviate_response(response)
            if results:
                return results
        except Exception as e:
            logger.warning(f"BM25 failed, falling back to near_text: {e}")

        # Last resort: near_text with metadata
        try:
            response = collection.query.near_text(
                query=query,
                limit=limit,
                include_vector=False,
                return_metadata=MetadataQuery(
                    distance=True,  # Request vector distance
                ),
            )
        except Exception as e:
            logger.warning(
                f"Near_text with metadata failed, falling back to basic: {e}"
            )
            response = collection.query.near_text(
                query=query, limit=limit, include_vector=False
            )
        return self._convert_weaviate_response(response)

    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        from ..agents.query_agent import QueryAgent

        return QueryAgent(self)

    def count_documents(self, date_filter: str = "all") -> int:
        """Count documents in the text collection."""
        if not self.has_text_collection():
            return 0

        collection = self.client.collections.get(self.text_collection.name)
        try:
            # Use fetch_objects with a high limit to get all objects and count them
            response = collection.query.fetch_objects(limit=10000, include_vector=False)
            return len(response.objects)
        except Exception:
            # Fallback: try to get a reasonable estimate
            return 0

    def count_images(self, date_filter: str = "all") -> int:
        """Count images in the image collection."""
        if not self.has_image_collection():
            return 0

        collection = self.client.collections.get(self.image_collection.name)
        try:
            # Use fetch_objects with a high limit to get all objects and count them
            response = collection.query.fetch_objects(limit=10000, include_vector=False)
            return len(response.objects)
        except Exception:
            # Fallback: try to get a reasonable estimate
            return 0

    def list_images(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """List images from the image collection."""
        if not self.has_image_collection():
            return []

        collection = self.client.collections.get(self.image_collection.name)
        response = collection.query.fetch_objects(
            limit=limit, offset=offset, include_vector=False
        )
        return self._convert_weaviate_response(response)

    def delete_image(self, image_id: str) -> bool:
        """Delete an image from the image collection by ID."""
        if not self.has_image_collection():
            return False

        collection = self.client.collections.get(self.image_collection.name)
        try:
            collection.data.delete_by_id(image_id)
            return True
        except Exception:
            return False

    def find_image_by_url(self, url: str) -> dict[str, Any] | None:
        """Find an image by its URL in the image collection."""
        if not self.has_image_collection():
            return None

        collection = self.client.collections.get(self.image_collection.name)
        try:
            # Use fetch_objects with a high limit and filter in Python
            response = collection.query.fetch_objects(limit=1000, include_vector=False)
            results = self._convert_weaviate_response(response)

            # Filter by URL in Python
            for result in results:
                if result.get("url") == url:
                    return result
            return None
        except Exception:
            return None

    def find_image_by_filename(self, filename: str) -> dict[str, Any] | None:
        """Find an image by its filename in the image collection."""
        if not self.has_image_collection():
            return None

        collection = self.client.collections.get(self.image_collection.name)
        try:
            # Use fetch_objects with a high limit and filter in Python
            response = collection.query.fetch_objects(limit=1000, include_vector=False)
            results = self._convert_weaviate_response(response)

            # Filter by filename in metadata
            for result in results:
                metadata = result.get("metadata", {})
                if metadata.get("filename") == filename:
                    return result
            return None
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

    def _convert_weaviate_response(self, response) -> list[dict[str, Any]]:
        """Convert Weaviate response to standard format."""
        results = []
        for obj in response.objects:
            result = {
                "id": obj.uuid,
                "url": obj.properties.get("url", ""),
                "text": obj.properties.get("text", ""),
                "metadata": {},
            }

            # Parse metadata if it exists
            if "metadata" in obj.properties:
                try:
                    result["metadata"] = json.loads(obj.properties["metadata"])
                except (json.JSONDecodeError, TypeError):
                    result["metadata"] = {}

            # Add image data if this is an image (check if 'image' field exists)
            if "image" in obj.properties:
                # Store the truncated reference for Weaviate cloud display
                image_value = obj.properties["image"]
                if image_value:  # Only add if not empty/null
                    result["image"] = image_value
                # For images, the actual data is stored in metadata.base64_data
                # The image field contains a truncated reference
                if "metadata" in result and "base64_data" in result["metadata"]:
                    result["image_data"] = result["metadata"]["base64_data"]
                else:
                    result["image_data"] = image_value

            # Add similarity score if available (from metadata)
            if hasattr(obj, "metadata") and obj.metadata:
                # Convert UUID to string for logging
                uuid_str = str(obj.uuid)
                logger.debug(f"Processing metadata for object {uuid_str[:8]}...")

                # Try to get BM25 score first (best for keyword matching)
                if hasattr(obj.metadata, "score") and obj.metadata.score is not None:
                    bm25_score = obj.metadata.score
                    logger.debug(f"Raw BM25 score: {bm25_score}")

                    # Fixed BM25 score normalization
                    # BM25 scores can be negative or positive depending on the query and document
                    # We want to map them to a 0-1 similarity scale where higher is better
                    # IMPORTANT: For BM25, more negative scores often indicate HIGHER relevance
                    # because they represent better matches to the query terms
                    if bm25_score > 0:
                        # For positive scores, use normalization
                        # Map 0-10 to 0.3-1.0 range for better discrimination
                        result["score"] = min(0.3 + (bm25_score / 10.0) * 0.7, 1.0)
                    else:
                        # For negative scores, invert the logic - more negative = higher relevance
                        # Map -10 to 1.0, -5 to 0.8, -2 to 0.6, -1 to 0.5, 0 to 0.4
                        # This correctly reflects that negative BM25 scores often indicate good matches
                        if bm25_score <= -10:
                            result["score"] = 1.0
                        elif bm25_score <= -5:
                            result["score"] = 0.8
                        elif bm25_score <= -2:
                            result["score"] = 0.6
                        elif bm25_score <= -1:
                            result["score"] = 0.5
                        else:
                            result["score"] = 0.4

                    logger.debug(
                        f"Normalized BM25 score: {result['score']} (from {bm25_score})"
                    )

                # Try to get certainty next (normalized similarity, higher is better)
                elif (
                    hasattr(obj.metadata, "certainty")
                    and obj.metadata.certainty is not None
                ):
                    result["score"] = obj.metadata.certainty
                    logger.debug(f"Certainty score: {result['score']}")

                # Fallback to distance (lower is better, so we invert it for consistency)
                elif (
                    hasattr(obj.metadata, "distance")
                    and obj.metadata.distance is not None
                ):
                    # Convert distance to similarity score (1 - distance for cosine)
                    result["score"] = 1.0 - obj.metadata.distance
                    logger.debug(
                        f"Distance-based score: {result['score']} (from distance {obj.metadata.distance})"
                    )

            # Fallback to direct score attribute
            elif hasattr(obj, "score") and obj.score is not None:
                result["score"] = obj.score
                logger.debug(f"Direct score: {result['score']}")

            # If no score was found, set a default low score
            if "score" not in result:
                result["score"] = 0.1
                uuid_str = str(obj.uuid)
                logger.debug(f"No score found for {uuid_str[:8]}, using default: 0.1")

            results.append(result)

        return results
