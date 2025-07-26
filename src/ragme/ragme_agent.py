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
        """Create and return a FunctionAgent with RAG-specific tools."""

        def find_urls_crawling_webpage(
            start_url: str, max_pages: int = 10
        ) -> list[str]:
            """
            Crawl a webpage and find all web pages under it.
            Args:
                start_url (str): The URL to start crawling from
                max_pages (int): The maximum number of pages to crawl
            Returns:
                list[str]: A list of URLs found
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

                for doc in documents:
                    doc_id = doc.get("id")
                    if doc_id:
                        success = self.ragme.delete_document(doc_id)
                        if success:
                            deleted_count += 1

                return f"Successfully deleted {deleted_count} documents from the collection"
            except Exception as e:
                return f"Error deleting documents: {str(e)}"

        def get_document_details(doc_id: int) -> dict[str, Any]:
            """
            Get detailed information about a specific document by ID.
            Args:
                doc_id (int): The document ID/index
            Returns:
                dict: Detailed document information including full content
            """
            documents = self.ragme.list_documents(
                limit=1000, offset=0
            )  # Get all to find by ID
            if doc_id < 0 or doc_id >= len(documents):
                return {"error": f"Document ID {doc_id} not found"}

            doc = documents[doc_id]
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
            for i, doc in enumerate(documents):
                summary_doc = {
                    "id": i + offset,  # Index for reference
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

        def write_to_ragme_collection(urls=list[str]):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            self.ragme.write_webpages_to_weaviate(urls)

        def query_agent(query: str):
            """
            Useful for asking questions about RagMe docs and website
            Args:
                query (str): The query to ask the QueryAgent
            Returns:
                str: The response from the QueryAgent
            """
            try:
                # Try to use the QueryAgent first
                response = self.ragme.query_agent.run(query)
                return response
            except Exception as e:
                # Fallback: use direct vector search if QueryAgent fails
                try:
                    # Get documents from the collection
                    documents = self.ragme.list_documents(limit=10, offset=0)

                    # Simple keyword matching for now
                    relevant_docs = []
                    query_lower = query.lower()

                    for doc in documents:
                        text = doc.get("text", "").lower()
                        if any(word in text for word in query_lower.split()):
                            relevant_docs.append(doc)

                    if relevant_docs:
                        # Return the most relevant document's content
                        most_relevant = relevant_docs[0]
                        content = most_relevant.get("text", "")
                        url = most_relevant.get("url", "")

                        # Truncate content if too long
                        if len(content) > 1000:
                            content = content[:1000] + "..."

                        return f"Based on the stored documents, here's what I found:\n\nURL: {url}\n\nContent: {content}"
                    else:
                        return f"I couldn't find any relevant information about '{query}' in the stored documents. The QueryAgent also encountered an error: {str(e)}"

                except Exception as fallback_error:
                    return f"Error querying the agent: {str(e)}. Fallback also failed: {str(fallback_error)}"

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
                list_ragme_collection,
                find_urls_crawling_webpage,
                query_agent,
                get_vector_db_info,
            ],
            llm=self.llm,
            system_prompt="""You are a helpful assistant that can write
            the contents of urls to RagMeDocs
            collection, as well as forwarding questions to a QueryAgent.

            IMPORTANT: When users ask questions about content that might be in the RagMeDocs collection,
            you should ALWAYS use the query_agent function to search through the stored documents first.
            The QueryAgent will search through the contents of the RagMeDocs collection to find relevant information.

            You can also ask questions about the RagMeDocs collection directly using list_ragme_collection.
            If the query is not about the RagMeDocs collection, you can ask the QueryAgent to answer the question.
            You can also answer which vector database is being used if asked.

            You can also delete documents from the collection:
            - Use delete_document(doc_id) to delete a specific document by its ID
            - Use delete_all_documents() to delete all documents from the collection
            - When users ask to "delete docs" or similar, you can use these functions to help them
            """,
        )

    def run(self, query: str):
        """
        Run a query through the RAG agent.

        Args:
            query (str): The query to process

        Returns:
            The response from the agent
        """
        return self.agent.run(query)
