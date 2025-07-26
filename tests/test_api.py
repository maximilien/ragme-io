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
    from src.ragme.api import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_ragme():
    """Mock the RagMe instance."""
    with patch("src.ragme.api.ragme") as mock:
        # Setup mock methods
        mock.write_webpages_to_weaviate = MagicMock()
        mock.run = AsyncMock()  # Use AsyncMock for async methods
        mock.cleanup = MagicMock()
        yield mock


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
