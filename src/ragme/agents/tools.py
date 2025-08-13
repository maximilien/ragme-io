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
        Initialize RagMeTools with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to vector
                           database and methods
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

    def delete_document_by_url(self, url: str) -> str:
        """
        Delete a specific document from the RagMeDocs collection by URL.
        Args:
            url (str): The document URL to delete
        Returns:
            str: Success or error message
        """
        try:
            # First find the document by URL
            document = self.ragme.vector_db.find_document_by_url(url)
            if document is None:
                return f"Document with URL {url} not found in the collection"

            # Delete the document using its ID
            doc_id = document.get("id")
            if not doc_id:
                return f"Document with URL {url} found but has no valid ID"

            success = self.ragme.delete_document(doc_id)
            if success:
                return f"Document with URL {url} deleted successfully"
            else:
                return f"Document with URL {url} could not be deleted"
        except Exception as e:
            return f"Error deleting document with URL {url}: {str(e)}"

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
        Delete documents from the RagMeDocs collection that match a pattern
        in their name/URL.

        Args:
            pattern (str): Pattern to match against document names/URLs
                          (supports regex-like patterns)
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
                return (
                    f"Successfully deleted {deleted_count} documents "
                    f"matching pattern: {pattern}"
                )

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

        # Normalize URLs to ensure they have a protocol
        normalized_urls = []
        skipped_urls = []

        for url in urls:
            if url and not url.startswith(("http://", "https://")):
                normalized_url = f"https://{url}"
            else:
                normalized_url = url

            # Check if a document with this URL already exists (ignoring protocol)
            url_without_protocol = normalized_url.replace("https://", "").replace(
                "http://", ""
            )
            existing_doc = None

            # Try to find existing document by checking both http and https versions
            for protocol in ["https://", "http://"]:
                test_url = f"{protocol}{url_without_protocol}"
                existing_doc = self.ragme.vector_db.find_document_by_url(test_url)
                if existing_doc:
                    break

            if existing_doc:
                skipped_urls.append(url)
            else:
                normalized_urls.append(normalized_url)

        if not normalized_urls:
            if skipped_urls:
                return "The document is already present in the collection"
            else:
                return "No valid URLs provided"

        try:
            self.ragme.write_webpages_to_weaviate(normalized_urls)

            # Build response message
            added_count = len(normalized_urls)
            skipped_count = len(skipped_urls)

            if skipped_count > 0:
                return f"Successfully added {added_count} URLs to the collection. The document is already present in the collection"
            else:
                return f"Successfully added {added_count} URLs to the collection"

        except Exception as e:
            return f"Error adding URLs to collection: {str(e)}"

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

    def count_documents(self, date_filter: str = "all") -> str:
        """
        Count the total number of documents in the collection with optional
        date filtering.

        Args:
            date_filter: Filter by date - 'all', 'current', 'month', 'year'

        Returns:
            str: Formatted count message
        """
        try:
            # Use the efficient count method from vector database
            if hasattr(self.ragme.vector_db, "count_documents"):
                count = self.ragme.vector_db.count_documents(date_filter)
            else:
                # Fallback to list and count
                documents = self.ragme.list_documents(limit=10000, offset=0)

                if date_filter == "all":
                    count = len(documents)
                else:
                    # Apply date filtering
                    import datetime

                    now = datetime.datetime.now()

                    if date_filter == "current":
                        start_of_week = now - datetime.timedelta(days=now.weekday())
                        cutoff = start_of_week.isoformat()
                    elif date_filter == "month":
                        cutoff = now.replace(day=1).isoformat()
                    elif date_filter == "year":
                        cutoff = now.replace(month=1, day=1).isoformat()
                    else:
                        cutoff = None

                    if cutoff:
                        count = 0
                        for doc in documents:
                            date_added = doc.get("metadata", {}).get("date_added", "")
                            if date_added >= cutoff:
                                count += 1
                    else:
                        count = len(documents)

            # Format the response nicely
            filter_text = {
                "all": "total",
                "current": "from this week",
                "month": "from this month",
                "year": "from this year",
            }.get(date_filter, f"with filter '{date_filter}'")

            return f"There are {count:,} documents {filter_text} in the collection."

        except Exception as e:
            return f"Error counting documents: {str(e)}"

    def write_image_to_collection(self, image_url: str) -> str:
        """
        Add an image from a URL to the RagMe image collection.

        Args:
            image_url: The URL of the image to add to the collection

        Returns:
            str: Success or error message
        """
        try:
            from ..utils.config_manager import config
            from ..utils.image_processor import image_processor
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)
            image_vdb.setup()

            # Process the image
            processed_data = image_processor.process_image(image_url)

            # Encode image to base64
            base64_data = image_processor.encode_image_to_base64(image_url)

            # Check if the vector database supports images
            if image_vdb.supports_images():
                # Write to image collection
                image_vdb.write_images(
                    [
                        {
                            "url": image_url,
                            "image_data": base64_data,
                            "metadata": processed_data,
                        }
                    ]
                )
            else:
                # Fallback: store as text document with image metadata
                classification = processed_data.get("classification", {})
                top_pred = classification.get("top_prediction", {})
                label = top_pred.get("label", "unknown")

                text_representation = (
                    f"Image: {image_url}\n"
                    f"Classification: {label}\n"
                    f"Metadata: {str(processed_data)}"
                )
                image_vdb.write_documents(
                    [
                        {
                            "url": image_url,
                            "text": text_representation,
                            "metadata": processed_data,
                        }
                    ]
                )

            return f"Successfully added image {image_url} to the collection"

        except Exception as e:
            return f"Error adding image to collection: {str(e)}"

    def list_image_collection(self, limit: int = 10, offset: int = 0) -> str:
        """
        List images in the RagMe image collection.

        Args:
            limit: Maximum number of images to return (default: 10)
            offset: Number of images to skip (default: 0)

        Returns:
            str: Formatted list of images with metadata
        """
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List images
            images = image_vdb.list_documents(limit=limit, offset=offset)

            if not images:
                return "No images found in the collection."

            result = f"Found {len(images)} images in the collection:\n\n"

            for i, img in enumerate(images, offset + 1):
                metadata = img.get("metadata", {})
                if isinstance(metadata, str):
                    import json

                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})

                result += f"{i}. Image ID: {img.get('id', 'unknown')}\n"
                result += (
                    f"   URL: {img.get('url', metadata.get('source', 'unknown'))}\n"
                )

                if top_prediction:
                    label = top_prediction.get("label", "unknown")
                    confidence = top_prediction.get("confidence", 0)
                    result += (
                        f"   Classification: {label} ({confidence:.2%} confidence)\n"
                    )

                if metadata.get("date_added"):
                    result += f"   Added: {metadata.get('date_added')}\n"

                result += "\n"

            return result

        except Exception as e:
            return f"Error listing images: {str(e)}"

    def delete_image_from_collection(self, image_id: str) -> str:
        """
        Delete an image from the RagMe image collection by ID.

        Args:
            image_id: The ID of the image to delete

        Returns:
            str: Success or error message
        """
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # Delete the image
            success = image_vdb.delete_document(image_id)

            if success:
                return f"Successfully deleted image with ID: {image_id}"
            else:
                return f"Image with ID {image_id} not found"

        except Exception as e:
            return f"Error deleting image: {str(e)}"

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
            self.delete_document_by_url,
            self.delete_all_documents,
            self.delete_documents_by_pattern,
            self.list_ragme_collection,
            self.find_urls_crawling_webpage,
            self.get_vector_db_info,
            self.count_documents,
            # Image-related tools
            self.write_image_to_collection,
            self.list_image_collection,
            self.delete_image_from_collection,
        ]
