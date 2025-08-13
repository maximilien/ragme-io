#!/usr/bin/env python3
"""
Unit tests for VDB Management Tool

Tests the VDBManager class and related functionality for managing
vector database collections independently of the RAGme UI and APIs.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add the src directory to the Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ragme.vdbs.vdb_management import VDBManager, print_emoji_status


class TestVDBManager(unittest.TestCase):
    """Test cases for VDBManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the config manager
        self.mock_config = Mock()
        self.mock_config.get_text_collection_name.return_value = "RagMeDocs"
        self.mock_config.get_image_collection_name.return_value = "RagMeImages"
        self.mock_config.get.return_value = "weaviate-cloud"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {"VECTOR_DB_TYPE": "weaviate-cloud"})
        self.env_patcher.start()

        # Mock the config import
        self.config_patcher = patch(
            "ragme.vdbs.vdb_management.config", self.mock_config
        )
        self.config_patcher.start()

        # Create VDBManager instance
        self.vdb_manager = VDBManager()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        self.config_patcher.stop()

    def test_init(self):
        """Test VDBManager initialization."""
        self.assertEqual(self.vdb_manager.vdb_type, "weaviate-cloud")
        self.assertEqual(self.vdb_manager.text_collection_name, "RagMeDocs")
        self.assertEqual(self.vdb_manager.image_collection_name, "RagMeImages")

    def test_show_config(self):
        """Test show_config method."""
        config_info = self.vdb_manager.show_config()

        expected = {
            "vdb_type": "weaviate-cloud",
            "text_collection": "RagMeDocs",
            "image_collection": "RagMeImages",
            "config_source": "config.yaml + .env",
        }

        self.assertEqual(config_info, expected)

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_check_health_success(self, mock_create_vdb):
        """Test check_health method with successful connections."""
        # Mock VDB instances
        mock_text_vdb = Mock()
        mock_text_vdb.count_documents.return_value = 10

        mock_image_vdb = Mock()
        mock_image_vdb.count_documents.return_value = 5

        # Configure mock to return different VDBs based on collection name
        def create_vdb_side_effect(collection_name):
            if collection_name == "RagMeDocs":
                return mock_text_vdb
            elif collection_name == "RagMeImages":
                return mock_image_vdb
            return Mock()

        mock_create_vdb.side_effect = create_vdb_side_effect

        health_info = self.vdb_manager.check_health()

        self.assertEqual(health_info["status"], "healthy")
        self.assertEqual(health_info["vdb_type"], "weaviate-cloud")
        self.assertEqual(len(health_info["errors"]), 0)

        # Check text collection
        text_coll = health_info["collections"]["text"]
        self.assertEqual(text_coll["status"], "healthy")
        self.assertEqual(text_coll["document_count"], 10)
        self.assertEqual(text_coll["name"], "RagMeDocs")

        # Check image collection
        image_coll = health_info["collections"]["image"]
        self.assertEqual(image_coll["status"], "healthy")
        self.assertEqual(image_coll["document_count"], 5)
        self.assertEqual(image_coll["name"], "RagMeImages")

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_check_health_failure(self, mock_create_vdb):
        """Test check_health method with connection failures."""
        # Mock VDB instances that raise exceptions
        mock_create_vdb.side_effect = Exception("Connection failed")

        health_info = self.vdb_manager.check_health()

        self.assertEqual(health_info["status"], "unhealthy")
        self.assertEqual(health_info["vdb_type"], "weaviate-cloud")
        self.assertEqual(len(health_info["errors"]), 2)

        # Check text collection error
        text_coll = health_info["collections"]["text"]
        self.assertEqual(text_coll["status"], "error")
        self.assertIn("Connection failed", text_coll["error"])

        # Check image collection error
        image_coll = health_info["collections"]["image"]
        self.assertEqual(image_coll["status"], "error")
        self.assertIn("Connection failed", image_coll["error"])

    def test_list_collections(self):
        """Test list_collections method."""
        collections = self.vdb_manager.list_collections()

        expected = {
            "text_collection": {"name": "RagMeDocs", "type": "text"},
            "image_collection": {"name": "RagMeImages", "type": "image"},
        }

        self.assertEqual(collections, expected)

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_list_text_documents_success(self, mock_create_vdb):
        """Test list_text_documents method with success."""
        mock_vdb = Mock()
        mock_documents = [
            {"id": "1", "url": "http://example.com", "text": "Sample text"},
            {"id": "2", "url": "http://example2.com", "text": "Another text"},
        ]
        mock_vdb.list_documents.return_value = mock_documents

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.list_text_documents(limit=50)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeDocs")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["documents"], mock_documents)

        # Verify the VDB was called correctly
        mock_create_vdb.assert_called_once_with(collection_name="RagMeDocs")
        mock_vdb.list_documents.assert_called_once_with(limit=50, offset=0)

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_list_text_documents_failure(self, mock_create_vdb):
        """Test list_text_documents method with failure."""
        mock_create_vdb.side_effect = Exception("VDB error")

        result = self.vdb_manager.list_text_documents()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["collection"], "RagMeDocs")
        self.assertIn("VDB error", result["error"])

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_list_image_documents_success(self, mock_create_vdb):
        """Test list_image_documents method with success."""
        mock_vdb = Mock()
        mock_documents = [
            {
                "id": "1",
                "url": "http://example.com/image.jpg",
                "image_data": "base64data",
            },
            {
                "id": "2",
                "url": "http://example2.com/image.png",
                "image_data": "base64data2",
            },
        ]
        mock_vdb.list_documents.return_value = mock_documents

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.list_image_documents(limit=30)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeImages")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["documents"], mock_documents)

        # Verify the VDB was called correctly
        mock_create_vdb.assert_called_once_with(collection_name="RagMeImages")
        mock_vdb.list_documents.assert_called_once_with(limit=30, offset=0)

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_list_image_documents_failure(self, mock_create_vdb):
        """Test list_image_documents method with failure."""
        mock_create_vdb.side_effect = Exception("Image VDB error")

        result = self.vdb_manager.list_image_documents()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["collection"], "RagMeImages")
        self.assertIn("Image VDB error", result["error"])

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_delete_text_collection_content_empty(self, mock_create_vdb):
        """Test delete_text_collection_content with empty collection."""
        mock_vdb = Mock()
        mock_vdb.list_documents.return_value = []

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.delete_text_collection_content()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeDocs")
        self.assertEqual(result["deleted_count"], 0)
        self.assertIn("already empty", result["message"])

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_delete_text_collection_content_success(self, mock_create_vdb):
        """Test delete_text_collection_content with documents to delete."""
        mock_vdb = Mock()
        mock_documents = [
            {"id": "1", "url": "http://example.com", "text": "Sample text"},
            {"id": "2", "url": "http://example2.com", "text": "Another text"},
        ]
        mock_vdb.list_documents.return_value = mock_documents
        mock_vdb.delete_document.return_value = None

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.delete_text_collection_content()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeDocs")
        self.assertEqual(result["deleted_count"], 2)
        self.assertIn("Successfully deleted 2 documents", result["message"])

        # Verify delete_document was called for each document
        self.assertEqual(mock_vdb.delete_document.call_count, 2)
        mock_vdb.delete_document.assert_any_call("1")
        mock_vdb.delete_document.assert_any_call("2")

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_delete_text_collection_content_partial_failure(self, mock_create_vdb):
        """Test delete_text_collection_content with some delete failures."""
        mock_vdb = Mock()
        mock_documents = [
            {"id": "1", "url": "http://example.com", "text": "Sample text"},
            {"id": "2", "url": "http://example2.com", "text": "Another text"},
        ]
        mock_vdb.list_documents.return_value = mock_documents

        # First delete succeeds, second fails
        def delete_side_effect(doc_id):
            if doc_id == "1":
                return None
            else:
                raise Exception("Delete failed")

        mock_vdb.delete_document.side_effect = delete_side_effect

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.delete_text_collection_content()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeDocs")
        self.assertEqual(result["deleted_count"], 1)  # Only one successful deletion
        self.assertIn("Successfully deleted 1 documents", result["message"])

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_delete_image_collection_content_success(self, mock_create_vdb):
        """Test delete_image_collection_content with documents to delete."""
        mock_vdb = Mock()
        mock_documents = [
            {
                "id": "1",
                "url": "http://example.com/image.jpg",
                "image_data": "base64data",
            },
            {
                "id": "2",
                "url": "http://example2.com/image.png",
                "image_data": "base64data2",
            },
        ]
        mock_vdb.list_documents.return_value = mock_documents
        mock_vdb.delete_document.return_value = None

        mock_create_vdb.return_value = mock_vdb

        result = self.vdb_manager.delete_image_collection_content()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["collection"], "RagMeImages")
        self.assertEqual(result["deleted_count"], 2)
        self.assertIn("Successfully deleted 2 documents", result["message"])

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_delete_image_collection_content_failure(self, mock_create_vdb):
        """Test delete_image_collection_content with VDB error."""
        mock_create_vdb.side_effect = Exception("Image VDB error")

        result = self.vdb_manager.delete_image_collection_content()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["collection"], "RagMeImages")
        self.assertIn("Image VDB error", result["error"])


