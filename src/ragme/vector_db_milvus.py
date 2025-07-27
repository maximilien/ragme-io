# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import os
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
                vector_field_name="vector",
            )

    def write_documents(self, documents: list[dict[str, Any]]):
        """Write documents to Milvus."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Documents not written.")
            return

        # Each document should have 'url', 'text', 'metadata', and optionally 'vector'
        data = []
        for i, doc in enumerate(documents):
            # Generate vector if not provided
            if "vector" not in doc or doc["vector"] is None:
                try:
                    # Use OpenAI embeddings to generate vector
                    from openai import OpenAI

                    # Get OpenAI API key from environment
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError(
                            "OPENAI_API_KEY environment variable is required for vector generation"
                        )

                    client = OpenAI(api_key=api_key)

                    # Generate embedding for the text content
                    text_content = doc.get("text", "")
                    if not text_content:
                        # Skip documents with empty text
                        continue

                    response = client.embeddings.create(
                        model="text-embedding-3-small", input=text_content
                    )

                    # Extract the vector
                    vector = response.data[0].embedding
                    doc["vector"] = vector

                except Exception as e:
                    warnings.warn(f"Failed to generate vector for document {i}: {e}")
                    continue

            # Only add documents that have a valid vector
            if "vector" in doc and doc["vector"] is not None:
                data.append(
                    {
                        "id": i,  # Use integer index instead of UUID
                        "url": doc.get("url", ""),
                        "text": doc.get("text", ""),
                        "metadata": json.dumps(
                            doc.get("metadata", {}), ensure_ascii=False
                        ),
                        "vector": doc["vector"],
                    }
                )

        if data:
            self.client.insert(self.collection_name, data)

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
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
            offset=offset,
        )

        docs = []
        for doc in results:
            try:
                metadata = json.loads(doc.get("metadata", "{}"))
            except Exception:
                metadata = {}
            docs.append(
                {
                    "id": doc.get("id"),
                    "url": doc.get("url", ""),
                    "text": doc.get("text", ""),
                    "metadata": metadata,
                }
            )
        return docs

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from Milvus by ID."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Cannot delete document.")
            return False

        try:
            # Delete the document by ID
            self.client.delete(self.collection_name, pks=[document_id])
            return True
        except Exception as e:
            warnings.warn(f"Failed to delete document {document_id}: {e}")
            return False

    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """Find a document by its URL."""
        self._ensure_client()
        if self.client is None:
            warnings.warn("Milvus client is not available. Cannot find document.")
            return None

        try:
            # Query for documents with the specific URL
            results = self.client.query(
                self.collection_name,
                filter=f'url == "{url}"',
                output_fields=["id", "url", "text", "metadata"],
                limit=1,
            )

            if results:
                doc = results[0]
                try:
                    metadata = json.loads(doc.get("metadata", "{}"))
                except Exception:
                    metadata = {}

                return {
                    "id": doc.get("id"),
                    "url": doc.get("url", ""),
                    "text": doc.get("text", ""),
                    "metadata": metadata,
                }

            return None
        except Exception as e:
            warnings.warn(f"Failed to find document by URL {url}: {e}")
            return None

    def create_query_agent(self):
        """Create a query agent for Milvus."""

        # Create a simple query agent that can perform vector similarity search
        class MilvusQueryAgent:
            def __init__(self, vector_db):
                self.vector_db = vector_db
                self.client = vector_db.client
                self.collection_name = vector_db.collection_name

            def run(self, query: str):
                """Run a query using vector similarity search."""
                try:
                    # For now, use simple keyword matching as fallback
                    # In a full implementation, you would:
                    # 1. Generate embeddings for the query
                    # 2. Perform vector similarity search
                    # 3. Return the most relevant documents

                    # Get all documents and perform keyword matching - increase limit
                    documents = self.vector_db.list_documents(limit=100, offset=0)

                    # Improved keyword matching for chunked documents
                    query_lower = query.lower()
                    query_words = query_lower.split()
                    relevant_docs = []

                    for doc in documents:
                        text = doc.get("text", "").lower()
                        url = doc.get("url", "").lower()

                        # Check if any query word appears in text or URL
                        # Also check metadata for chunked documents
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
                                {
                                    "doc": doc,
                                    "matches": matches,
                                    "text_length": len(text),
                                }
                            )

                    if relevant_docs:
                        # Sort by relevance (more matches first, then by text length)
                        relevant_docs.sort(
                            key=lambda x: (-x["matches"], -x["text_length"])
                        )

                        # Get the most relevant document
                        most_relevant = relevant_docs[0]["doc"]
                        content = most_relevant.get("text", "")
                        url = most_relevant.get("url", "")
                        metadata = most_relevant.get("metadata", {})

                        # For chunked documents, provide more context
                        if metadata.get("is_chunked") or metadata.get("is_chunk"):
                            chunk_info = f" (Chunked document with {metadata.get('total_chunks', 'unknown')} chunks)"
                        else:
                            chunk_info = ""

                        # Truncate content if too long
                        if len(content) > 2000:
                            content = content[:2000] + "..."

                        return f"Based on the stored documents, here's what I found:\n\nURL: {url}{chunk_info}\n\nContent: {content}"
                    else:
                        return f"I couldn't find any relevant information about '{query}' in the stored documents."

                except Exception as e:
                    return f"Error performing query: {str(e)}"

        return MilvusQueryAgent(self)

    def cleanup(self):
        """Clean up Milvus client."""
        # No explicit cleanup needed for MilvusClient
        if self.client is not None:
            self.client = None

    @property
    def db_type(self) -> str:
        return "milvus"
