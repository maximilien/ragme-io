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


class WeaviateLocalVectorDatabase(VectorDatabase):
    """Local Weaviate implementation of the vector database interface."""

    def __init__(self, collection_name: str = "RagMeDocs"):
        super().__init__(collection_name)
        self.client = None
        self._create_client()

    def _create_client(self):
        """Create the local Weaviate client."""
        import os

        import weaviate

        # Get local Weaviate URL from environment or use default
        weaviate_url = os.getenv("WEAVIATE_LOCAL_URL", "http://localhost:8080")

        try:
            # Temporarily unset authentication environment variables
            original_api_key = os.environ.pop("WEAVIATE_API_KEY", None)
            original_api_key_v2 = os.environ.pop("WEAVIATE_APIKEY", None)

            try:
                # Parse the URL to get host and port
                if weaviate_url.startswith("http://"):
                    host_port = weaviate_url[7:]  # Remove 'http://'
                elif weaviate_url.startswith("https://"):
                    host_port = weaviate_url[8:]  # Remove 'https://'
                else:
                    host_port = weaviate_url

                # Split host and port
                if ":" in host_port:
                    host, port_str = host_port.split(":", 1)
                    port = int(port_str)
                else:
                    host = host_port
                    port = 8080

                # Use the Weaviate v4 client syntax
                self.client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    headers={},  # No additional headers
                )
            finally:
                # Restore environment variables
                if original_api_key:
                    os.environ["WEAVIATE_API_KEY"] = original_api_key
                if original_api_key_v2:
                    os.environ["WEAVIATE_APIKEY"] = original_api_key_v2

        except Exception as e:
            # Provide helpful error message for local setup
            raise ConnectionError(
                f"Failed to connect to local Weaviate at {weaviate_url}. "
                f"Make sure Weaviate is running locally. Error: {str(e)}"
            ) from e

    def setup(self):
        """Set up local Weaviate collection if it doesn't exist."""
        from weaviate.classes.config import DataType, Property

        if not self.client.collections.exists(self.collection_name):
            self.client.collections.create(
                self.collection_name,
                description="A dataset with the contents of RagMe docs and website",
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
        """Write documents to local Weaviate."""
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
        """
        List documents from the local Weaviate collection.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of documents with their properties
        """
        try:
            # Get documents from the collection using the correct Weaviate v4 API
            collection = self.client.collections.get(self.collection_name)
            response = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                include_vector=False,
            )

            documents = []
            for obj in response.objects:
                doc = {
                    "id": obj.uuid,
                    "url": obj.properties.get("url", ""),
                    "text": obj.properties.get("text", ""),
                    "metadata": {},
                }

                # Add all other properties as metadata
                for key, value in obj.properties.items():
                    if key not in ["url", "text"]:
                        doc["metadata"][key] = value

                documents.append(doc)

            # Sort by creation time (most recent first) - Weaviate doesn't support sorting in query
            # So we'll sort the results after fetching
            documents.sort(
                key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
            )

            return documents

        except Exception as e:
            print(f"Error listing documents from Weaviate: {str(e)}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the local Weaviate collection by ID.

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if document was deleted successfully, False if not found
        """
        try:
            # Delete the document by UUID using the correct Weaviate v4 API
            collection = self.client.collections.get(self.collection_name)
            collection.data.delete_by_id(document_id)
            return True
        except Exception as e:
            print(f"Error deleting document {document_id} from Weaviate: {str(e)}")
            return False

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for documents using local Weaviate's vector similarity search.

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
                    "metadata": {},
                }

                # Add all other properties as metadata
                for key, value in obj.properties.items():
                    if key not in ["url", "text"]:
                        doc["metadata"][key] = value

                documents.append(doc)

            return documents

        except Exception as e:
            print(f"Failed to perform vector search for query '{query}': {str(e)}")
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
            print(f"Fallback keyword search also failed: {str(e)}")
            return []

    def create_query_agent(self, llm=None):
        """Create a local Weaviate query agent."""

        # Create a custom query agent that ensures proper URL formatting and citations
        class WeaviateLocalQueryAgent:
            def __init__(self, vector_db, llm=None):
                self.vector_db = vector_db
                self.client = vector_db.client
                self.collection_name = vector_db.collection_name
                self.llm = llm  # Store the LLM instance for detailed query detection

                # Get query configuration
                from src.ragme.utils.config_manager import config

                self.top_k = config.get("query.top_k", 5)

                # Get citation configuration
                self.include_citations = config.get("query.include_citations", False)

            async def run(self, query: str, is_detailed: bool = None):
                """Run a query using vector similarity search."""
                try:
                    # Use the vector database search method
                    documents = self.vector_db.search(query, limit=5)

                    if documents:
                        # Get the most relevant document
                        most_relevant = documents[0]
                        content = most_relevant.get("text", "")
                        url = most_relevant.get("url", "")
                        metadata = most_relevant.get("metadata", {})

                        # For chunked documents, provide more context
                        if metadata.get("is_chunked") or metadata.get("is_chunk"):
                            chunk_info = f" (Chunked document with {metadata.get('total_chunks', 'unknown')} chunks)"
                        else:
                            chunk_info = ""

                        # Include similarity score if available
                        score_info = ""
                        if "score" in most_relevant:
                            score_info = f" (Similarity: {most_relevant['score']:.3f})"

                        # Truncate content if too long
                        if len(content) > 2000:
                            content = content[:2000] + "..."

                        # Format URL as a proper markdown link
                        url_link = f"[{url}]({url})" if url else "No URL available"

                        result = f"**Based on the stored documents, here's what I found:**\n\n**URL:** {url_link}{chunk_info}{score_info}\n\n**Answer:** {content}"

                        # Add citations based on configuration and query type
                        # Use the passed is_detailed parameter, or default to False if not provided
                        if is_detailed is None:
                            is_detailed = False

                        # If include_citations is True, always include citations
                        # If include_citations is False, only include for detailed queries or multiple documents
                        should_include_citations = (
                            self.include_citations or is_detailed or len(documents) > 1
                        )

                        if should_include_citations:
                            citations = self._generate_citations(documents[:3])
                            result += f"\n\n**Citations:**\n{citations}"

                        return result
                    else:
                        return f"I couldn't find any relevant information about '{query}' in the stored documents."

                except Exception as e:
                    return f"Error performing query: {str(e)}"

            def _generate_citations(self, documents: list[dict]) -> str:
                """
                Generate citations for the top documents used in the response.

                Args:
                    documents (list): List of documents to cite

                Returns:
                    str: Formatted citations
                """
                citations = []
                for i, doc in enumerate(documents, 1):
                    url = doc.get("url", "")
                    metadata = doc.get("metadata", {})
                    filename = metadata.get("filename", "Unknown Document")

                    # Format URL as markdown link
                    if url:
                        url_link = f"[{url}]({url})"
                    else:
                        url_link = "No URL available"

                    # Add similarity score if available
                    score_info = ""
                    if "score" in doc:
                        score_info = f" (Similarity: {doc['score']:.3f})"

                    citations.append(f"{i}. **{filename}** - {url_link}{score_info}")

                return "\n".join(citations)

        return WeaviateLocalQueryAgent(self, llm)

    def cleanup(self):
        """Clean up local Weaviate client."""
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

                warnings.warn(f"Error during local Weaviate cleanup: {e}")
            finally:
                self.client = None

    @property
    def db_type(self) -> str:
        return "weaviate-local"
