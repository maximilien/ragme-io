# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from typing import Any

from src.ragme.utils.common import (
    crawl_webpage,
    filter_items_by_date_range,
    parse_date_query,
)

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
            # First get the document to check if it has a storage path
            documents = self.ragme.list_documents(limit=1000, offset=0)
            document = next(
                (doc for doc in documents if str(doc.get("id")) == doc_id), None
            )

            storage_path = None
            storage_deleted = False

            if document:
                storage_path = document.get("metadata", {}).get("storage_path")
                if storage_path:
                    try:
                        from ..utils.config_manager import config
                        from ..utils.storage import StorageService

                        storage_service = StorageService(config)
                        storage_deleted = storage_service.delete_file(storage_path)
                        if storage_deleted:
                            print(f"Deleted document from storage: {storage_path}")
                        else:
                            print(
                                f"Failed to delete document from storage: {storage_path}"
                            )
                    except Exception as storage_error:
                        print(
                            f"Error deleting document from storage {storage_path}: {storage_error}"
                        )
                        # Continue with vector database deletion even if storage deletion fails

            # Delete from vector database
            success = self.ragme.delete_document(doc_id)
            if success:
                message = f"Document {doc_id} deleted successfully"
                if storage_path and storage_deleted:
                    message += f" (also deleted from storage: {storage_path})"
                elif storage_path and not storage_deleted:
                    message += f" (failed to delete from storage: {storage_path})"
                return message
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
            storage_deleted_count = 0

            for _i, doc in enumerate(documents):
                doc_id = doc.get("id")
                if doc_id:
                    # Check if document has a storage path and delete from storage if it exists
                    storage_path = doc.get("metadata", {}).get("storage_path")
                    if storage_path:
                        try:
                            from ..utils.config_manager import config
                            from ..utils.storage import StorageService

                            storage_service = StorageService(config)
                            storage_deleted = storage_service.delete_file(storage_path)
                            if storage_deleted:
                                print(f"Deleted document from storage: {storage_path}")
                                storage_deleted_count += 1
                            else:
                                print(
                                    f"Failed to delete document from storage: {storage_path}"
                                )
                        except Exception as storage_error:
                            print(
                                f"Error deleting document from storage {storage_path}: {storage_error}"
                            )
                            # Continue with vector database deletion even if storage deletion fails

                    # Delete from vector database
                    success = self.ragme.delete_document(doc_id)
                    if success:
                        deleted_count += 1

            message = (
                f"Successfully deleted {deleted_count} documents from the collection"
            )
            if storage_deleted_count > 0:
                message += f" (also deleted {storage_deleted_count} files from storage)"

            return message
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

    def list_ragme_collection(self, limit: int = 10, offset: int = 0) -> str:
        """
        List the contents of the RagMeDocs collection with essential information only.
        Returns a formatted string with document summaries for fast listing.
        """
        documents = self.ragme.list_documents(limit=limit, offset=offset)

        if not documents:
            return "No documents found in the collection."

        result = f"Found {len(documents)} documents in the collection:\n\n"

        for i, doc in enumerate(documents, offset + 1):
            metadata = doc.get("metadata", {})

            result += f"{i}. Document ID: {doc.get('id', 'unknown')}\n"
            result += f"   URL: {doc.get('url', 'unknown')}\n"
            result += f"   Type: {metadata.get('type', 'unknown')}\n"

            if metadata.get("date_added"):
                result += f"   Added: {metadata.get('date_added')}\n"

            result += f"   Content Length: {len(doc.get('text', ''))} characters\n"

            # Add a preview of the content
            content_preview = (
                doc.get("text", "")[:100] + "..."
                if len(doc.get("text", "")) > 100
                else doc.get("text", "")
            )
            result += f"   Preview: {content_preview}\n"

            result += "\n"

        return result

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

        # Handle new collection structure
        if hasattr(db, "text_collection") and db.text_collection:
            text_collection = db.text_collection.name
        elif hasattr(db, "collection_name"):
            text_collection = getattr(db, "collection_name", "unknown")
        else:
            text_collection = "unknown"

        if hasattr(db, "image_collection") and db.image_collection:
            image_collection = db.image_collection.name
            config = f"Text Collection: {text_collection}, Image Collection: {image_collection}"
        else:
            config = f"Text Collection: {text_collection}"

        return f"RagMe is currently using the '{db_type}' vector database. {config}."

    def count_documents(self, date_filter: str = "all") -> str:
        """
        Count the total number of documents in the collection with optional
        date filtering.

        Args:
            date_filter: Filter by date - 'all', 'today', 'week', 'month', 'year'

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

                    if date_filter == "today":
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
            import os

            from ..utils.image_processor import image_processor
            from ..vdbs.vector_db_factory import create_vector_database

            # Create image vector database using the configured database type
            db_type = os.getenv("VECTOR_DB_TYPE", "weaviate")
            image_vdb = create_vector_database(db_type)
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
            str: Formatted list of images with metadata and image previews
        """
        try:
            # Use the existing vector database from RagMe instance
            # Create image vector database for listing images
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List images from image collection
            images = image_vdb.list_images(limit=limit, offset=offset)

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

                # Get image ID and filename for preview
                img_id = img.get("id", "unknown")
                filename = metadata.get("filename", img.get("url", "unknown"))

                result += f"{i}. Image ID: {img_id}\n"
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

                # Add image preview using the special format that frontend can detect
                result += f"\n[IMAGE:{img_id}:{filename}]\n"
                result += "\n"

            return result

        except Exception as e:
            return f"Error listing images: {str(e)}"

    def delete_image_from_collection(self, image_id: str) -> str:
        """
        Delete an image from the RagMe image collection by ID or filename.

        Args:
            image_id: The ID or filename of the image to delete

        Returns:
            str: Success or error message
        """
        try:
            import os
            import re

            from ..vdbs.vector_db_factory import create_vector_database

            # Create image vector database using the configured database type
            db_type = os.getenv("VECTOR_DB_TYPE", "weaviate")
            image_vdb = create_vector_database(db_type)

            # Check if the input looks like a UUID (typical image ID format)
            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                re.IGNORECASE,
            )

            actual_image_id = image_id
            image_document = None

            # If it doesn't look like a UUID, try to find by filename
            if not uuid_pattern.match(image_id):
                # Try to find the image by filename
                image_document = image_vdb.find_image_by_filename(image_id)
                if image_document:
                    actual_image_id = image_document.get("id")
                    if not actual_image_id:
                        return f"Image with filename '{image_id}' found but has no ID"
                else:
                    return f"Image with filename '{image_id}' not found"
            else:
                # If it looks like a UUID, find the image by ID
                images = image_vdb.list_images(limit=1000, offset=0)
                image_document = next(
                    (img for img in images if str(img.get("id")) == image_id), None
                )

            # Check if image has a storage path and delete from storage if it exists
            storage_path = None
            storage_deleted = False

            if image_document:
                storage_path = image_document.get("metadata", {}).get("storage_path")
                if storage_path:
                    try:
                        from ..utils.config_manager import config
                        from ..utils.storage import StorageService

                        storage_service = StorageService(config)
                        storage_deleted = storage_service.delete_file(storage_path)
                        if storage_deleted:
                            print(f"Deleted image from storage: {storage_path}")
                        else:
                            print(
                                f"Failed to delete image from storage: {storage_path}"
                            )
                    except Exception as storage_error:
                        print(
                            f"Error deleting image from storage {storage_path}: {storage_error}"
                        )
                        # Continue with vector database deletion even if storage deletion fails

            # Delete the image using the actual ID
            success = image_vdb.delete_image(actual_image_id)

            if success:
                message = "Successfully deleted image"
                if actual_image_id != image_id:
                    message += f" '{image_id}' (ID: {actual_image_id})"
                else:
                    message += f" with ID: {image_id}"

                if storage_path and storage_deleted:
                    message += f" (also deleted from storage: {storage_path})"
                elif storage_path and not storage_deleted:
                    message += f" (failed to delete from storage: {storage_path})"

                return message
            else:
                return f"Image with ID {actual_image_id} not found"

        except Exception as e:
            return f"Error deleting image: {str(e)}"

    def list_documents_by_datetime(
        self, date_query: str, limit: int = 10, offset: int = 0
    ) -> str:
        """
        List documents in the collection filtered by a natural language date query.

        Args:
            date_query: Natural language date query (e.g., "yesterday", "today", "last week", "3 days ago")
            limit: Maximum number of documents to return (default: 10)
            offset: Number of documents to skip (default: 0)

        Returns:
            str: Formatted list of documents within the specified date range
        """
        try:
            # Parse the date query into a date range
            date_range = parse_date_query(date_query)
            if not date_range:
                return f"Could not understand the date query '{date_query}'. Supported formats: today, yesterday, this week, last week, this month, last month, this year, last year, 'X days ago', 'X weeks ago', 'X months ago'"

            start_date, end_date = date_range

            # Get all documents first
            all_documents = self.ragme.list_documents(limit=1000, offset=0)

            # Filter by date range
            filtered_documents = filter_items_by_date_range(
                all_documents, start_date, end_date
            )

            # Apply pagination
            total_count = len(filtered_documents)
            paginated_documents = filtered_documents[offset : offset + limit]

            if not paginated_documents:
                return f"No documents found for {date_query} (date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')})"

            result = f"Found {total_count} documents for {date_query} (showing {len(paginated_documents)}):\n\n"

            for i, doc in enumerate(paginated_documents, offset + 1):
                metadata = doc.get("metadata", {})

                result += f"{i}. Document ID: {doc.get('id', 'unknown')}\n"
                result += f"   URL: {doc.get('url', 'unknown')}\n"
                result += f"   Type: {metadata.get('type', 'unknown')}\n"

                if metadata.get("date_added"):
                    result += f"   Added: {metadata.get('date_added')}\n"

                result += f"   Content Length: {len(doc.get('text', ''))} characters\n"

                # Add a preview of the content
                content_preview = (
                    doc.get("text", "")[:100] + "..."
                    if len(doc.get("text", "")) > 100
                    else doc.get("text", "")
                )
                result += f"   Preview: {content_preview}\n"
                result += "\n"

            return result

        except Exception as e:
            return f"Error listing documents by datetime: {str(e)}"

    def list_images_by_datetime(
        self, date_query: str, limit: int = 10, offset: int = 0
    ) -> str:
        """
        List images in the collection filtered by a natural language date query.

        Args:
            date_query: Natural language date query (e.g., "yesterday", "today", "last week", "3 days ago")
            limit: Maximum number of images to return (default: 10)
            offset: Number of images to skip (default: 0)

        Returns:
            str: Formatted list of images within the specified date range
        """
        try:
            # Parse the date query into a date range
            date_range = parse_date_query(date_query)
            if not date_range:
                return f"Could not understand the date query '{date_query}'. Supported formats: today, yesterday, this week, last week, this month, last month, this year, last year, 'X days ago', 'X weeks ago', 'X months ago'"

            start_date, end_date = date_range

            # Get all images first
            # Create image vector database for listing images
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List all images from image collection
            all_images = image_vdb.list_images(limit=1000, offset=0)

            # Filter by date range
            filtered_images = filter_items_by_date_range(
                all_images, start_date, end_date
            )

            # Apply pagination
            total_count = len(filtered_images)
            paginated_images = filtered_images[offset : offset + limit]

            if not paginated_images:
                return f"No images found for {date_query} (date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')})"

            result = f"Found {total_count} images for {date_query} (showing {len(paginated_images)}):\n\n"

            for i, img in enumerate(paginated_images, offset + 1):
                metadata = img.get("metadata", {})
                if isinstance(metadata, str):
                    import json

                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})

                # Get image ID and filename for preview
                img_id = img.get("id", "unknown")
                filename = metadata.get("filename", img.get("url", "unknown"))

                result += f"{i}. Image ID: {img_id}\n"
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

                # Add image preview using the special format that frontend can detect
                result += f"\n[IMAGE:{img_id}:{filename}]\n"
                result += "\n"

            return result

        except Exception as e:
            return f"Error listing images by datetime: {str(e)}"

    def get_images_by_date_range_with_data(self, date_query: str) -> list[dict]:
        """
        Get images from a date range with their OCR text and classification data.
        This tool is designed for use by the QueryAgent to access image data for summarization.

        Args:
            date_query (str): Natural language date query (e.g., "today", "yesterday", "this week", "last week")

        Returns:
            list[dict]: List of images with OCR text and classification data
        """
        try:
            # Parse the date query into a date range
            date_range = parse_date_query(date_query)
            if not date_range:
                return []

            start_date, end_date = date_range

            # Create image vector database for listing images
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List all images from image collection
            all_images = image_vdb.list_images(limit=1000, offset=0)

            # Filter by date range
            filtered_images = filter_items_by_date_range(
                all_images, start_date, end_date
            )

            # Process each image to extract OCR text and classification data
            processed_images = []
            for img in filtered_images:
                metadata = img.get("metadata", {})
                if isinstance(metadata, str):
                    import json

                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                # Extract OCR text
                ocr_content = metadata.get("ocr_content", {})
                ocr_text = ocr_content.get("extracted_text", "") if ocr_content else ""

                # Extract classification data
                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})
                label = top_prediction.get("label", "unknown")
                confidence = top_prediction.get("confidence", 0)

                # Create processed image data
                processed_image = {
                    "id": img.get("id", "unknown"),
                    "url": img.get("url", "unknown"),
                    "filename": metadata.get("filename", "unknown"),
                    "date_added": metadata.get("date_added", "unknown"),
                    "ocr_text": ocr_text,
                    "classification": {"label": label, "confidence": confidence},
                    "has_ocr": bool(ocr_text.strip()),
                    "metadata": metadata,
                }

                processed_images.append(processed_image)

            return processed_images

        except Exception:
            return []

    def get_todays_images_with_data(self) -> list[dict]:
        """
        Get today's images with their OCR text and classification data.
        This tool is designed for use by the QueryAgent to access image data for summarization.
        (Convenience method that calls get_images_by_date_range_with_data)

        Returns:
            list[dict]: List of today's images with OCR text and classification data
        """
        return self.get_images_by_date_range_with_data("today")

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
            self.list_documents_by_datetime,
            self.find_urls_crawling_webpage,
            self.get_vector_db_info,
            self.count_documents,
            # Image-related tools
            self.write_image_to_collection,
            self.list_image_collection,
            self.list_images_by_datetime,
            self.delete_image_from_collection,
            self.get_todays_images_with_data,
            self.get_images_by_date_range_with_data,
        ]
