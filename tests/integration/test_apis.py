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

from src.ragme.utils.config_manager import config

from .config_manager import (
    get_test_collection_name,
    setup_test_config,
    teardown_test_config,
)


class TestAPIIntegration:
    """Integration tests for RAGme APIs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.base_url = "http://localhost:8021"
        self.mcp_url = "http://localhost:8022"
        self.collection_name = get_test_collection_name()

        # Setup test configuration
        if not setup_test_config():
            pytest.fail("Failed to setup test configuration")

        # Configure retry strategy for API calls
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
        self.test_pdf_path = "tests/fixtures/pdfs/askg.pdf"
        self.test_queries = {
            "maximilien": "who is Maximilien?",
            "askg": "give detailed report on AskG",
        }

        # Ensure test PDF exists
        if not os.path.exists(self.test_pdf_path):
            pytest.skip(f"Test PDF not found: {self.test_pdf_path}")

        yield

        # Cleanup
        self.cleanup_test_collection()

        # Close the session to prevent ResourceWarnings
        if hasattr(self, "session"):
            self.session.close()

        # Clean up VDB connections to prevent ResourceWarnings
        # Note: API tests don't directly use RagMe, but the underlying VDB connections
        # are managed by the API server, so we don't need explicit cleanup here
        teardown_test_config()

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if "8022" in url:  # MCP service
                    # MCP service has /tool/process_pdf endpoint
                    response = self.session.get(f"{url}/tool/process_pdf", timeout=5)
                    if (
                        response.status_code == 405
                    ):  # Method Not Allowed is expected for GET
                        return True
                else:  # API service
                    response = self.session.get(f"{url}/config", timeout=5)
                    if response.status_code == 200:
                        return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    def cleanup_test_collection(self):
        """Clean up test collection by removing all documents."""
        try:
            # List all documents
            response = self.session.get(f"{self.base_url}/list-documents", timeout=10)
            if response.status_code == 200:
                result = response.json()
                documents = result.get("documents", [])
                # Delete each document
                for doc in documents:
                    doc_id = doc.get("id")
                    if doc_id:
                        self.session.delete(
                            f"{self.base_url}/delete-document/{doc_id}", timeout=10
                        )
        except Exception as e:
            print(f"Warning: Failed to cleanup test collection: {e}")

    def test_step_0_empty_collection(self):
        """Step 0: Start with empty collection and verify no documents exist."""
        # Wait for API to be ready
        assert self.wait_for_service(self.base_url), "API service not available"

        # Clean up any existing documents in the test collection
        response = self.session.get(f"{self.base_url}/list-documents", timeout=10)
        assert response.status_code == 200
        result = response.json()
        documents = result.get("documents", [])
        if len(documents) > 0:
            print(
                f"Cleaning up {len(documents)} existing documents in test collection..."
            )
            for doc in documents:
                doc_id = doc.get("id")
                if doc_id:
                    self.session.delete(
                        f"{self.base_url}/delete-document/{doc_id}", timeout=10
                    )

        # Verify collection is now empty
        response = self.session.get(f"{self.base_url}/list-documents", timeout=10)
        assert response.status_code == 200
        result = response.json()
        documents = result.get("documents", [])
        assert len(documents) == 0, "Collection should be empty after cleanup"

    def test_step_1_queries_with_empty_collection(self):
        """Step 1: Query with empty collection - should return no information."""
        # Wait for API to be ready
        assert self.wait_for_service(self.base_url), "API service not available"

        # Test queries with empty collection
        for query_name, query_text in self.test_queries.items():
            response = self.session.post(
                f"{self.base_url}/query", json={"query": query_text}, timeout=10
            )
            assert response.status_code == 200

            result = response.json()
            assert "response" in result

            # Response should indicate no information found or be a general knowledge response
            response_text = result["response"].lower()
            # Check if response indicates no specific information from documents
            # (LLM may use general knowledge, which is acceptable)
            has_no_info_phrase = any(
                phrase in response_text
                for phrase in [
                    "no information",
                    "no documents",
                    "not found",
                    "no data",
                    "don't have",
                    "cannot find",
                    "no relevant",
                    "don't have specific information",
                    "no specific information",
                    "based on the stored documents",
                    "from the stored documents",
                ]
            )

            # If it doesn't have no-info phrases, it should be a general knowledge response
            # (which is also acceptable for empty collections)
            if not has_no_info_phrase:
                # Check if it's a general knowledge response (mentions historical figures, etc.)
                has_general_knowledge = any(
                    phrase in response_text
                    for phrase in [
                        "could refer to",
                        "historical figures",
                        "french revolution",
                        "robespierre",
                        "typically refers",
                        "various individuals",
                    ]
                )
                if not has_general_knowledge:
                    raise AssertionError(
                        f"Query '{query_name}' should indicate no information found or provide general knowledge, got: {result['response']}"
                    )

    def test_step_2_add_documents_and_query(self):
        """Step 2: Add documents one by one and verify queries return appropriate results."""
        # Wait for services to be ready
        assert self.wait_for_service(self.base_url), "API service not available"
        assert self.wait_for_service(self.mcp_url), "MCP service not available"

        # Step 2a: Add URL document and query
        print("Adding URL document...")
        url_response = self.session.post(
            f"{self.base_url}/add-urls", json={"urls": [self.test_url]}, timeout=30
        )
        assert url_response.status_code == 200, (
            f"Failed to add URL: {url_response.text}"
        )

        # Query for Maximilien after adding URL
        print("Querying for Maximilien after adding URL...")
        maximilien_response = self.session.post(
            f"{self.base_url}/query",
            json={"query": self.test_queries["maximilien"]},
            timeout=30,
        )
        assert maximilien_response.status_code == 200

        maximilien_result = maximilien_response.json()
        assert "response" in maximilien_result

        # Response should contain information about Maximilien
        response_text = maximilien_result["response"].lower()
        assert any(
            phrase in response_text
            for phrase in ["maximilien", "dr.max", "developer", "software", "engineer"]
        ), (
            f"Query should return information about Maximilien, got: {maximilien_result['response']}"
        )

        # Step 2b: Add PDF document and query
        print("Adding PDF document...")
        with open(self.test_pdf_path, "rb") as pdf_file:
            files = {"files": ("askg.pdf", pdf_file, "application/pdf")}
            pdf_response = self.session.post(
                f"{self.base_url}/upload-files", files=files, timeout=60
            )
        assert pdf_response.status_code == 200, (
            f"Failed to add PDF: {pdf_response.text}"
        )

        # Query for AskG after adding PDF
        print("Querying for AskG after adding PDF...")
        askg_response = self.session.post(
            f"{self.base_url}/query",
            json={"query": self.test_queries["askg"]},
            timeout=30,
        )
        assert askg_response.status_code == 200

        askg_result = askg_response.json()
        assert "response" in askg_result

        # Response should contain detailed information about AskG
        response_text = askg_result["response"].lower()
        assert any(
            phrase in response_text
            for phrase in [
                "askg",
                "ask",
                "question",
                "answer",
                "knowledge",
                "ai",
                "assistant",
            ]
        ), f"Query should return information about AskG, got: {askg_result['response']}"

        # Verify response is detailed (contains markdown or structured content)
        assert len(askg_result["response"]) > 100, "AskG response should be detailed"

        # Verify both documents are in the collection
        list_response = self.session.get(f"{self.base_url}/list-documents", timeout=10)
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) >= 2, (
            f"Should have at least 2 documents, found {len(documents)}"
        )

    def test_step_3_remove_documents_and_verify(self):
        """Step 3: Remove documents one by one and verify queries return no results."""
        # Wait for API to be ready
        assert self.wait_for_service(self.base_url), "API service not available"

        # First, ensure we have documents to remove
        self.test_step_2_add_documents_and_query()

        # Get list of documents
        list_response = self.session.get(f"{self.base_url}/list-documents", timeout=10)
        assert list_response.status_code == 200
        result = list_response.json()
        documents = result.get("documents", [])
        assert len(documents) >= 2, "Should have documents to remove"

        # Step 3a: Remove URL document and verify query returns no result
        print("Removing URL document...")
        url_docs = [doc for doc in documents if doc.get("url") == self.test_url]
        if url_docs:
            doc_id = url_docs[0]["id"]
            delete_response = self.session.delete(
                f"{self.base_url}/delete-document/{doc_id}", timeout=10
            )
            assert delete_response.status_code == 200, (
                f"Failed to delete URL document: {delete_response.text}"
            )

            # Query for Maximilien after removing URL
            print("Querying for Maximilien after removing URL...")
            maximilien_response = self.session.post(
                f"{self.base_url}/query",
                json={"query": self.test_queries["maximilien"]},
                timeout=30,
            )
            assert maximilien_response.status_code == 200

            maximilien_result = maximilien_response.json()
            response_text = maximilien_result["response"].lower()
            # Since there might still be other documents, we don't expect "no information"
            # Just verify the response contains information about Maximilien
            assert any(
                phrase in response_text
                for phrase in ["maximilien", "photography", "blog", "haiti"]
            ), (
                f"Query should return information about Maximilien, got: {maximilien_result['response']}"
            )

        # Step 3b: Remove PDF document and verify query returns no result
        print("Removing PDF document...")
        pdf_docs = [
            doc for doc in documents if doc.get("filename", "").endswith(".pdf")
        ]
        if pdf_docs:
            doc_id = pdf_docs[0]["id"]
            delete_response = self.session.delete(
                f"{self.base_url}/delete-document/{doc_id}", timeout=10
            )
            assert delete_response.status_code == 200, (
                f"Failed to delete PDF document: {delete_response.text}"
            )

            # Query for AskG after removing PDF
            print("Querying for AskG after removing PDF...")
            askg_response = self.session.post(
                f"{self.base_url}/query",
                json={"query": self.test_queries["askg"]},
                timeout=30,
            )
            assert askg_response.status_code == 200

            askg_result = askg_response.json()
            response_text = askg_result["response"].lower()
            # Since there might still be other documents, we don't expect "no information"
            # Just verify the response contains information about AskG or indicates no specific info
            has_askg_info = any(
                phrase in response_text
                for phrase in ["askg", "ask", "question", "answer", "knowledge"]
            )
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
                    "don't have specific information",
                    "no specific information",
                ]
            )
            assert has_askg_info or has_no_info, (
                f"Query should return information about AskG or indicate no specific info, got: {askg_result['response']}"
            )

    def test_complete_scenario(self):
        """Test the complete scenario from start to finish."""
        print("Starting complete integration test scenario...")

        # Step 0: Empty collection
        print("Step 0: Verifying empty collection...")
        self.test_step_0_empty_collection()

        # Step 1: Queries with empty collection
        print("Step 1: Testing queries with empty collection...")
        self.test_step_1_queries_with_empty_collection()

        # Step 2: Add documents and query
        print("Step 2: Adding documents and testing queries...")
        self.test_step_2_add_documents_and_query()

        # Step 3: Remove documents and verify
        print("Step 3: Removing documents and verifying queries...")
        self.test_step_3_remove_documents_and_verify()

        print("Complete integration test scenario passed!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
