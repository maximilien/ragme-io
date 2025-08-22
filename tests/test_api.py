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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch weaviate.connect_to_weaviate_cloud before importing the app
with patch("weaviate.connect_to_weaviate_cloud", return_value=MagicMock()):
    from src.ragme.apis.api import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_ragme():
    """Mock the RagMe instance."""
    with patch("src.ragme.apis.api.get_ragme") as mock_get_ragme:
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.write_webpages_to_weaviate = MagicMock()
        mock_ragme_instance.run = AsyncMock()  # Use AsyncMock for async methods
        mock_ragme_instance.cleanup = MagicMock()

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance
        yield mock_ragme_instance


def test_add_urls_success(client, mock_ragme):
    """Test successful URL addition."""
    test_urls = ["https://example.com", "https://example.org"]
    response = client.post("/add-urls", json={"urls": test_urls})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": f"Successfully processed {len(test_urls)} URLs",
        "urls_processed": len(test_urls),
    }
    mock_ragme.write_webpages_to_weaviate.assert_called_once_with(test_urls)


def test_add_urls_empty_list(client, mock_ragme):
    """Test adding an empty list of URLs."""
    response = client.post("/add-urls", json={"urls": []})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Successfully processed 0 URLs",
        "urls_processed": 0,
    }
    mock_ragme.write_webpages_to_weaviate.assert_called_once_with([])


def test_add_urls_error(client, mock_ragme):
    """Test error handling when adding URLs."""
    mock_ragme.write_webpages_to_weaviate.side_effect = Exception("Test error")

    response = client.post("/add-urls", json={"urls": ["https://example.com"]})

    assert response.status_code == 500
    assert response.json() == {"detail": "Test error"}


def test_query_success(client, mock_ragme):
    """Test successful query."""
    test_query = "What is the main topic?"
    test_response = "The main topic is testing."
    mock_ragme.run.return_value = test_response

    response = client.post("/query", json={"query": test_query})

    assert response.status_code == 200
    assert response.json() == {"status": "success", "response": test_response}
    mock_ragme.run.assert_called_once_with(test_query)


def test_query_error(client, mock_ragme):
    """Test error handling when querying."""
    mock_ragme.run.side_effect = Exception("Test error")

    response = client.post("/query", json={"query": "test query"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Test error"}


def test_invalid_input(client):
    """Test invalid input validation."""
    # Test invalid URL input
    response = client.post("/add-urls", json={"invalid_field": ["https://example.com"]})
    assert response.status_code == 422

    # Test invalid query input
    response = client.post("/query", json={"invalid_field": "test query"})
    assert response.status_code == 422


def test_mcp_server_config_success(client):
    """Test successful MCP server configuration update."""
    test_config = {"servers": [{"server": "Google GDrive", "enabled": True}]}
    response = client.post("/mcp-server-config", json=test_config)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "1 MCP server(s)" in result["message"]
    assert len(result["results"]) == 1
    assert result["results"][0]["server"] == "Google GDrive"
    assert result["results"][0]["enabled"] is True
    assert result["total_updated"] == 1


def test_mcp_server_config_multiple_servers(client):
    """Test updating multiple MCP server configurations."""
    test_config = {
        "servers": [
            {"server": "Google GDrive", "enabled": True},
            {"server": "Dropbox Drive", "enabled": False},
            {"server": "Google Mail", "enabled": True},
        ]
    }
    response = client.post("/mcp-server-config", json=test_config)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "3 MCP server(s)" in result["message"]
    assert len(result["results"]) == 3
    assert result["total_updated"] == 3

    # Check individual results
    servers = {r["server"]: r for r in result["results"]}
    assert servers["Google GDrive"]["enabled"] is True
    assert servers["Dropbox Drive"]["enabled"] is False
    assert servers["Google Mail"]["enabled"] is True


def test_mcp_server_config_disable(client):
    """Test disabling MCP server configuration."""
    test_config = {"servers": [{"server": "Dropbox Drive", "enabled": False}]}
    response = client.post("/mcp-server-config", json=test_config)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "1 MCP server(s)" in result["message"]
    assert len(result["results"]) == 1
    assert result["results"][0]["server"] == "Dropbox Drive"
    assert result["results"][0]["enabled"] is False
    assert result["total_updated"] == 1


def test_mcp_server_config_invalid_input(client):
    """Test invalid MCP server configuration input."""
    # Test missing servers field
    response = client.post("/mcp-server-config", json={"enabled": True})
    assert response.status_code == 422

    # Test empty servers list
    response = client.post("/mcp-server-config", json={"servers": []})
    assert response.status_code == 200  # Empty list is valid

    # Test invalid server object (missing server field)
    response = client.post("/mcp-server-config", json={"servers": [{"enabled": True}]})
    assert response.status_code == 422

    # Test invalid server object (missing enabled field)
    response = client.post(
        "/mcp-server-config", json={"servers": [{"server": "Test Server"}]}
    )
    assert response.status_code == 422

    # Test invalid enabled field type
    response = client.post(
        "/mcp-server-config",
        json={"servers": [{"server": "Test Server", "enabled": "not_boolean"}]},
    )
    assert response.status_code == 422


def test_mcp_server_config_with_authentication(client):
    """Test MCP server configuration with authentication."""
    test_config = {
        "servers": [
            {"server": "Google GDrive", "enabled": True, "authenticated": True},
            {"server": "Dropbox Drive", "enabled": False, "authenticated": False},
        ]
    }
    response = client.post("/mcp-server-config", json=test_config)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "2 MCP server(s)" in result["message"]
    assert len(result["results"]) == 2
    assert result["total_updated"] == 2

    # Check individual results
    servers = {r["server"]: r for r in result["results"]}
    assert servers["Google GDrive"]["enabled"] is True
    assert servers["Google GDrive"]["authenticated"] is True
    assert servers["Dropbox Drive"]["enabled"] is False
    assert servers["Dropbox Drive"]["authenticated"] is False


def test_reset_chat_session_success(client, mock_ragme):
    """Test successful chat session reset."""
    # Add the reset_chat_session method to the mock
    mock_ragme.reset_chat_session = MagicMock()

    response = client.post("/reset-chat-session")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Chat session reset successfully",
    }
    mock_ragme.reset_chat_session.assert_called_once()


def test_reset_chat_session_error(client, mock_ragme):
    """Test error handling when resetting chat session."""
    # Add the reset_chat_session method to the mock and make it raise an exception
    mock_ragme.reset_chat_session = MagicMock(side_effect=Exception("Test error"))

    response = client.post("/reset-chat-session")

    assert response.status_code == 200
    assert response.json() == {
        "status": "error",
        "message": "Failed to reset chat session: Test error",
    }
    mock_ragme.reset_chat_session.assert_called_once()
