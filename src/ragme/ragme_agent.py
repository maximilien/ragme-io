# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from typing import List, Dict, Any

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from src.ragme.common import crawl_webpage

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")


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
            self.ragme.weeviate_client.collections.delete(self.ragme.collection_name)

        def list_ragme_collection(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            List the contents of the RagMeDocs collection
            """
            return self.ragme.list_documents()

        def write_to_ragme_collection(urls=list[str]):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            self.ragme.write_webpages_to_weaviate(urls)

        def query_agent(query: str) -> str:
            """
            Useful for asking questions about RagMe docs and website
            Args:
                query (str): The query to ask the QueryAgent
            Returns:
                str: The response from the QueryAgent
            """
            response = self.ragme.query_agent.run(query)
            return response.final_answer

        return FunctionAgent(
            tools=[write_to_ragme_collection, delete_ragme_collection, list_ragme_collection, find_urls_crawling_webpage, query_agent],
            llm=self.llm,
            system_prompt="""You are a helpful assistant that can write 
            the contents of urls to RagMeDocs 
            collection, as well as forwarding questions to a QueryAgent.
            The QueryAgent will priortize the contents of the RagMeDocs collection 
            to answer the question.
            You can also ask questions about the RagMeDocs collection directly.
            If the query is not about the RagMeDocs collection, you can ask the QueryAgent to answer the question.
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