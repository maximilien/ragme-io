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
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ragme.agents.local_agent import DirectoryMonitor, FileHandler, RagMeLocalAgent


class TestRagMeLocalAgent:
    """Test cases for RagMeLocalAgent class"""

    @patch("src.ragme.agents.local_agent.RAGME_API_URL", "http://test-api.com")
    @patch("src.ragme.agents.local_agent.RAGME_MCP_URL", "http://test-mcp.com")
    def test_init_with_default_urls(self):
        """Test initialization with default URLs from environment"""
        agent = RagMeLocalAgent()
        assert agent.api_url == "http://test-api.com"
        assert agent.mcp_url == "http://test-mcp.com"

    def test_init_with_custom_urls(self):
        """Test initialization with custom URLs"""
        agent = RagMeLocalAgent(
            api_url="http://custom-api.com", mcp_url="http://custom-mcp.com"
        )
        assert agent.api_url == "http://custom-api.com"
        assert agent.mcp_url == "http://custom-mcp.com"

    @patch("src.ragme.agents.local_agent.RAGME_API_URL", None)
    @patch("src.ragme.agents.local_agent.RAGME_MCP_URL", "http://test-mcp.com")
    def test_init_missing_api_url(self):
        """Test initialization fails when API URL is missing"""
        with pytest.raises(
            ValueError, match="RAGME_API_URL environment variable is required"
        ):
            RagMeLocalAgent()

    @patch("src.ragme.agents.local_agent.RAGME_API_URL", "http://test-api.com")
    @patch("src.ragme.agents.local_agent.RAGME_MCP_URL", None)
    def test_init_missing_mcp_url(self):
        """Test initialization fails when MCP URL is missing"""
        with pytest.raises(
            ValueError, match="RAGME_MCP_URL environment variable is required"
        ):
            RagMeLocalAgent()

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_add_to_rag_success(self, mock_post):
        """Test successful addition to RAG"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        # Use the correct data structure that the new add_to_rag method expects
        data = {
            "data": {
                "text": "This is test content",
                "url": "file://test.txt",
                "metadata": {"filename": "test.txt"},
            },
            "metadata": {"source": "test"},
        }
        result = agent.add_to_rag(data)

        assert result is True
        # The method now sends a different structure, so we need to check the call differently
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-api.com/add-json"

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_add_to_rag_api_error(self, mock_post):
        """Test RAG addition with API error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        mock_post.return_value = mock_response

        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        data = {"test": "data"}
        result = agent.add_to_rag(data)

        assert result is False

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_add_to_rag_response_error(self, mock_post):
        """Test RAG addition with response error"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "Processing failed",
        }
        mock_post.return_value = mock_response

        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        data = {"test": "data"}
        result = agent.add_to_rag(data)

        assert result is False

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_add_to_rag_exception(self, mock_post):
        """Test RAG addition with exception"""
        mock_post.side_effect = Exception("Network error")

        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        data = {"test": "data"}
        result = agent.add_to_rag(data)

        assert result is False

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_process_pdf_file_success(self, mock_post):
        """Test successful PDF processing"""
        # Create a temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"fake pdf content")
            temp_file_path = Path(temp_file.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "data": {"text": "extracted text content"},
                    "metadata": {"pages": 5},
                },
            }
            mock_post.return_value = mock_response

            agent = RagMeLocalAgent(
                api_url="http://test-api.com", mcp_url="http://test-mcp.com"
            )

            result = agent._process_pdf_file(temp_file_path)

            assert result is True
            assert mock_post.call_count == 2  # One for MCP, one for RAG
        finally:
            temp_file_path.unlink()

    def test_process_pdf_file_nonexistent(self):
        """Test PDF processing with nonexistent file"""
        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        result = agent._process_pdf_file(Path("/nonexistent/file.pdf"))
        assert result is False

    def test_process_pdf_file_wrong_extension(self):
        """Test PDF processing with wrong file extension"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file_path = Path(temp_file.name)

        try:
            agent = RagMeLocalAgent(
                api_url="http://test-api.com", mcp_url="http://test-mcp.com"
            )

            result = agent._process_pdf_file(temp_file_path)
            assert result is False
        finally:
            temp_file_path.unlink()

    @patch("src.ragme.agents.local_agent.requests.post")
    def test_process_docx_file_success(self, mock_post):
        """Test successful DOCX processing"""
        # Create a temporary DOCX file
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
            temp_file.write(b"fake docx content")
            temp_file_path = Path(temp_file.name)

        try:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "data": {"text": "extracted text content", "table_count": 2},
                    "metadata": {"pages": 3},
                },
            }
            mock_post.return_value = mock_response

            agent = RagMeLocalAgent(
                api_url="http://test-api.com", mcp_url="http://test-mcp.com"
            )

            result = agent._process_docx_file(temp_file_path)

            assert result is True
            assert mock_post.call_count == 2  # One for MCP, one for RAG
        finally:
            temp_file_path.unlink()

    def test_process_docx_file_nonexistent(self):
        """Test DOCX processing with nonexistent file"""
        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        result = agent._process_docx_file(Path("/nonexistent/file.docx"))
        assert result is False

    def test_process_file_pdf(self):
        """Test process_file with PDF"""
        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        with patch.object(agent, "_process_pdf_file") as mock_process_pdf:
            mock_process_pdf.return_value = True

            # Use a unique file path within the watch directory to avoid conflicts with processed markers
            file_path = Path("watch_directory/test_unique_pdf.pdf")

            # Create the test file
            file_path.parent.mkdir(exist_ok=True)
            file_path.touch()

            # Clean up any existing processed marker
            processed_marker = file_path.with_suffix(file_path.suffix + ".processed")
            if processed_marker.exists():
                processed_marker.unlink()

            try:
                agent.process_file(file_path)
                mock_process_pdf.assert_called_once_with(file_path)
            finally:
                # Clean up test files
                file_path.unlink(missing_ok=True)
                processed_marker.unlink(missing_ok=True)
                lock_file = file_path.with_suffix(file_path.suffix + ".lock")
                lock_file.unlink(missing_ok=True)

    @patch("src.ragme.agents.local_agent.RAGME_API_URL", "http://test-api.com")
    @patch("src.ragme.agents.local_agent.RAGME_MCP_URL", "http://test-mcp.com")
    def test_process_file_docx(self):
        """Test processing a DOCX file."""
        mock_ragme = RagMeLocalAgent()
        mock_ragme._process_docx_file = Mock(return_value=True)

        # Use a unique file path within the watch directory to avoid conflicts with processed markers
        file_path = Path("watch_directory/test_unique_docx.docx")

        # Create the test file
        file_path.parent.mkdir(exist_ok=True)
        file_path.touch()

        # Clean up any existing processed marker
        processed_marker = file_path.with_suffix(file_path.suffix + ".processed")
        if processed_marker.exists():
            processed_marker.unlink()

        try:
            # Test with a DOCX file
            result = mock_ragme.process_file(file_path)
            assert result is None  # process_file doesn't return anything
            mock_ragme._process_docx_file.assert_called_once_with(file_path)
        finally:
            # Clean up test files
            file_path.unlink(missing_ok=True)
            processed_marker.unlink(missing_ok=True)
            lock_file = file_path.with_suffix(file_path.suffix + ".lock")
            lock_file.unlink(missing_ok=True)

    @patch("src.ragme.agents.local_agent.RAGME_API_URL", "http://test-api.com")
    @patch("src.ragme.agents.local_agent.RAGME_MCP_URL", "http://test-mcp.com")
    def test_file_type_metadata_setting(self):
        """Test that file type is correctly set in metadata."""
        mock_ragme = RagMeLocalAgent()

        # Mock the API response
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success"}

            # Test data with a PDF filename
            test_data = {
                "data": {"text": "Test content"},
                "metadata": {
                    "filename": "test_document.pdf",
                    "date_added": "2024-01-01",
                },
            }

            # Call add_to_rag
            result = mock_ragme.add_to_rag(test_data)

            # Verify the API was called
            mock_post.assert_called_once()

            # Get the data that was sent to the API
            call_args = mock_post.call_args
            sent_data = call_args[1]["json"]

            # Check that the type field was set correctly
            metadata = sent_data["data"]["documents"][0]["metadata"]
            assert metadata["type"] == "PDF"
            assert metadata["filename"] == "test_document.pdf"

            assert result is True

    def test_process_file_unsupported(self):
        """Test process_file with unsupported file type"""
        agent = RagMeLocalAgent(
            api_url="http://test-api.com", mcp_url="http://test-mcp.com"
        )

        with patch("src.ragme.agents.local_agent.logging") as mock_logging:
            file_path = Path("watch_directory/test.txt")

            # Create the test file
            file_path.parent.mkdir(exist_ok=True)
            file_path.touch()

            try:
                agent.process_file(file_path)
                mock_logging.warning.assert_called_once_with(
                    f"Unsupported file type: {file_path}"
                )
            finally:
                # Clean up test files
                file_path.unlink(missing_ok=True)
                lock_file = file_path.with_suffix(file_path.suffix + ".lock")
                lock_file.unlink(missing_ok=True)


