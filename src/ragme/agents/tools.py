# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from typing import Any

from src.ragme.utils.common import crawl_webpage

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


class RagMeTools:
    """A class containing all the tools for RagMe operations."""

    def __init__(self, ragme_instance):
        """
        Initialize the RagMeTools with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to vector database and methods
        """
        self.ragme = ragme_instance

    def find_urls_crawling_webpage(
        self, start_url: str, max_pages: int = 10
    ) -> list[str]:
        """
        Useful for finding all URLs on a webpage that match a search term
        Args:
            start_url (str): The starting URL to crawl
            max_pages (int): Maximum number of pages to crawl
        Returns:
            list[str]: List of URLs found
        """
        return crawl_webpage(start_url, max_pages)

    def delete_ragme_collection(self) -> str:
        """
        Reset and delete the RagMeDocs collection
        Returns:
            str: Success message
        """
        self.ragme.vector_db.cleanup()
        self.ragme.vector_db.setup()
        return "RagMeDocs collection has been reset and recreated"

    def delete_document(self, doc_id: str) -> str:
        """
        Delete a specific document from the RagMeDocs collection by ID.
        Args:
            doc_id (str): The document ID to delete
        Returns:
            str: Success or error message
        """
        try:
            success = self.ragme.delete_document(doc_id)
            if success:
                return f"Document {doc_id} deleted successfully"
            else:
                return f"Document {doc_id} not found or could not be deleted"
        except Exception as e:
            return f"Error deleting document {doc_id}: {str(e)}"

    def delete_all_documents(self) -> str:
        """
        Delete all documents from the RagMeDocs collection.
        Returns:
            str: Success message with count of deleted documents
        """
        try:
            # Get all documents first
            documents = self.ragme.list_documents(limit=1000, offset=0)
            deleted_count = 0

            for _i, doc in enumerate(documents):
                doc_id = doc.get("id")
                if doc_id:
                    success = self.ragme.delete_document(doc_id)
                    if success:
                        deleted_count += 1

            return f"Successfully deleted {deleted_count} documents from the collection"
        except Exception as e:
            return f"Error deleting documents: {str(e)}"

    def delete_documents_by_pattern(self, pattern: str) -> str:
        """
        Delete documents from the RagMeDocs collection that match a pattern in their name/URL.
        Args:
            pattern (str): Pattern to match against document names/URLs (supports regex-like patterns)
        Returns:
            str: Success message with count of deleted documents
        """
        try:
            import re

            # Get all documents first
            documents = self.ragme.list_documents(limit=1000, offset=0)
            deleted_count = 0
            matched_docs = []

            # Convert pattern to regex (handle common patterns)
            # If pattern doesn't look like regex, treat it as a simple substring match
            if not any(
                char in pattern
                for char in ["*", "+", "?", "(", ")", "[", "]", "\\", "^", "$"]
            ):
                # Simple substring match - convert to case-insensitive regex
                regex_pattern = re.escape(pattern)
            else:
                # Treat as regex pattern
                regex_pattern = pattern

            try:
                regex = re.compile(regex_pattern, re.IGNORECASE)
            except re.error:
                return f"Invalid regex pattern: {pattern}"

            # Find documents that match the pattern
            for doc in documents:
                doc_url = doc.get("url", "")
                doc_filename = doc.get("metadata", {}).get("filename", "")
                doc_original_filename = doc.get("metadata", {}).get(
                    "original_filename", ""
                )

                # Check if pattern matches any of the document identifiers
                if (
                    regex.search(doc_url)
                    or regex.search(doc_filename)
                    or regex.search(doc_original_filename)
                ):
                    matched_docs.append(doc)

            # Delete matched documents
            for doc in matched_docs:
                doc_id = doc.get("id")
                if doc_id:
                    success = self.ragme.delete_document(doc_id)
                    if success:
                        deleted_count += 1

            if deleted_count == 0:
                return f"No documents found matching pattern: {pattern}"
            else:
                return f"Successfully deleted {deleted_count} documents matching pattern: {pattern}"

        except Exception as e:
            return f"Error deleting documents by pattern: {str(e)}"

    def get_document_details(self, doc_id: int) -> dict[str, Any]:
        """
        Get detailed information about a specific document by ID.
        Args:
            doc_id (int): The document ID (starts from 1)
        Returns:
            dict: Detailed document information including full content
        """
        documents = self.ragme.list_documents(
            limit=1000, offset=0
        )  # Get all to find by ID
        # Adjust for 1-based indexing
        adjusted_id = doc_id - 1
        if adjusted_id < 0 or adjusted_id >= len(documents):
            return {"error": f"Document ID {doc_id} not found"}

        doc = documents[adjusted_id]
        return {
            "id": doc_id,
            "url": doc.get("url", "Unknown"),
            "type": doc.get("metadata", {}).get("type", "Unknown"),
            "date_added": doc.get("metadata", {}).get("date_added", "Unknown"),
            "content": doc.get("text", ""),
            "metadata": doc.get("metadata", {}),
        }

    def list_ragme_collection(
        self, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        List the contents of the RagMeDocs collection with essential information only.
        Returns a summary of documents without full text content for fast listing.
        """
        documents = self.ragme.list_documents(limit=limit, offset=offset)

        # Return only essential information for fast listing
        summary_docs = []
        for _i, doc in enumerate(documents):
            summary_doc = {
                "url": doc.get("url", "Unknown"),
                "type": doc.get("metadata", {}).get("type", "Unknown"),
                "date_added": doc.get("metadata", {}).get("date_added", "Unknown"),
                "content_length": len(doc.get("text", "")),
                "content_preview": (
                    doc.get("text", "")[:100] + "..."
                    if len(doc.get("text", "")) > 100
                    else doc.get("text", "")
                ),
            }
            summary_docs.append(summary_doc)

        return summary_docs

    def write_to_ragme_collection(self, urls=None) -> str:
        """
        Useful for writing new content to the RagMeDocs collection
        Args:
            urls (list[str]): A list of URLs to write to the RagMeDocs collection
        Returns:
            str: Success message
        """
        if urls is None:
            urls = []
        self.ragme.write_webpages_to_weaviate(urls)
        return f"Successfully added {len(urls)} URLs to the collection"

    def get_vector_db_info(self) -> str:
        """
        Report which vector database is being used and its configuration.
        Returns:
            str: Information about the current vector database
        """
        db = self.ragme.vector_db
        db_type = getattr(db, "db_type", type(db).__name__)
        config = f"Collection: {getattr(db, 'collection_name', 'unknown')}"
        return f"RagMe is currently using the '{db_type}' vector database. {config}."

    def get_all_tools(self):
        """
        Get all tools as a list of functions for use with LlamaIndex FunctionAgent.
        Returns:
            list: List of tool functions
        """
        return [
            self.write_to_ragme_collection,
            self.delete_ragme_collection,
            self.delete_document,
            self.delete_all_documents,
            self.delete_documents_by_pattern,
            self.list_ragme_collection,
            self.find_urls_crawling_webpage,
            self.get_vector_db_info,
        ]
