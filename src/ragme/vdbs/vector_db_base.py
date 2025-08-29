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


class CollectionConfig:
    """Configuration for a vector database collection."""

    def __init__(self, name: str, collection_type: str):
        """
        Initialize collection configuration.

        Args:
            name: Name of the collection
            collection_type: Type of collection ("text" or "image")
        """
        self.name = name
        self.type = collection_type


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""

    def __init__(self, collections: list[CollectionConfig]):
        """
        Initialize the vector database with collection configurations.

        Args:
            collections: List of collection configurations
        """
        self.collections = collections
        self.text_collection = None
        self.image_collection = None

        # Set up collection references
        for collection in collections:
            if collection.type == "text" and self.text_collection is None:
                self.text_collection = collection
            elif collection.type == "image" and self.image_collection is None:
                self.image_collection = collection

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
        Write documents to the text collection of the vector database.

        Args:
            documents: List of documents with 'url', 'text', and 'metadata' fields

        Returns:
            None
        """
        pass

    @abstractmethod
    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """
        List documents from the text collection of the vector database.

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
        Delete a document from the text collection of the vector database by ID.

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if document was deleted successfully, False if not found
        """
        pass

    @abstractmethod
    def update_document_metadata(
        self, document_id: str, metadata: dict[str, Any]
    ) -> bool:
        """
        Update metadata for a document in the text collection of the vector database.

        Args:
            document_id: ID of the document to update
            metadata: Dictionary of metadata fields to update

        Returns:
            bool: True if document was updated successfully, False if not found
        """
        pass

    @abstractmethod
    def find_document_by_url(self, url: str) -> dict[str, Any] | None:
        """
        Find a document by its URL in the text collection.

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
        If both text and image collections are configured, searches both in parallel.

        Args:
            query: The search query text
            limit: Maximum number of results to return per collection

        Returns:
            List of documents sorted by relevance from all collections
        """
        pass

    @abstractmethod
    def search_text_collection(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search only the text collection.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            List of documents sorted by relevance
        """
        pass

    @abstractmethod
    def search_image_collection(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search only the image collection using metadata.

        Args:
            query: The search query text
            limit: Maximum number of results to return

        Returns:
            List of images sorted by relevance
        """
        pass

    @abstractmethod
    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        pass

    @abstractmethod
    def count_documents(self, date_filter: str = "all") -> int:
        """
        Count documents in the text collection of the vector database efficiently.

        Args:
            date_filter: Date filter to apply ('today', 'week', 'month', 'year', 'all')

        Returns:
            Number of documents matching the filter
        """
        pass

    @abstractmethod
    def count_images(self, date_filter: str = "all") -> int:
        """
        Count images in the image collection of the vector database efficiently.

        Args:
            date_filter: Date filter to apply ('today', 'week', 'month', 'year', 'all')

        Returns:
            Number of images matching the filter
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
        Write images to the image collection of the vector database.

        Args:
            images: List of images with 'url', 'image_data' (base64),
                   and 'metadata' fields

        Returns:
            None
        """
        pass

    @abstractmethod
    def list_images(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """
        List images from the image collection of the vector database.

        Args:
            limit: Maximum number of images to return
            offset: Number of images to skip

        Returns:
            List of images with their properties
        """
        pass

    @abstractmethod
    def delete_image(self, image_id: str) -> bool:
        """
        Delete an image from the image collection of the vector database by ID.

        Args:
            image_id: ID of the image to delete

        Returns:
            bool: True if image was deleted successfully, False if not found
        """
        pass

    @abstractmethod
    def update_image_metadata(self, image_id: str, metadata: dict[str, Any]) -> bool:
        """
        Update metadata for an image in the image collection of the vector database.

        Args:
            image_id: ID of the image to update
            metadata: Dictionary of metadata fields to update

        Returns:
            bool: True if image was updated successfully, False if not found
        """
        pass

    @abstractmethod
    def find_image_by_url(self, url: str) -> dict[str, Any] | None:
        """
        Find an image by its URL in the image collection.

        Args:
            url: URL of the image to find

        Returns:
            Image dict if found, None if not found
        """
        pass

    @abstractmethod
    def find_image_by_filename(self, filename: str) -> dict[str, Any] | None:
        """
        Find an image by its filename in the image collection.

        Args:
            filename: Filename of the image to find

        Returns:
            Image dict if found, None if not found
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

    def has_text_collection(self) -> bool:
        """Check if this VDB has a text collection configured."""
        return self.text_collection is not None

    def has_image_collection(self) -> bool:
        """Check if this VDB has an image collection configured."""
        return self.image_collection is not None

    def get_text_collection_name(self) -> str | None:
        """Get the name of the text collection."""
        return self.text_collection.name if self.text_collection else None

    def get_image_collection_name(self) -> str | None:
        """Get the name of the image collection."""
        return self.image_collection.name if self.image_collection else None
