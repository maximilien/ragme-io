# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import asyncio
import json
import os
import warnings
from datetime import datetime
from typing import Any

import dotenv
from llama_index.readers.web import SimpleWebPageReader

from src.ragme.agents.ragme_agent import RagMeAgent
from src.ragme.vdbs.vector_db import VectorDatabase, create_vector_database

# Get environment variables
dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Check if environment variables are set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

# Filter warnings - more comprehensive suppression
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based `config`.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince211.*"
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Support for class-based `config`.*",
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*model_fields.*"
)


class RagMe:
    """A class for managing RAG (Retrieval-Augmented Generation) operations with web content using a Vector Database."""

    def __init__(
        self,
        vector_db: VectorDatabase = None,
        db_type: str = None,
        collection_name: str = None,
    ):
        """
        Initialize RagMe with a vector database.

        Args:
            vector_db: Vector database instance (if None, will create one based on db_type)
            db_type: Type of vector database to use if vector_db is None (defaults to VECTOR_DB_TYPE env var or "weaviate")
            collection_name: Name of the collection to use (defaults to configuration or "RagMeDocs")
        """
        # Get collection name from config if not provided
        if collection_name is None:
            from src.ragme.utils.config_manager import config

            # Use the new text collection method
            collection_name = config.get_text_collection_name()

        self.collection_name = collection_name

        # Get db_type from environment if not provided
        if db_type is None:
            db_type = os.getenv("VECTOR_DB_TYPE", "weaviate")

        self.db_type = db_type  # Store the db_type for reporting

        # Initialize vector database
        if vector_db is None:
            self.vector_db = create_vector_database(db_type, collection_name)
        else:
            self.vector_db = vector_db

        # Set up the database
        self.vector_db.setup()

        # Initialize agents
        self.query_agent = self.vector_db.create_query_agent()
        self.ragme_agent = RagMeAgent(self)

    # public methods

    def cleanup(self):
        """Clean up resources."""
        try:
            # Clean up vector database
            if hasattr(self, "vector_db") and self.vector_db:
                self.vector_db.cleanup()
                self.vector_db = None

            # Clean up agents
            if hasattr(self, "query_agent") and self.query_agent:
                self.query_agent = None

            if hasattr(self, "ragme_agent") and self.ragme_agent:
                self.ragme_agent = None

        except Exception as e:
            # Log the error but don't raise it to avoid breaking shutdown
            import warnings

            warnings.warn(f"Error during RagMe cleanup: {e}")

    def write_webpages_to_weaviate(self, urls: list[str]):
        """
        Write the contents of a list of URLs to the vector database.

        Args:
            urls (list[str]): A list of URLs to write to the vector database
        """
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        docs_to_write = []
        db_type = os.getenv("VECTOR_DB_TYPE", "weaviate").lower()
        if db_type == "milvus":
            from pymilvus import model

            embedding_fn = model.DefaultEmbeddingFunction()
            texts = [doc.text for doc in documents]
            vectors = embedding_fn.encode_documents(texts)
            for doc, vector in zip(documents, vectors, strict=False):
                docs_to_write.append(
                    {
                        "url": doc.id_,
                        "text": doc.text,
                        "metadata": {
                            "type": "webpage",
                            "url": doc.id_,
                            "date_added": datetime.now().isoformat(),
                        },
                        "vector": (
                            vector.tolist()
                            if hasattr(vector, "tolist")
                            else list(vector)
                        ),
                    }
                )
        else:
            # Map documents to their original URLs
            for i, doc in enumerate(documents):
                # Use the original URL from the input list
                original_url = urls[i] if i < len(urls) else doc.id_
                docs_to_write.append(
                    {
                        "url": original_url,
                        "text": doc.text,
                        "metadata": {
                            "type": "webpage",
                            "url": original_url,
                            "date_added": datetime.now().isoformat(),
                        },
                    }
                )
        self.vector_db.write_documents(docs_to_write)

    def write_json_to_weaviate(
        self, json_data: dict[str, Any], metadata: dict[str, Any] = None
    ):
        """
        Write JSON content to the vector database.

        Args:
            json_data (Dict[str, Any]): The JSON data to write
            metadata (Dict[str, Any], optional): Additional metadata to store with the content
        """
        # Convert JSON data to string for storage
        json_text = json.dumps(json_data, ensure_ascii=False)

        # Prepare metadata
        if metadata is None:
            metadata = {}

        # Add date_added to metadata
        metadata["date_added"] = datetime.now().isoformat()

        # Create document to write
        doc_to_write = {
            "url": json_data.get("filename", "filename not found"),
            "text": json_text,
            "metadata": metadata,
        }

        self.vector_db.write_documents([doc_to_write])

    def list_documents(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        """
        List documents in the vector database.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            list: List of documents with their metadata
        """
        return self.vector_db.list_documents(limit, offset)

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector database by ID.

        Args:
            document_id: ID of the document to delete

        Returns:
            bool: True if document was deleted successfully, False if not found
        """
        return self.vector_db.delete_document(document_id)

    async def run(self, query: str):
        response = await self.ragme_agent.run(query)
        return str(response)

    def reset_chat_session(self):
        """
        Reset the chat session, clearing memory and confirmation state.
        This should be called when starting a new chat session.
        """
        if hasattr(self, "ragme_agent") and self.ragme_agent:
            self.ragme_agent.reset_confirmation_state()
            # Clear the memory as well
            if hasattr(self.ragme_agent, "memory"):
                self.ragme_agent.memory.reset()


if __name__ == "__main__":
    ragme = RagMe()
    try:
        print("Give me a one URL or a list of URLs to save (separated by commas):")
        urls = input()
        if "," in urls:
            urls = urls.split(",")
        else:
            url = urls
            search_term = input("Give me a search term to find all post URLs: ")
            prefix = "/".join(url.split("/")[:-1])
            urls = ragme.find_all_post_urls(url, search_term)
            urls = [prefix + "/" + url for url in urls]
            urls = list(set(urls))
            print(f"Found the following post URLs: {urls}")
            if (
                input(
                    f"Do you want to proceed and process these {len(urls)} URLs? (y/n)"
                )
                == "n"
            ):
                print("Quitting...")
                exit()
        print(f"Processing {len(urls)} URLs")
        urls = [url.strip() for url in urls]
        ragme.write_webpages_to_weaviate(urls)
        print("Done writing to vector database")

        while True:
            print("What questions do you have about the URLs just saved?")
            query = input()
            if query.lower() == "q" or query.lower() == "quit":
                print("Quitting...")
                break
            else:
                answer = asyncio.run(ragme.run(query))
                print("Answer:")
                print(answer + "\n")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
    finally:
        ragme.cleanup()
