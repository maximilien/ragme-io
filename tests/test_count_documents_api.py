# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.ragme.apis.api import app


class TestCountDocumentsAPI:
    """Test suite for the count-documents API endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_success_all_filter(self, mock_get_ragme):
        """Test successful document count with 'all' date filter using efficient method."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(return_value=3)

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 3
        assert data["date_filter"] == "all"

        # Verify efficient method was called
        mock_ragme_instance.vector_db.count_documents.assert_called_once_with("all")

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_success_current_filter(self, mock_get_ragme):
        """Test successful document count with 'current' date filter using efficient method."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(return_value=1)

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents?date_filter=current")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert data["date_filter"] == "current"

        # Verify efficient method was called
        mock_ragme_instance.vector_db.count_documents.assert_called_once_with("current")

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_empty_collection(self, mock_get_ragme):
        """Test document count when collection is empty."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(return_value=0)

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["date_filter"] == "all"

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_error_handling(self, mock_get_ragme):
        """Test error handling when count_documents raises exception."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(
            side_effect=Exception("Database connection failed")
        )

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents")

        # Verify error response
        assert response.status_code == 500
        assert "Database connection failed" in response.text

    def test_count_documents_invalid_date_filter(self):
        """Test with invalid date filter parameter."""
        # Make request with invalid date filter
        response = self.client.get("/count-documents?date_filter=invalid")

        # Should still work but pass invalid filter to filter function
        # The filter function will handle the invalid filter
        assert response.status_code in [200, 422]  # Depending on validation

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_month_filter(self, mock_get_ragme):
        """Test document count with 'month' date filter."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(return_value=5)

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents?date_filter=month")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 5
        assert data["date_filter"] == "month"

        # Verify efficient method was called
        mock_ragme_instance.vector_db.count_documents.assert_called_once_with("month")

    @patch("src.ragme.apis.api.get_ragme")
    def test_count_documents_year_filter(self, mock_get_ragme):
        """Test document count with 'year' date filter."""
        # Create a mock RagMe instance
        mock_ragme_instance = MagicMock()
        mock_ragme_instance.vector_db.count_documents = Mock(return_value=75)

        # Make get_ragme() return the mock instance
        mock_get_ragme.return_value = mock_ragme_instance

        # Make request
        response = self.client.get("/count-documents?date_filter=year")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 75
        assert data["date_filter"] == "year"

        # Verify efficient method was called
        mock_ragme_instance.vector_db.count_documents.assert_called_once_with("year")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
