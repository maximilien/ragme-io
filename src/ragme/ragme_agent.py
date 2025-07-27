# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from typing import Any

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from src.ragme.common import crawl_webpage

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


class RagMeAgent:
    """A class for managing RAG agent operations with web content and document collections."""

    def __init__(self, ragme_instance):
        """
        Initialize the RagMeAgent with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to Weaviate client and methods
        """
        self.ragme = ragme_instance
        self.llm = OpenAI(model="gpt-4o-mini")
        self.agent = self._create_agent()

    def _create_agent(self):
        """
        Create the RAG agent with tools for managing the RagMeDocs collection.
        """

        def find_urls_crawling_webpage(
            start_url: str, max_pages: int = 10
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

        def delete_ragme_collection():
            """
            Reset and delete the RagMeDocs collection
            """
            # Note: This is a simplified implementation. In a real scenario,
            # you might want to add a delete_collection method to the VectorDatabase interface
            # For now, we'll just clean up and recreate the collection
            self.ragme.vector_db.cleanup()
            self.ragme.vector_db.setup()

        def delete_document(doc_id: str) -> str:
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

        def delete_all_documents() -> str:
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

        def delete_documents_by_pattern(pattern: str) -> str:
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

        def get_document_details(doc_id: int) -> dict[str, Any]:
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
            limit: int = 10, offset: int = 0
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
                    "content_preview": doc.get("text", "")[:100] + "..."
                    if len(doc.get("text", "")) > 100
                    else doc.get("text", ""),
                }
                summary_docs.append(summary_doc)

            return summary_docs

        def write_to_ragme_collection(urls=None):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            if urls is None:
                urls = []
            self.ragme.write_webpages_to_weaviate(urls)

        def query_agent(query: str):
            """
            Useful for asking questions about RagMe docs and website
            Args:
                query (str): The query to ask about stored documents
            Returns:
                str: The response with relevant document content
            """
            # Use direct vector search as the primary method
            try:
                # Get documents from the collection - increase limit to find more documents
                documents = self.ragme.list_documents(limit=100, offset=0)

                # Improved keyword matching for chunked documents
                relevant_docs = []
                query_lower = query.lower()
                query_words = query_lower.split()

                for _i, doc in enumerate(documents):
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
                            {"doc": doc, "matches": matches, "text_length": len(text)}
                        )

                if relevant_docs:
                    # Sort by relevance (more matches first, then by text length)
                    relevant_docs.sort(key=lambda x: (-x["matches"], -x["text_length"]))

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
                    if len(content) > 1500:
                        content = content[:1500] + "..."

                    result = f"Based on the stored documents, here's what I found:\n\nURL: {url}{chunk_info}\n\nContent: {content}"
                    return result
                else:
                    return f"I couldn't find any relevant information about '{query}' in the stored documents."

            except Exception as e:
                return f"Error searching documents: {str(e)}"

        def get_vector_db_info() -> str:
            """
            Report which vector database is being used and its configuration.
            Returns:
                str: Information about the current vector database
            """
            db = self.ragme.vector_db
            db_type = getattr(db, "db_type", type(db).__name__)
            config = f"Collection: {getattr(db, 'collection_name', 'unknown')}"
            return (
                f"RagMe is currently using the '{db_type}' vector database. {config}."
            )

        return FunctionAgent(
            tools=[
                write_to_ragme_collection,
                delete_ragme_collection,
                delete_document,
                delete_all_documents,
                delete_documents_by_pattern,
                list_ragme_collection,
                find_urls_crawling_webpage,
                query_agent,
                get_vector_db_info,
            ],
            llm=self.llm,
            system_prompt="""You are a helpful assistant that can write
            the contents of urls to RagMeDocs
            collection, as well as answering questions about stored documents.

            MANDATORY RULE: For ANY question about documents, content, or information, you MUST call query_agent(query) first.

            DO NOT provide any response about document content without calling query_agent(query).
            DO NOT use any other method to search documents.
            ALWAYS use query_agent(query) for document queries.

            The query_agent function searches through all stored documents to find relevant information.
            Return the query_agent result directly to the user without modification.

            You can also ask questions about the RagMeDocs collection directly using list_ragme_collection.
            You can also answer which vector database is being used if asked.

            You can also delete documents from the collection:
            - Use delete_document(doc_id) to delete a specific document by its ID
            - Use delete_all_documents() to delete all documents from the collection
            - Use delete_documents_by_pattern(pattern) to delete documents matching a pattern in their name/URL
            - When users ask to "delete docs" or similar, you can use these functions to help them
            - For pattern-based deletion, users can say things like "del all docs with name pattern test_integration.pdf" or "delete documents matching pattern test_*"
            """,
        )

    async def run(self, query: str):
        """
        Run a query through the RAG agent.

        Args:
            query (str): The query to process

        Returns:
            The response from the agent
        """
        response = await self.agent.run(query)
        return str(response)
