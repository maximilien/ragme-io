# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config` is deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic._internal._config")

import base64
import json
import logging
import os
import requests

from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from PIL import Image, ExifTags
from exif import Image as ExifImage
from bs4 import BeautifulSoup

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.readers.web import SimpleWebPageReader
from pydantic import BaseModel, Field
import weaviate
from weaviate.auth import Auth
from weaviate.agents.query import QueryAgent
from weaviate.classes.config import Configure, Property, DataType

from src.ragme.common import crawl_webpage

import dotenv

dotenv.load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")

# Check if environment variables are set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")
if not WEAVIATE_API_KEY:
    raise ValueError("WEAVIATE_API_KEY is not set")
if not WEAVIATE_URL:
    raise ValueError("WEAVIATE_URL is not set")

# Filter warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")
logging.getLogger("httpx").setLevel(logging.WARNING)

class RagMe:
    """A class for managing RAG (Retrieval-Augmented Generation) operations with web content using a Vector Database."""
    
    def __init__(self):
        self.docs_collection_name = "RagMeDocs"
        self.images_collection_name = "RagMeImages"
        self.weeviate_client, self.query_agent, self.ragme_agent = None, None, None

        self._create_weaviate_client()
        self._setup_weaviate()
        
        self.query_agent = self._create_query_agent()
        self.ragme_agent = self._create_ragme_agent()
    
    # private methods

    def _create_weaviate_client(self):
        if not self.weeviate_client:
            self.weeviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=WEAVIATE_URL,
                auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
            )
        return self.weeviate_client
    
    def _setup_weaviate(self):
        # Create the RagMeDocs collection
        if not self.weeviate_client.collections.exists(self.docs_collection_name):
            self.weeviate_client.collections.create(
                self.docs_collection_name,
                description="A dataset with the contents of RagMe docs and website",
                vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                properties=[
                    Property(name="url", data_type=DataType.TEXT, description="the source URL of the webpage"),
                    Property(name="text", data_type=DataType.TEXT, description="the content of the webpage"),
                    Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
            ])
        # Create the RagMeImages collection
        if not self.weeviate_client.collections.exists(self.images_collection_name):
            try:
                self.weeviate_client.collections.create(
                    self.images_collection_name,
                    description="A dataset with the contents of RagMe images",
                    vectorizer_config=Configure.Vectorizer.multi2vec_google(image_fields=["image"]),
                    properties=[
                        Property(name="image", data_type=DataType.BLOB, description="the base64 encoded image"),
                        Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
                    ]
                )
            except Exception as e:
                print("multi2vec-google not available or not supporting images, falling back to text2vec-weaviate.")
                self.weeviate_client.collections.create(
                    self.images_collection_name,
                    description="A dataset with the contents of RagMe images",
                    vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                    properties=[
                        Property(name="image", data_type=DataType.BLOB, description="the base64 encoded image"),
                        Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
                    ]
                )

    def _create_query_agent(self):
        return QueryAgent(client=self.weeviate_client, collections=[self.docs_collection_name, self.images_collection_name])

    def _create_ragme_agent(self):
        llm = OpenAI(model="gpt-4o-mini")

        def find_urls_crawling_webpage(start_url: str, max_pages: int = 10) -> list[str]:
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
            self.weeviate_client.collections.delete(self.docs_collection_name)

        def list_ragme_collection(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            List the contents of the RagMeDocs collection
            """
            return self.list_documents()

        def write_images_to_ragme_collection(image_urls=list[str], metadata: Dict[str, Any] = None):
            """
            Useful for writing new content to the RagMeImages collection
            Args:
                image_urls (list[str]): A list of image URLs to write to the RagMeImages collection
                metadata (Dict[str, Any], optional): Additional metadata to store with the content
            """
            self.write_images_to_weaviate(image_urls, metadata)

        def write_to_ragme_collection(urls=list[str]):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            self.write_webpages_to_weaviate(urls)

        def query_agent(query: str) -> str:
            """
            Useful for asking questions about RagMe docs and website
            Args:
                query (str): The query to ask the QueryAgent
            Returns:
                str: The response from the QueryAgent
            """
            response = self.query_agent.run(query)
            return response.final_answer

        return FunctionAgent(
            tools=[write_to_ragme_collection, write_images_to_ragme_collection, delete_ragme_collection, list_ragme_collection, find_urls_crawling_webpage, query_agent],
            llm=llm,
            system_prompt="""You are a helpful assistant that can write the
            contents of urls to RagMeDocs collection,
            as well as forwarding questions to a QueryAgent""",
        )
    
    def _get_image_metadata(self, image_url: str) -> Dict[str, Any]:
        """
        Get the metadata of an image
        """
        try:
            response = requests.get(image_url)
            image = ExifImage(response.content)
            metadata = {
                "type": "image",
                "url": image_url,
                "exif": {}
            }
            for tag in image.list_all():
                try:
                    metadata["exif"][tag] = str(image.get(tag))
                except:
                    continue
            return metadata
        except Exception as e:
            print(f"Error getting image metadata: {e}")
            return {"type": "image", "url": image_url}
    
    # public methods

    def cleanup(self):
        if self.weeviate_client:
            self.weeviate_client.close()

    def write_images_to_weaviate(self, image_urls: list[str], metadata: Dict[str, Any] = None):
        """
        Write an image to the RagMeImages collection in Weaviate.
        Args:
            image_urls (list[str]): The URLs of the images to write to the RagMeImages collection
        """
        collection = self.weeviate_client.collections.get(self.images_collection_name)
        with collection.batch.dynamic() as batch:
            for image_url in image_urls:
                if metadata is None:
                    metadata = self._get_image_metadata(image_url)
                
                with open(image_url, "rb") as file:
                    image_data = file.read()
                    base64_encoding = base64.b64encode(image_data).decode("utf-8")
                    data_properties = {
                        "image": base64_encoding,
                    }
                    metadata_text = json.dumps(metadata, ensure_ascii=False)
                    data_properties["metadata"] = metadata_text
                    batch.add_data_object(data_properties, "Image")

    def write_webpages_to_weaviate(self, urls: list[str]):
        """
        Write the contents of a list of URLs to the RagMeDocs collection in Weaviate.
        Args:
            urls (list[str]): A list of URLs to write to the RagMeDocs collection
        """
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        collection = self.weeviate_client.collections.get(self.docs_collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                metadata_text = json.dumps({"type": "webpage", "url": doc.id_}, ensure_ascii=False)
                batch.add_object(properties={"url": doc.id_,
                                             "metadata": metadata_text,
                                             "text": doc.text})
    
    def write_json_to_weaviate(self, json_data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Write JSON content to the RagMeDocs collection in Weaviate.
        Args:
            json_data (Dict[str, Any]): The JSON data to write
            metadata (Dict[str, Any], optional): Additional metadata to store with the content
        """
        # Convert JSON data to string for storage
        json_text = json.dumps(json_data, ensure_ascii=False)
        
        # Convert metadata to string if provided
        metadata_text = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"
        
        collection = self.weeviate_client.collections.get(self.docs_collection_name)
        with collection.batch.dynamic() as batch:
            batch.add_object(properties={
                "url": json_data.get("filename", "filename not found"),
                "text": json_text,
                "metadata": metadata_text
            })

    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents in the Weaviate collection.
        
        Args:
            limit (int): Maximum number of documents to return
            offset (int): Number of documents to skip
            
        Returns:
            List[Dict[str, Any]]: List of documents with their properties
        """
        collection = self.weeviate_client.collections.get(self.docs_collection_name)
        
        # Query the collection
        result = collection.query.fetch_objects(
            limit=limit,
            offset=offset,
            include_vector=False  # Don't include vector data in response
        )
        
        # Process the results
        documents = []
        for obj in result.objects:
            doc = {
                "id": obj.uuid,
                "url": obj.properties.get("url", ""),
                "text": obj.properties.get("text", ""),
                "metadata": obj.properties.get("metadata", "{}")
            }
            
            # Try to parse metadata if it's a JSON string
            try:
                doc["metadata"] = json.loads(doc["metadata"])
            except json.JSONDecodeError:
                pass
                
            documents.append(doc)
            
        return documents

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
        print("Done writing to Weaviate")
        
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
