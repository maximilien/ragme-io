# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.ragme.agents.tools import RagMeTools
from src.ragme.utils.common import filter_items_by_date_range, parse_date_query


class TestDateTimeListing:
    """Test datetime-based listing functionality."""

    def test_parse_date_query_today(self):
        """Test parsing 'today' date query."""
        start_date, end_date = parse_date_query("today")

        now = datetime.now()
        expected_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        assert start_date.date() == expected_start.date()
        assert end_date.date() == expected_end.date()
        assert start_date.hour == 0
        assert end_date.hour == 23

    def test_parse_date_query_yesterday(self):
        """Test parsing 'yesterday' date query."""
        start_date, end_date = parse_date_query("yesterday")

        yesterday = datetime.now() - timedelta(days=1)
        expected_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_end = yesterday.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        assert start_date.date() == expected_start.date()
        assert end_date.date() == expected_end.date()

    def test_parse_date_query_this_week(self):
        """Test parsing 'this week' date query."""
        start_date, end_date = parse_date_query("this week")

        now = datetime.now()
        expected_start = now - timedelta(days=now.weekday())
        expected_start = expected_start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        assert start_date.date() == expected_start.date()
        assert end_date.date() == expected_end.date()

    def test_parse_date_query_last_week(self):
        """Test parsing 'last week' date query."""
        start_date, end_date = parse_date_query("last week")

        now = datetime.now()
        expected_start = now - timedelta(days=now.weekday() + 7)
        expected_start = expected_start.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected_end = expected_start + timedelta(
            days=6, hours=23, minutes=59, seconds=59, microseconds=999999
        )

        assert start_date.date() == expected_start.date()
        assert end_date.date() == expected_end.date()

    def test_parse_date_query_days_ago(self):
        """Test parsing 'X days ago' date query."""
        start_date, end_date = parse_date_query("3 days ago")

        target_date = datetime.now() - timedelta(days=3)
        expected_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_end = target_date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        assert start_date.date() == expected_start.date()
        assert end_date.date() == expected_end.date()

    def test_parse_date_query_invalid(self):
        """Test parsing invalid date query."""
        result = parse_date_query("invalid date query")
        assert result is None

    def test_filter_items_by_date_range(self):
        """Test filtering items by date range."""
        # Create test items with different dates
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)

        items = [
            {"id": "1", "metadata": {"date_added": now.isoformat()}},
            {"id": "2", "metadata": {"date_added": yesterday.isoformat()}},
            {"id": "3", "metadata": {"date_added": last_week.isoformat()}},
            {
                "id": "4",
                "metadata": {},  # No date
            },
        ]

        # Filter for yesterday
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        filtered = filter_items_by_date_range(items, start_date, end_date)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "2"

    def test_filter_items_by_date_range_json_metadata(self):
        """Test filtering items with JSON string metadata."""
        import json

        now = datetime.now()
        yesterday = now - timedelta(days=1)

        items = [
            {"id": "1", "metadata": json.dumps({"date_added": now.isoformat()})},
            {"id": "2", "metadata": json.dumps({"date_added": yesterday.isoformat()})},
        ]

        # Filter for yesterday
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        filtered = filter_items_by_date_range(items, start_date, end_date)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "2"

    @patch("src.ragme.agents.tools.parse_date_query")
    @patch("src.ragme.agents.tools.filter_items_by_date_range")
    def test_list_documents_by_datetime(self, mock_filter, mock_parse):
        """Test list_documents_by_datetime tool."""
        # Setup mocks
        mock_ragme = Mock()
        mock_ragme.list_documents.return_value = [
            {
                "id": "1",
                "url": "test.com",
                "text": "test",
                "metadata": {"date_added": "2025-01-01T00:00:00"},
            }
        ]

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)
        mock_parse.return_value = (start_date, end_date)
        mock_filter.return_value = [
            {
                "id": "1",
                "url": "test.com",
                "text": "test",
                "metadata": {"date_added": "2025-01-01T00:00:00"},
            }
        ]

        tools = RagMeTools(mock_ragme)
        result = tools.list_documents_by_datetime("yesterday")

        assert "Found 1 documents for yesterday" in result
        assert "test.com" in result
        mock_parse.assert_called_once_with("yesterday")
        mock_filter.assert_called_once()

    @patch("src.ragme.agents.tools.parse_date_query")
    @patch("src.ragme.agents.tools.filter_items_by_date_range")
    @patch("src.ragme.vdbs.vector_db_factory.create_vector_database")
    @patch("src.ragme.utils.config_manager.config")
    def test_list_images_by_datetime(
        self, mock_config, mock_create_vdb, mock_filter, mock_parse
    ):
        """Test list_images_by_datetime tool."""
        import json

        # Setup mocks
        mock_ragme = Mock()
        mock_config.get_image_collection_name.return_value = "TestImages"

        # Mock the vector database
        mock_vdb = Mock()
        mock_vdb.list_images.return_value = [
            {
                "id": "1",
                "url": "test.jpg",
                "metadata": json.dumps(
                    {
                        "date_added": "2025-01-01T00:00:00",
                        "classification": {
                            "top_prediction": {"label": "photo", "confidence": 0.95}
                        },
                    }
                ),
            }
        ]
        mock_create_vdb.return_value = mock_vdb

        start_date = datetime(2025, 1, 1, 0, 0, 0)
        end_date = datetime(2025, 1, 1, 23, 59, 59)
        mock_parse.return_value = (start_date, end_date)
        mock_filter.return_value = [
            {
                "id": "1",
                "url": "test.jpg",
                "metadata": json.dumps(
                    {
                        "date_added": "2025-01-01T00:00:00",
                        "classification": {
                            "top_prediction": {"label": "photo", "confidence": 0.95}
                        },
                    }
                ),
            }
        ]

        tools = RagMeTools(mock_ragme)
        result = tools.list_images_by_datetime("yesterday")

        assert "Found 1 images for yesterday" in result
        assert "test.jpg" in result
        assert "photo" in result
        mock_parse.assert_called_once_with("yesterday")
        mock_filter.assert_called_once()

    def test_list_documents_by_datetime_invalid_query(self):
        """Test list_documents_by_datetime with invalid date query."""
        mock_ragme = Mock()
        tools = RagMeTools(mock_ragme)

        with patch("src.ragme.agents.tools.parse_date_query", return_value=None):
            result = tools.list_documents_by_datetime("invalid date")

        assert "Could not understand the date query" in result
        assert "Supported formats" in result

    def test_list_images_by_datetime_invalid_query(self):
        """Test list_images_by_datetime with invalid date query."""
        mock_ragme = Mock()
        tools = RagMeTools(mock_ragme)

        with patch("src.ragme.agents.tools.parse_date_query", return_value=None):
            result = tools.list_images_by_datetime("invalid date")

        assert "Could not understand the date query" in result
        assert "Supported formats" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
