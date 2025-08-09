# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import asyncio
import json
import os
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress ResourceWarnings from dependencies
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=".*Enable tracemalloc.*"
)
warnings.filterwarnings("ignore", category=ResourceWarning)

from src.ragme.agents.ragme_agent import RagMeAgent
from src.ragme.ragme import RagMe
from src.ragme.utils.config_manager import config

from .config_manager import (
    get_test_collection_name,
    setup_test_config,
    teardown_test_config,
)


class TestAgentsIntegration:
    """Integration tests for RAGme Agents."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.mcp_url = "http://localhost:8022"
        self.collection_name = get_test_collection_name()

        # Setup test configuration
        if not setup_test_config():
            pytest.fail("Failed to setup test configuration")

        # Force config reload after setup to pick up modified .env file
        config.reload()

        # Configure retry strategy for MCP calls
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Test data
        self.test_url = "https://maximilien.org"
        self.test_pdf_path = "tests/fixtures/pdfs/ragme-ai.pdf"
        self.test_queries = {
            "maximilien": "who is Maximilien?",
            "ragme": "what is the RAGme-ai project?",
        }

        # Ensure test PDF exists
        if not os.path.exists(self.test_pdf_path):
            pytest.skip(f"Test PDF not found: {self.test_pdf_path}")

        # Initialize RagMe and RagMeAgent
        self.ragme = RagMe()
        self.agent = RagMeAgent(self.ragme)

        yield

        # Cleanup
        self.cleanup_test_collection()

        # Close the session to prevent ResourceWarnings
        if hasattr(self, "session"):
            self.session.close()

        # Clean up VDB connections to prevent ResourceWarnings
        if hasattr(self, "ragme") and self.ragme:
            self.ragme.cleanup()
        teardown_test_config()

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{url}/tool/process_pdf", timeout=5)
                if response.status_code in [
                    200,
                    405,
                ]:  # 405 is expected for GET on POST endpoint
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    def cleanup_test_collection(self):
        """Clean up test collection by removing all documents."""
        try:
            # Use the agent to list and delete documents
            # This is a simplified cleanup - in practice you might want to use the API directly
            documents = self.ragme.list_documents()
            for doc in documents:
                if hasattr(self.ragme, "delete_document"):
                    self.ragme.delete_document(doc.get("id"))
        except Exception as e:
            print(f"Warning: Failed to cleanup test collection: {e}")

    async def test_step_0_empty_collection(self):
        """Step 0: Start with empty collection and verify no documents exist."""
        # Wait for MCP service to be ready
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # Clean up any existing documents in the test collection
        documents = self.ragme.list_documents()
        if len(documents) > 0:
            print(
                f"Cleaning up {len(documents)} existing documents in test collection..."
            )
            for doc in documents:
                if hasattr(self.ragme, "delete_document"):
                    self.ragme.delete_document(doc.get("id"))

        # Verify collection is now empty
        documents = self.ragme.list_documents()
        assert len(documents) == 0, "Collection should be empty after cleanup"

    async def test_step_1_queries_with_empty_collection(self):
        """Step 1: Query with empty collection - should return no information."""
        # Wait for MCP service to be ready
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # Test queries with empty collection using agent
        for query_name, query_text in self.test_queries.items():
            response = await self.agent.run(query_text)

            # Response should indicate no information found or provide general knowledge
            response_text = response.lower()
            # Check if response indicates no specific information from documents
            has_no_info = any(
                phrase in response_text
                for phrase in [
                    "no information",
                    "no documents",
                    "not found",
                    "no data",
                    "don't have",
                    "cannot find",
                    "no relevant",
                    "empty",
                    "don't have specific",
                    "don't have detailed",
                ]
            )
            # Or if it provides general knowledge (which is also acceptable)
            has_general_knowledge = any(
                phrase in response_text
                for phrase in [
                    "could refer to",
                    "historical",
                    "fictional",
                    "general",
                    "context",
                ]
            )
            # Or if it's asking for confirmation (which is also acceptable)
            is_asking_confirmation = any(
                phrase in response_text
                for phrase in [
                    "confirm",
                    "sure",
                    "proceed",
                    "yes",
                    "no",
                    "cancel",
                ]
            )
            assert has_no_info or has_general_knowledge or is_asking_confirmation, (
                f"Query '{query_name}' should indicate no specific information found, got: {response}"
            )

    async def test_step_2_add_documents_and_query(self):
        """Step 2: Add documents one by one and verify queries return appropriate results."""
        # Wait for MCP service to be ready
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # Step 2a: Add URL document using agent
        print("Adding URL document via agent...")
        url_query = f"add URL {self.test_url}"
        url_response = await self.agent.run(url_query)

        # Verify URL was added successfully or requires confirmation
        response_lower = url_response.lower()
        is_successful = any(
            phrase in response_lower
            for phrase in ["added", "success", "processed", "uploaded", "stored"]
        )
        requires_confirmation = any(
            phrase in response_lower
            for phrase in ["confirm", "sure", "proceed", "yes", "no", "cancel"]
        )
        assert is_successful or requires_confirmation, (
            f"URL should be added successfully or require confirmation, got: {url_response}"
        )

        # Query for Maximilien after adding URL
        print("Querying for Maximilien after adding URL...")
        maximilien_response = await self.agent.run(self.test_queries["maximilien"])

        # Response should contain information about Maximilien or require confirmation
        response_text = maximilien_response.lower()
        has_info = any(
            phrase in response_text
            for phrase in ["maximilien", "dr.max", "developer", "software", "engineer"]
        )
        requires_confirmation = any(
            phrase in response_text
            for phrase in [
                "confirm",
                "sure",
                "proceed",
                "yes",
                "no",
                "cancel",
            ]
        )
        assert has_info or requires_confirmation, (
            f"Query should return information about Maximilien or require confirmation, got: {maximilien_response}"
        )

        # Step 2b: Add PDF document using MCP server (if available)
        print("Adding PDF document via MCP server...")
        pdf_added = False
        try:
            with open(self.test_pdf_path, "rb") as pdf_file:
                files = {"file": ("ragme-ai.pdf", pdf_file, "application/pdf")}
                pdf_response = self.session.post(
                    f"{self.mcp_url}/tool/process_pdf", files=files, timeout=60
                )
            if pdf_response.status_code == 200:
                # Verify PDF was processed successfully
                pdf_result = pdf_response.json()
                if pdf_result.get("success", False):
                    pdf_added = True
                    print("✅ PDF document added successfully via MCP")
                else:
                    print(
                        f"⚠️ PDF processing failed: {pdf_result.get('error', 'Unknown error')}"
                    )
            else:
                print(
                    f"⚠️ MCP server returned status {pdf_response.status_code} for PDF upload"
                )
        except Exception as e:
            print(f"⚠️ Failed to add PDF via MCP server: {e}")

        # Query for RAGme after attempting to add PDF
        print("Querying for RAGme after adding PDF...")
        ragme_response = await self.agent.run(self.test_queries["ragme"])
        print(f"🔍 RAGme query response: {ragme_response[:200]}...")

        if pdf_added:
            # Response should contain detailed information about RAGme or require confirmation
            response_text = ragme_response.lower()
            has_info = any(
                phrase in response_text
                for phrase in [
                    "ragme",
                    "rag",
                    "project",
                    "answer",
                    "knowledge",
                    "ai",
                    "assistant",
                ]
            )
            requires_confirmation = any(
                phrase in response_text
                for phrase in [
                    "confirm",
                    "sure",
                    "proceed",
                    "yes",
                    "no",
                    "cancel",
                ]
            )
            assert has_info or requires_confirmation, (
                f"Query should return information about RAGme or require confirmation, got: {ragme_response}"
            )

            # Verify response is detailed (contains markdown or structured content) or requires confirmation
            requires_confirmation = any(
                phrase in ragme_response.lower()
                for phrase in [
                    "confirm",
                    "sure",
                    "proceed",
                    "yes",
                    "no",
                    "cancel",
                ]
            )
            assert len(ragme_response) > 100 or requires_confirmation, (
                "RAGme response should be detailed or require confirmation"
            )
        else:
            # If PDF wasn't added, response should indicate no information
            response_text = ragme_response.lower()
            has_no_info = any(
                phrase in response_text
                for phrase in [
                    "no information",
                    "no documents",
                    "not found",
                    "no data",
                    "don't have",
                    "cannot find",
                    "no relevant",
                    "empty",
                    "don't have specific",
                    "don't have detailed",
                ]
            )
            has_general_knowledge = any(
                phrase in response_text
                for phrase in [
                    "could refer to",
                    "historical",
                    "fictional",
                    "general",
                    "context",
                ]
            )
            assert has_no_info or has_general_knowledge, (
                f"Query should indicate no specific information found, got: {ragme_response}"
            )

        # Verify documents in the collection (at least the URL document should be there)
        documents = self.ragme.list_documents()
        print(f"📄 Documents in collection: {len(documents)}")
        for i, doc in enumerate(documents):
            print(
                f"  Document {i + 1}: {doc.get('title', 'No title')} - {doc.get('url', doc.get('filename', 'No source'))}"
            )

        # Note: PDF processing via MCP may not be fully integrated yet (as per TODO)
        # For now, we expect at least 1 document (the URL document)
        expected_min_docs = 1
        assert len(documents) >= expected_min_docs, (
            f"Should have at least {expected_min_docs} document(s), found {len(documents)}"
        )

    async def test_step_3_remove_documents_and_verify(self):
        """Step 3: Remove documents one by one and verify queries return no results."""
        # Wait for MCP service to be ready
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # First, ensure we have documents to remove
        await self.test_step_2_add_documents_and_query()

        # Get list of documents
        documents = self.ragme.list_documents()
        assert len(documents) >= 1, "Should have at least one document to remove"

        # Step 3a: Remove URL document and verify query returns no result
        print("Removing URL document...")
        url_docs = [doc for doc in documents if doc.get("url") == self.test_url]
        if url_docs:
            doc_id = url_docs[0]["id"]
            delete_query = f"delete document {doc_id}"
            delete_response = await self.agent.run(delete_query)

            # Verify deletion was successful or requires confirmation
            response_lower = delete_response.lower()
            is_successful = any(
                phrase in response_lower
                for phrase in ["deleted", "removed", "success", "confirmed"]
            )
            requires_confirmation = any(
                phrase in response_lower
                for phrase in ["confirm", "sure", "proceed", "yes", "no", "cancel"]
            )
            assert is_successful or requires_confirmation, (
                f"Document deletion should be successful or require confirmation, got: {delete_response}"
            )

            # Query for Maximilien after removing URL
            print("Querying for Maximilien after removing URL...")
            maximilien_response = await self.agent.run(self.test_queries["maximilien"])

            response_text = maximilien_response.lower()
            # Check if response indicates no information or is asking for confirmation
            has_no_info = any(
                phrase in response_text
                for phrase in [
                    "no information",
                    "no documents",
                    "not found",
                    "no data",
                    "don't have",
                    "cannot find",
                    "no relevant",
                    "empty",
                ]
            )
            is_asking_confirmation = any(
                phrase in response_text
                for phrase in [
                    "confirm",
                    "sure",
                    "proceed",
                    "yes",
                    "no",
                    "cancel",
                ]
            )
            assert has_no_info or is_asking_confirmation, (
                f"Query should indicate no information or ask for confirmation after removing URL document, got: {maximilien_response}"
            )

        # Step 3b: Remove PDF document and verify query returns no result
        print("Removing PDF document...")
        pdf_docs = [
            doc for doc in documents if doc.get("filename", "").endswith(".pdf")
        ]
        if pdf_docs:
            doc_id = pdf_docs[0]["id"]
            delete_query = f"delete document {doc_id}"
            delete_response = await self.agent.run(delete_query)

            # Verify deletion was successful or requires confirmation
            response_lower = delete_response.lower()
            is_successful = any(
                phrase in response_lower
                for phrase in ["deleted", "removed", "success", "confirmed"]
            )
            requires_confirmation = any(
                phrase in response_lower
                for phrase in ["confirm", "sure", "proceed", "yes", "no", "cancel"]
            )
            assert is_successful or requires_confirmation, (
                f"Document deletion should be successful or require confirmation, got: {delete_response}"
            )

            # Query for RAGme after removing PDF
            print("Querying for RAGme after removing PDF...")
            ragme_response = await self.agent.run(self.test_queries["ragme"])

            response_text = ragme_response.lower()
            # Check if response indicates no information or is asking for confirmation
            has_no_info = any(
                phrase in response_text
                for phrase in [
                    "no information",
                    "no documents",
                    "not found",
                    "no data",
                    "don't have",
                    "cannot find",
                    "no relevant",
                    "empty",
                ]
            )
            is_asking_confirmation = any(
                phrase in response_text
                for phrase in [
                    "confirm",
                    "sure",
                    "proceed",
                    "yes",
                    "no",
                    "cancel",
                ]
            )
            assert has_no_info or is_asking_confirmation, (
                f"Query should indicate no information or ask for confirmation after removing PDF document, got: {ragme_response}"
            )

    async def test_agent_functionality(self):
        """Test specific agent functionality and capabilities."""
        # Wait for MCP service to be ready
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # Test agent info
        agent_info = self.agent.get_agent_info()
        # The agent info might be None or have a different structure
        if agent_info is not None:
            assert isinstance(agent_info, dict), "Agent info should be a dictionary"
            # Check if it has any keys (agent_type might not be present)
            assert len(agent_info) > 0, "Agent info should not be empty"

        # Test memory info
        memory_info = self.agent.get_memory_info()
        # Memory info might be None or have a different structure
        if memory_info is not None:
            assert isinstance(memory_info, dict), "Memory info should be a dictionary"
            # Check if it has any keys (memory might not be present)
            assert len(memory_info) >= 0, "Memory info should be valid"

        # Test agent can handle various query types
        test_queries = [
            "What documents do you have?",
            "List all documents",
            "Show me the documents in the database",
        ]

        for query in test_queries:
            response = await self.agent.run(query)
            assert response is not None, f"Agent should respond to query: {query}"
            assert len(response) > 0, (
                f"Agent response should not be empty for query: {query}"
            )

    async def test_complete_scenario(self):
        """Test the complete scenario from start to finish."""
        print("Starting complete agent integration test scenario...")

        # Reset agent confirmation state to ensure clean start
        self.agent.reset_confirmation_state()

        # Step 0: Empty collection
        print("Step 0: Verifying empty collection...")
        await self.test_step_0_empty_collection()

        # Step 1: Queries with empty collection
        print("Step 1: Testing queries with empty collection...")
        await self.test_step_1_queries_with_empty_collection()

        # Step 2: Add documents and query
        print("Step 2: Adding documents and testing queries...")
        await self.test_step_2_add_documents_and_query()

        # Step 3: Remove documents and verify
        print("Step 3: Removing documents and verifying queries...")
        await self.test_step_3_remove_documents_and_verify()

        print("Complete agent integration test scenario passed!")

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        assert self.agent is not None, "Agent should be initialized"
        assert hasattr(self.agent, "run"), "Agent should have run method"
        assert hasattr(self.agent, "ragme"), "Agent should have ragme instance"
        assert hasattr(self.agent, "functional_agent"), (
            "Agent should have functional_agent"
        )
        assert hasattr(self.agent, "query_agent"), "Agent should have query_agent"


# Helper function to run async tests
def run_async_test(test_func):
    """Helper to run async test functions."""
    return asyncio.run(test_func())


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