class TestPrintEmojiStatus(unittest.TestCase):
    """Test cases for print_emoji_status function."""

    @patch("builtins.print")
    def test_print_emoji_status_success(self, mock_print):
        """Test print_emoji_status with success status."""
        print_emoji_status("success", "Operation completed")
        mock_print.assert_called_once_with("✅ Operation completed")

    @patch("builtins.print")
    def test_print_emoji_status_error(self, mock_print):
        """Test print_emoji_status with error status."""
        print_emoji_status("error", "Operation failed")
        mock_print.assert_called_once_with("❌ Operation failed")

    @patch("builtins.print")
    def test_print_emoji_status_warning(self, mock_print):
        """Test print_emoji_status with warning status."""
        print_emoji_status("warning", "Be careful")
        mock_print.assert_called_once_with("⚠️ Be careful")

    @patch("builtins.print")
    def test_print_emoji_status_info(self, mock_print):
        """Test print_emoji_status with info status."""
        print_emoji_status("info", "Information")
        mock_print.assert_called_once_with("ℹ️ Information")

    @patch("builtins.print")
    def test_print_emoji_status_unknown(self, mock_print):
        """Test print_emoji_status with unknown status."""
        print_emoji_status("unknown", "Unknown status")
        mock_print.assert_called_once_with("ℹ️ Unknown status")


class TestVDBManagerIntegration(unittest.TestCase):
    """Integration tests for VDBManager with real configuration."""

    @patch("ragme.vdbs.vdb_management.create_vector_database")
    def test_integration_with_real_config(self, mock_create_vdb):
        """Test VDBManager integration with real configuration loading."""
        # This test verifies that the VDBManager can work with the real config system
        # but mocks the actual VDB operations to avoid external dependencies

        mock_vdb = Mock()
        mock_vdb.count_documents.return_value = 0
        mock_vdb.list_documents.return_value = []
        mock_create_vdb.return_value = mock_vdb

        # Create VDBManager instance (this will load real config)
        manager = VDBManager()

        # Test that we can get configuration info
        config_info = manager.show_config()
        self.assertIn("vdb_type", config_info)
        self.assertIn("text_collection", config_info)
        self.assertIn("image_collection", config_info)
        self.assertIn("config_source", config_info)

        # Test that we can list collections
        collections = manager.list_collections()
        self.assertIn("text_collection", collections)
        self.assertIn("image_collection", collections)


if __name__ == "__main__":
    unittest.main()
