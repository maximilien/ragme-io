# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import asyncio
import json
import os
import warnings
from typing import List, Dict, Any

from llama_index.readers.web import SimpleWebPageReader

import dotenv

from src.ragme.ragme_agent import RagMeAgent
from src.ragme.vector_db import create_vector_database, VectorDatabase

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
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")


class RagMe:
    """A class for managing RAG (Retrieval-Augmented Generation) operations with web content using a Vector Database."""
    
    def __init__(self, vector_db: VectorDatabase = None, db_type: str = "weaviate", collection_name: str = "RagMeDocs"):
        """
        Initialize RagMe with a vector database.
        
        Args:
            vector_db: Vector database instance (if None, will create one based on db_type)
            db_type: Type of vector database to use if vector_db is None
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name
        
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
        if self.vector_db:
            self.vector_db.cleanup()

    def write_webpages_to_weaviate(self, urls: list[str]):
        """
        Write the contents of a list of URLs to the vector database.
        Args:
            urls (list[str]): A list of URLs to write to the vector database
        """
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        
        # Convert documents to the format expected by the vector database
        docs_to_write = []
        for doc in documents:
            docs_to_write.append({
                "url": doc.id_,
                "text": doc.text,
                "metadata": {"type": "webpage", "url": doc.id_}
            })
        
        self.vector_db.write_documents(docs_to_write)
    
    def write_json_to_weaviate(self, json_data: Dict[str, Any], metadata: Dict[str, Any] = None):
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
        
        # Create document to write
        doc_to_write = {
            "url": json_data.get("filename", "filename not found"),
            "text": json_text,
            "metadata": metadata
        }
        
        self.vector_db.write_documents([doc_to_write])

    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents in the vector database.
        
        Args:
            limit (int): Maximum number of documents to return
            offset (int): Number of documents to skip
            
        Returns:
            List[Dict[str, Any]]: List of documents with their properties
        """
        return self.vector_db.list_documents(limit, offset)

    async def run(self, query: str):
        response = await self.ragme_agent.run(
            user_msg=query
        )
        return str(response)

if __name__ == "__main__":
    ragme = RagMe()
    try:
        print("Give me a one URL or a list of URLs to save (separated by commas):")
        urls = input()
        if ',' in urls:
            urls = urls.split(',')
        else:
            url = urls
            search_term = input("Give me a search term to find all post URLs: ")
            prefix = '/'.join(url.split('/')[:-1])
            urls = ragme.find_all_post_urls(url, search_term)
            urls = [prefix + '/' + url for url in urls]
            urls = list(set(urls))
            print(f"Found the following post URLs: {urls}")
            if input(f"Do you want to proceed and process these {len(urls)} URLs? (y/n)") == 'n':
                print("Quitting...")
                exit()
        print(f"Processing {len(urls)} URLs")
        urls = [url.strip() for url in urls]
        ragme.write_webpages_to_weaviate(urls)
        print("Done writing to vector database")
        
        while True:
            print("What questions do you have about the URLs just saved?")
            query = input()
            if query.lower() == 'q' or query.lower() == 'quit':
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
