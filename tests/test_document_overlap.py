# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

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

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.agents.local_agent import RagMeLocalAgent
from src.ragme.apis.api import add_json
from src.ragme.ragme import RagMe


@pytest.mark.asyncio
class TestDocumentOverlap:
    """Integration tests to ensure PDF and URL documents don't overlap each other."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = Path(self.temp_dir) / "test_document.pdf"

        # Create a simple test PDF file
        with open(self.test_pdf_path, "w") as f:
            f.write("%PDF-1.4\n")
            f.write("1 0 obj\n")
            f.write("<< /Type /Catalog /Pages 2 0 R >>\n")
            f.write("endobj\n")
            f.write("2 0 obj\n")
            f.write("<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
            f.write("endobj\n")
            f.write("3 0 obj\n")
            f.write(
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
            )
            f.write("endobj\n")
            f.write("4 0 obj\n")
            f.write("<< /Length 44 >>\n")
            f.write("stream\n")
            f.write("BT /F1 12 Tf 100 700 Td (Test Integration Document) Tj ET\n")
            f.write("endstream\n")
            f.write("endobj\n")
            f.write("xref\n")
            f.write("0 5\n")
            f.write("0000000000 65535 f \n")
            f.write("0000000009 00000 n \n")
            f.write("0000000058 00000 n \n")
            f.write("0000000115 00000 n \n")
            f.write("0000000204 00000 n \n")
            f.write("trailer\n")
            f.write("<< /Size 5 /Root 1 0 R >>\n")
            f.write("startxref\n")
            f.write("297\n")
            f.write("%%EOF\n")

    def teardown_method(self):
        """Clean up test environment after each test."""
        # Remove temporary files
        if self.test_pdf_path.exists():
            self.test_pdf_path.unlink()
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    @patch("src.ragme.ragme.RagMe")
    async def test_pdf_and_url_documents_dont_overlap(self, mock_ragme_class):
        """Test that adding PDF and URL documents don't overwrite each other."""
        # Mock the RagMe instance
        mock_ragme = MagicMock()
        mock_ragme_class.return_value = mock_ragme

        # Mock the vector database to track documents
        mock_vector_db = MagicMock()
        mock_ragme.vector_db = mock_vector_db

        # Track documents that are written
        written_documents = []

        def mock_write_documents(docs):
            written_documents.extend(docs)

        mock_vector_db.write_documents.side_effect = mock_write_documents

        # Mock find_document_by_url to return None (no existing documents)
        mock_vector_db.find_document_by_url.return_value = None

        # Test data: Add a URL document first
        url_document_data = {
            "documents": [
                {
                    "text": "This is a test webpage about artificial intelligence.",
                    "url": "https://example.com/ai-article",
                    "metadata": {
                        "type": "webpage",
                        "title": "AI Article",
                        "source": "example.com",
                    },
                }
            ]
        }

        # Add the URL document
        from src.ragme.apis.api import JSONInput

        url_input = JSONInput(data=url_document_data, metadata={"source": "test"})

        with patch("src.ragme.apis.api.get_ragme", return_value=mock_ragme):
            result = await add_json(url_input)

        # Verify URL document was added
        assert result["status"] == "success"
        assert result["processed_count"] == 1
        assert len(written_documents) == 1

        # Verify the URL document has the correct URL format
        url_doc = written_documents[0]
        assert "https://example.com/ai-article#" in url_doc["url"]
        assert (
            url_doc["text"] == "This is a test webpage about artificial intelligence."
        )

        # Now add a PDF document
        pdf_document_data = {
            "documents": [
                {
                    "text": "This is a PDF document about machine learning algorithms.",
                    "url": "file://test_document.pdf",
                    "metadata": {
                        "type": "pdf",
                        "filename": "test_document.pdf",
                        "pages": 5,
                    },
                }
            ]
        }

        # Add the PDF document
        pdf_input = JSONInput(data=pdf_document_data, metadata={"source": "test"})

        with patch("src.ragme.apis.api.get_ragme", return_value=mock_ragme):
            result = await add_json(pdf_input)

        # Verify PDF document was added
        assert result["status"] == "success"
        assert result["processed_count"] == 1
        assert len(written_documents) == 2

        # Verify the PDF document has the correct URL format
        pdf_doc = written_documents[1]
        assert "file://test_document.pdf#" in pdf_doc["url"]
        assert (
            pdf_doc["text"]
            == "This is a PDF document about machine learning algorithms."
        )

        # Verify documents have different URLs and don't overlap
        assert url_doc["url"] != pdf_doc["url"]
        assert url_doc["text"] != pdf_doc["text"]

        # Verify metadata is preserved
        assert url_doc["metadata"]["type"] == "webpage"
        assert pdf_doc["metadata"]["type"] == "pdf"

    @patch("src.ragme.ragme.RagMe")
    async def test_multiple_pdf_documents_dont_overlap(self, mock_ragme_class):
        """Test that adding multiple PDF documents don't overwrite each other."""
        # Mock the RagMe instance
        mock_ragme = MagicMock()
        mock_ragme_class.return_value = mock_ragme

        # Mock the vector database to track documents
        mock_vector_db = MagicMock()
        mock_ragme.vector_db = mock_vector_db

        # Track documents that are written
        written_documents = []

        def mock_write_documents(docs):
            written_documents.extend(docs)

        mock_vector_db.write_documents.side_effect = mock_write_documents

        # Mock find_document_by_url to return None (no existing documents)
        mock_vector_db.find_document_by_url.return_value = None

        # Test data: Add multiple PDF documents
        pdf_documents_data = {
            "documents": [
                {
                    "text": "First PDF document about neural networks.",
                    "url": "file://document1.pdf",
                    "metadata": {
                        "type": "pdf",
                        "filename": "document1.pdf",
                        "pages": 3,
                    },
                },
                {
                    "text": "Second PDF document about deep learning.",
                    "url": "file://document2.pdf",
                    "metadata": {
                        "type": "pdf",
                        "filename": "document2.pdf",
                        "pages": 4,
                    },
                },
                {
                    "text": "Third PDF document about computer vision.",
                    "url": "file://document3.pdf",
                    "metadata": {
                        "type": "pdf",
                        "filename": "document3.pdf",
                        "pages": 6,
                    },
                },
            ]
        }

        # Add the PDF documents
        from src.ragme.apis.api import JSONInput

        pdf_input = JSONInput(data=pdf_documents_data, metadata={"source": "test"})

        with patch("src.ragme.apis.api.get_ragme", return_value=mock_ragme):
            result = await add_json(pdf_input)

        # Verify all PDF documents were added
        assert result["status"] == "success"
        assert result["processed_count"] == 3
        assert len(written_documents) == 3

        # Verify each document has a unique URL
        urls = [doc["url"] for doc in written_documents]
        assert len(set(urls)) == 3  # All URLs should be unique

        # Verify documents have different content
        texts = [doc["text"] for doc in written_documents]
        assert len(set(texts)) == 3  # All texts should be unique

        # Verify each document has the correct file URL format
        for i, doc in enumerate(written_documents):
            expected_base_url = f"file://document{i + 1}.pdf"
            assert expected_base_url in doc["url"]
            assert doc["metadata"]["filename"] == f"document{i + 1}.pdf"

    @patch("src.ragme.ragme.RagMe")
    async def test_multiple_url_documents_dont_overlap(self, mock_ragme_class):
        """Test that adding multiple URL documents don't overwrite each other."""
        # Mock the RagMe instance
        mock_ragme = MagicMock()
        mock_ragme_class.return_value = mock_ragme

        # Mock the vector database to track documents
        mock_vector_db = MagicMock()
        mock_ragme.vector_db = mock_vector_db

        # Track documents that are written
        written_documents = []

        def mock_write_documents(docs):
            written_documents.extend(docs)

        mock_vector_db.write_documents.side_effect = mock_write_documents

        # Mock find_document_by_url to return None (no existing documents)
        mock_vector_db.find_document_by_url.return_value = None

        # Test data: Add multiple URL documents
        url_documents_data = {
            "documents": [
                {
                    "text": "First webpage about Python programming.",
                    "url": "https://python.org/tutorial",
                    "metadata": {
                        "type": "webpage",
                        "title": "Python Tutorial",
                        "source": "python.org",
                    },
                },
                {
                    "text": "Second webpage about JavaScript frameworks.",
                    "url": "https://reactjs.org/docs",
                    "metadata": {
                        "type": "webpage",
                        "title": "React Documentation",
                        "source": "reactjs.org",
                    },
                },
                {
                    "text": "Third webpage about machine learning basics.",
                    "url": "https://scikit-learn.org/stable/",
                    "metadata": {
                        "type": "webpage",
                        "title": "Scikit-learn Documentation",
                        "source": "scikit-learn.org",
                    },
                },
            ]
        }

        # Add the URL documents
        from src.ragme.apis.api import JSONInput

        url_input = JSONInput(data=url_documents_data, metadata={"source": "test"})

        with patch("src.ragme.apis.api.get_ragme", return_value=mock_ragme):
            result = await add_json(url_input)

        # Verify all URL documents were added
        assert result["status"] == "success"
        assert result["processed_count"] == 3
        assert len(written_documents) == 3

        # Verify each document has a unique URL
        urls = [doc["url"] for doc in written_documents]
        assert len(set(urls)) == 3  # All URLs should be unique

        # Verify documents have different content
        texts = [doc["text"] for doc in written_documents]
        assert len(set(texts)) == 3  # All texts should be unique

        # Verify each document has the correct URL format with timestamp
        for doc in written_documents:
            assert "#" in doc["url"]  # Should have timestamp fragment
            assert doc["metadata"]["type"] == "webpage"

    @patch("src.ragme.ragme.RagMe")
    async def test_mixed_document_types_dont_overlap(self, mock_ragme_class):
        """Test that adding mixed document types (PDF, URL, JSON) don't overlap."""
        # Mock the RagMe instance
        mock_ragme = MagicMock()
        mock_ragme_class.return_value = mock_ragme

        # Mock the vector database to track documents
        mock_vector_db = MagicMock()
        mock_ragme.vector_db = mock_vector_db

        # Track documents that are written
        written_documents = []

        def mock_write_documents(docs):
            written_documents.extend(docs)

        mock_vector_db.write_documents.side_effect = mock_write_documents

        # Mock find_document_by_url to return None (no existing documents)
        mock_vector_db.find_document_by_url.return_value = None

        # Test data: Add mixed document types
        mixed_documents_data = {
            "documents": [
                {
                    "text": "PDF document about data science.",
                    "url": "file://data_science.pdf",
                    "metadata": {
                        "type": "pdf",
                        "filename": "data_science.pdf",
                        "pages": 8,
                    },
                },
                {
                    "text": "Webpage about data visualization.",
                    "url": "https://matplotlib.org/",
                    "metadata": {
                        "type": "webpage",
                        "title": "Matplotlib Documentation",
                        "source": "matplotlib.org",
                    },
                },
                {
                    "text": "JSON data about API endpoints.",
                    "url": "file://api_documentation.json",
                    "metadata": {
                        "type": "json",
                        "filename": "api_documentation.json",
                        "endpoints": 15,
                    },
                },
            ]
        }

        # Add the mixed documents
        from src.ragme.apis.api import JSONInput

        mixed_input = JSONInput(data=mixed_documents_data, metadata={"source": "test"})

        with patch("src.ragme.apis.api.get_ragme", return_value=mock_ragme):
            result = await add_json(mixed_input)

        # Verify all documents were added
        assert result["status"] == "success"
        assert result["processed_count"] == 3
        assert len(written_documents) == 3

        # Verify each document has a unique URL
        urls = [doc["url"] for doc in written_documents]
        assert len(set(urls)) == 3  # All URLs should be unique

        # Verify documents have different content
        texts = [doc["text"] for doc in written_documents]
        assert len(set(texts)) == 3  # All texts should be unique

        # Verify each document type is preserved
        doc_types = [doc["metadata"]["type"] for doc in written_documents]
        assert "pdf" in doc_types
        assert "webpage" in doc_types
        assert "json" in doc_types

        # Verify file URLs have correct format
        file_docs = [
            doc for doc in written_documents if doc["url"].startswith("file://")
        ]
        assert len(file_docs) == 2  # PDF and JSON

        # Verify web URLs have correct format
        web_docs = [
            doc for doc in written_documents if doc["url"].startswith("https://")
        ]
        assert len(web_docs) == 1  # Webpage

    @patch("src.ragme.agents.local_agent.requests.post")
    @patch("src.ragme.ragme.RagMe")
    def test_pdf_file_processing_doesnt_overlap_urls(self, mock_ragme_class, mock_post):
        """Test that processing PDF files doesn't overlap with existing URL documents."""
        # Mock the RagMe instance
        mock_ragme = MagicMock()
        mock_ragme_class.return_value = mock_ragme

        # Mock the vector database to track documents
        mock_vector_db = MagicMock()
        mock_ragme.vector_db = mock_vector_db

        # Track documents that are written
        written_documents = []

        def mock_write_documents(docs):
            written_documents.extend(docs)

        mock_vector_db.write_documents.side_effect = mock_write_documents

        # Mock find_document_by_url to return None (no existing documents)
        mock_vector_db.find_document_by_url.return_value = None

        # Mock the MCP server response for PDF processing
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "data": {"text": "Extracted text from PDF document"},
                "metadata": {"pages": 5, "filename": "test_document.pdf"},
            },
        }
        mock_post.return_value = mock_response

        # Create local agent
        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        # Mock the add_to_rag method to track what's added
        original_add_to_rag = agent.add_to_rag

        def mock_add_to_rag(data):
            # Call the original method but track the data
            written_documents.append(data)
            return original_add_to_rag(data)

        agent.add_to_rag = mock_add_to_rag

        # Process the PDF file
        result = agent._process_pdf_file(self.test_pdf_path)

        # Verify PDF processing was successful
        assert result is True
        assert len(written_documents) == 1

        # Verify the PDF document has the correct data structure
        pdf_doc = written_documents[0]
        assert "data" in pdf_doc
        assert "text" in pdf_doc["data"]
        assert pdf_doc["data"]["text"] == "Extracted text from PDF document"
        assert "metadata" in pdf_doc
        assert pdf_doc["metadata"]["filename"] == "test_document.pdf"
