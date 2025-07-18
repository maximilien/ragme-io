# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")

import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.ragme.api import app

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_ragme():
    """Mock the RagMe instance."""
    with patch('src.ragme.api.ragme') as mock:
        # Setup mock methods
        mock.write_json_to_weaviate = MagicMock()
        mock.run = MagicMock()
        mock.cleanup = MagicMock()
        yield mock

def test_add_json_success(client, mock_ragme):
    """Test successful JSON addition with metadata."""
    test_data = {
        "data": {
            "title": "Test Document",
            "content": "This is a test document",
            "tags": ["test", "example"]
        },
        "metadata": {
            "source": "test",
            "timestamp": "2024-03-20"
        }
    }
    
    response = client.post("/add-json", json=test_data)
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Successfully processed JSON content"
    }
    mock_ragme.write_json_to_weaviate.assert_called_once_with(
        test_data["data"],
        test_data["metadata"]
    )

def test_add_json_without_metadata(client, mock_ragme):
    """Test successful JSON addition without metadata."""
    test_data = {
        "data": {
            "title": "Test Document",
            "content": "This is a test document"
        }
    }
    
    response = client.post("/add-json", json=test_data)
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Successfully processed JSON content"
    }
    mock_ragme.write_json_to_weaviate.assert_called_once_with(
        test_data["data"],
        None
    )

def test_add_json_error(client, mock_ragme):
    """Test error handling when adding JSON."""
    test_data = {
        "data": {
            "title": "Test Document"
        }
    }
    
    # Simulate an error in write_json_to_weaviate
    mock_ragme.write_json_to_weaviate.side_effect = Exception("Test error")
    
    response = client.post("/add-json", json=test_data)
    
    assert response.status_code == 500
    assert response.json() == {"detail": "Test error"}

def test_add_json_invalid_input(client):
    """Test invalid input validation."""
    # Test missing data
    response = client.post("/add-json", json={"metadata": {"source": "test"}})
    assert response.status_code == 422
    
    # Test invalid data type
    response = client.post("/add-json", json={"data": "not a dict"})
    assert response.status_code == 422
    
    # Test invalid metadata type
    response = client.post("/add-json", json={
        "data": {"title": "test"},
        "metadata": "not a dict"
    })
    assert response.status_code == 422

def test_add_json_complex_data(client, mock_ragme):
    """Test adding complex nested JSON data."""
    test_data = {
        "data": {
            "title": "Complex Document",
            "sections": [
                {
                    "name": "Section 1",
                    "content": "Content 1",
                    "nested": {
                        "key": "value",
                        "array": [1, 2, 3]
                    }
                },
                {
                    "name": "Section 2",
                    "content": "Content 2"
                }
            ],
            "metadata": {
                "version": 1.0,
                "tags": ["complex", "nested", "test"]
            }
        },
        "metadata": {
            "source": "test",
            "timestamp": "2024-03-20",
            "author": "Test User",
            "version": "1.0.0"
        }
    }
    
    response = client.post("/add-json", json=test_data)
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Successfully processed JSON content"
    }
    mock_ragme.write_json_to_weaviate.assert_called_once_with(
        test_data["data"],
        test_data["metadata"]
    ) 