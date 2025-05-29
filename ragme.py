import os, logging, json
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Union
import asyncio
import warnings
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from common import crawl_webpage

logging.getLogger("httpx").setLevel(logging.WARNING)

from llama_index.core.workflow import (StartEvent, StopEvent, Workflow, step, Event, Context)
from llama_index.readers.web import SimpleWebPageReader
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

import weaviate
from weaviate.auth import Auth
from weaviate.agents.query import QueryAgent
from weaviate.classes.config import Configure, Property, DataType

import dotenv

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")
if not WEAVIATE_API_KEY:
    raise ValueError("WEAVIATE_API_KEY is not set")
if not WEAVIATE_URL:
    raise ValueError("WEAVIATE_URL is not set")

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

class RagMe:
    """A class for managing RAG (Retrieval-Augmented Generation) operations with web content using Weaviate."""
    
    def __init__(self):
        self.collection_name = "RagMeDocs"
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
        if not self.weeviate_client.collections.exists(self.collection_name):
            self.weeviate_client.collections.create(
                self.collection_name,
                description="A dataset with the contents of RagMe docs and website",
                vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                properties=[
                    Property(name="url", data_type=DataType.TEXT, description="the source URL of the webpage"),
                    Property(name="text", data_type=DataType.TEXT, description="the content of the webpage"),
            ])

    def _create_query_agent(self):
        return QueryAgent(client=self.weeviate_client, collections=[self.collection_name])

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
            self.weeviate_client.collections.delete(self.collection_name)

        def write_to_ragme_collection(urls=list[str]):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            self.write_webpages_to_weaviate(urls)

        def find_all_post_urls(blog_url: str, search_term: str) -> list[str]:
            """
            Find all post URLs from a given blog URL given a search term.
            Args:
                blog_url (str): The URL of the blog to search
                search_term (str): The search term to find in the blog URLs
            Returns:
                list[str]: A list of post URLs
            """
            response = requests.get(blog_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            post_urls = [a['href'] for a in soup.find_all('a', href=True) if search_term in a['href']]
            print(f"Found the {len(post_urls)} post URLs: {post_urls}")
            return post_urls

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
            tools=[write_to_ragme_collection, delete_ragme_collection, find_all_post_urls, find_urls_crawling_webpage, query_agent],
            llm=llm,
            system_prompt="""You are a helpful assistant that can write the
            contents of urls to RagMeDocs collection,
            as well as forwarding questions to a QueryAgent""",
        )
    
    # public methods

    def cleanup(self):
        if self.weeviate_client:
            self.weeviate_client.close()

    def write_webpages_to_weaviate(self, urls: list[str]):
        """
        Write the contents of a list of URLs to the RagMeDocs collection in Weaviate.
        Args:
            urls (list[str]): A list of URLs to write to the RagMeDocs collection
        """
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        collection = self.weeviate_client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                batch.add_object(properties={"url": doc.id_,
                                            "text": doc.text})
    
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
