import os, logging, json
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Union
import asyncio
import warnings
import requests
from bs4 import BeautifulSoup

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
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

class RagMe:
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
        if self.weeviate_client.collections.exists(self.collection_name):
            self.weeviate_client.collections.delete(self.collection_name)
        else:
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

        def write_to_ragme_collection(urls=list[str]):
            """Useful for writing new content to the RagMeDocs collection"""
            self.write_webpages_to_weaviate(urls)

        def query_agent(query: str) -> str:
            """Useful for asking questions about RagMe docs and website"""
            response = self.query_agent.run(query)
            return response.final_answer

        return FunctionAgent(
            tools=[write_to_ragme_collection, query_agent],
            llm=llm,
            system_prompt="""You are a helpful assistant that can write the
            contents of urls to RagMeDocs collection,
            as well as forwarding questions to a QueryAgent""",
        )
    
    # public methods

    def cleanup(self):
        if self.weeviate_client:
            self.weeviate_client.close()

    # TODO: avoid re-writing the same URLs
    def write_webpages_to_weaviate(self, urls: list[str]):
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        collection = self.weeviate_client.collections.get(self.collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                batch.add_object(properties={"url": doc.id_,
                                            "text": doc.text})
    def find_all_post_urls(self, blog_url: str) -> list[str]:
        """Find all post URLs from a given blog URL."""
        response = requests.get(blog_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        post_urls = [a['href'] for a in soup.find_all('a', href=True) if 'reviews' in a['href']]
        return post_urls

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
            prefix = '/'.join(url.split('/')[:-1])
            urls = ragme.find_all_post_urls(url)
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