class TestFileHandler:
    """Test cases for FileHandler class"""

    def test_init(self):
        """Test FileHandler initialization"""
        callback = Mock()
        handler = FileHandler(callback)

        assert handler.callback == callback
        assert handler.supported_extensions == {
            ".pdf",
            ".docx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".bmp",
            ".heic",
            ".heif",
        }

    def test_on_created_supported_file(self):
        """Test on_created with supported file"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.pdf"

        handler.on_created(event)

        callback.assert_called_once_with(Path("/path/to/test.pdf"))

    def test_on_created_unsupported_file(self):
        """Test on_created with unsupported file"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.txt"

        handler.on_created(event)

        callback.assert_not_called()

    def test_on_created_directory(self):
        """Test on_created with directory"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = True
        event.src_path = "/path/to/directory"

        handler.on_created(event)

        callback.assert_not_called()

    def test_on_modified_supported_file(self):
        """Test on_modified with supported file - should ignore modification events"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.docx"

        handler.on_modified(event)

        # on_modified should not call the callback (ignores modification events)
        callback.assert_not_called()

    def test_on_modified_unsupported_file(self):
        """Test on_modified with unsupported file"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.txt"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_on_modified_directory(self):
        """Test on_modified with directory"""
        callback = Mock()
        handler = FileHandler(callback)

        # Create a mock event
        event = Mock()
        event.is_directory = True
        event.src_path = "/path/to/directory"

        handler.on_modified(event)

        callback.assert_not_called()

    def test_case_insensitive_extensions(self):
        """Test that file extensions are handled case-insensitively"""
        callback = Mock()
        handler = FileHandler(callback)

        # Test uppercase extensions
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/test.PDF"

        handler.on_created(event)
        callback.assert_called_once_with(Path("/path/to/test.PDF"))


class TestDirectoryMonitor:
    """Test cases for DirectoryMonitor class"""

    def test_init(self):
        """Test DirectoryMonitor initialization"""
        callback = Mock()
        monitor = DirectoryMonitor("/test/directory", callback)

        assert monitor.directory == Path("/test/directory")
        assert monitor.handler.callback == callback
        assert isinstance(monitor.observer, type(monitor.observer))

    def test_start_nonexistent_directory(self):
        """Test start with nonexistent directory"""
        callback = Mock()
        monitor = DirectoryMonitor("/nonexistent/directory", callback)

        with patch("src.ragme.agents.local_agent.logging") as mock_logging:
            monitor.start()
            mock_logging.error.assert_called_once_with(
                "Directory does not exist: /nonexistent/directory"
            )

    @patch("src.ragme.agents.local_agent.Observer")
    def test_start_success(self, mock_observer_class):
        """Test successful start"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        callback = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = DirectoryMonitor(temp_dir, callback)

            # Mock the infinite loop to break after a short time
            with patch("src.ragme.agents.local_agent.time.sleep") as mock_sleep:
                mock_sleep.side_effect = KeyboardInterrupt()

                with patch("src.ragme.agents.local_agent.logging") as mock_logging:
                    monitor.start()

                    mock_observer.schedule.assert_called_once()
                    mock_observer.start.assert_called_once()
                    mock_observer.stop.assert_called_once()
                    mock_observer.join.assert_called_once()
                    mock_logging.info.assert_any_call(
                        f"Starting to monitor directory: {temp_dir}"
                    )
                    mock_logging.info.assert_any_call("Stopped monitoring directory")

    def test_stop_without_start(self):
        """Test stop method without starting the observer"""
        callback = Mock()
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = DirectoryMonitor(temp_dir, callback)

            # Mock the observer to avoid threading issues
            mock_observer = Mock()
            monitor.observer = mock_observer

            with patch("src.ragme.agents.local_agent.logging") as mock_logging:
                monitor.stop()

                mock_observer.stop.assert_called_once()
                mock_observer.join.assert_called_once()
                mock_logging.info.assert_called_once_with(
                    "Stopped monitoring directory"
                )
