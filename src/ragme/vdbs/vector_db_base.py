# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from abc import ABC, abstractmethod
from typing import Any

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
    def write_documents(self, documents: list[dict[str, Any]]):
        """
        Write documents to the vector database.

        Args:
            documents: List of documents with 'url', 'text', and 'metadata' fields

        Returns:
            None
        """
        pass

    @abstractmethod
    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
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
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector database by ID.

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if document was deleted successfully, False if not found
        """
        pass

    @abstractmethod
    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """
        Find a document by its URL.

        Args:
            url: URL of the document to find

        Returns:
            Document dict if found, None if not found
        """
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for documents using vector similarity search.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            List of documents sorted by relevance
        """
        pass

    @abstractmethod
    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        pass

    @abstractmethod
    def count_documents(self, date_filter: str = "all") -> int:
        """
        Count documents in the vector database efficiently.

        Args:
            date_filter: Date filter to apply ('current', 'month', 'year', 'all')

        Returns:
            Number of documents matching the filter
        """
        pass

    @abstractmethod
    def cleanup(self):
        """Clean up resources and close connections."""
        pass

    # Image support methods
    @abstractmethod
    def write_images(self, images: list[dict[str, Any]]):
        """
        Write images to the vector database.

        Args:
            images: List of images with 'url', 'image_data' (base64), 
                   and 'metadata' fields

        Returns:
            None
        """
        pass

    @abstractmethod
    def supports_images(self) -> bool:
        """
        Check if this vector database implementation supports image storage.

        Returns:
            bool: True if images are supported, False otherwise
        """
        pass
