# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Tests for PDF image extraction functionality.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ragme.utils.config_manager import config
from ragme.utils.pdf_image_extractor import pdf_image_extractor


class TestPDFImageExtraction(unittest.TestCase):
    """Test cases for PDF image extraction functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_pdf = "tests/fixtures/pdfs/ragme-io.pdf"
        self.assertTrue(
            os.path.exists(self.test_pdf), f"Test PDF not found: {self.test_pdf}"
        )

    def test_configuration_loading(self):
        """Test that PDF image extraction configuration is properly loaded."""
        pdf_config = config.get("pdf_image_extraction", {})

        # Check required fields
        required_fields = [
            "enabled",
            "min_image_size_kb",
            "max_image_size_mb",
            "supported_formats",
        ]
        for field in required_fields:
            self.assertIn(
                field, pdf_config, f"Missing required configuration field: {field}"
            )

        # Check data types
        self.assertIsInstance(pdf_config["enabled"], bool)
        self.assertIsInstance(pdf_config["min_image_size_kb"], int)
        self.assertIsInstance(pdf_config["max_image_size_mb"], int)
        self.assertIsInstance(pdf_config["supported_formats"], list)

    def test_image_extraction(self):
        """Test extracting images from a PDF."""
        extracted_images = pdf_image_extractor.extract_images_from_pdf(
            self.test_pdf, "test_pdf.pdf", "documents/test_pdf.pdf"
        )

        # Should extract some images from the test PDF
        self.assertGreater(
            len(extracted_images), 0, "Should extract at least one image"
        )

        # Check structure of extracted images
        for img in extracted_images:
            self.assertIn("url", img)
            self.assertIn("image_data", img)
            self.assertIn("metadata", img)

            # Check metadata structure
            metadata = img["metadata"]
            self.assertEqual(metadata["source_type"], "pdf_extracted_image")
            self.assertEqual(metadata["pdf_filename"], "test_pdf.pdf")
            self.assertIn("pdf_page_number", metadata)
            self.assertIn("pdf_image_name", metadata)
            self.assertIn("extraction_timestamp", metadata)

    def test_image_size_constraints(self):
        """Test image size constraint checking."""
        # Test with valid size
        valid_data = b"x" * 2048  # 2KB
        self.assertTrue(pdf_image_extractor._check_image_size_constraints(valid_data))

        # Test with too small size
        small_data = b"x" * 512  # 0.5KB
        self.assertFalse(pdf_image_extractor._check_image_size_constraints(small_data))

        # Test with too large size
        large_data = b"x" * (15 * 1024 * 1024)  # 15MB
        self.assertFalse(pdf_image_extractor._check_image_size_constraints(large_data))

    def test_supported_format_checking(self):
        """Test supported format checking."""
        # Test with unsupported format (raw data)
        raw_data = b"raw image data"
        format_info = pdf_image_extractor._get_image_format_info(raw_data)
        self.assertFalse(format_info["supported"])

        # Test that the method exists and is callable
        self.assertTrue(hasattr(pdf_image_extractor, "_get_image_format_info"))
        self.assertTrue(callable(pdf_image_extractor._get_image_format_info))

    def test_error_handling(self):
        """Test error handling for various edge cases."""
        # Test with non-existent PDF
        extracted_images = pdf_image_extractor.extract_images_from_pdf(
            "non_existent.pdf", "test.pdf", None
        )
        self.assertEqual(len(extracted_images), 0)

        # Test with empty PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(
                b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n/Count 0\n>>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n108\n%%EOF\n"
            )
            temp_path = temp_file.name

        try:
            extracted_images = pdf_image_extractor.extract_images_from_pdf(
                temp_path, "empty.pdf", None
            )
            self.assertEqual(len(extracted_images), 0)
        finally:
            os.unlink(temp_path)

    def test_metadata_creation(self):
        """Test metadata creation for extracted images."""
        # Create sample processed data
        processed_data = {
            "classification": {
                "top_prediction": {"label": "test_image", "confidence": 0.95}
            },
            "ocr_content": {"text": "Test caption", "confidence": 0.88},
            "size": 1024,
            "format": "jpeg",
        }

        metadata = pdf_image_extractor._create_image_metadata(
            "test_image.jpg", 5, "test.pdf", "documents/test.pdf", processed_data
        )

        # Check required fields
        self.assertEqual(metadata["source_type"], "pdf_extracted_image")
        self.assertEqual(metadata["pdf_filename"], "test.pdf")
        self.assertEqual(metadata["pdf_page_number"], 5)
        self.assertEqual(metadata["pdf_image_name"], "test_image.jpg")
        self.assertEqual(metadata["pdf_storage_path"], "documents/test.pdf")
        self.assertIn("extraction_timestamp", metadata)
        self.assertEqual(metadata["extracted_caption"], "Test caption")

        # Check that original data is preserved
        self.assertEqual(metadata["classification"], processed_data["classification"])
        self.assertEqual(metadata["ocr_content"], processed_data["ocr_content"])

    def test_collection_integration(self):
        """Test integration with vector database collection."""
        # Extract images
        extracted_images = pdf_image_extractor.extract_images_from_pdf(
            self.test_pdf, "test_pdf.pdf", "documents/test_pdf.pdf"
        )

        if extracted_images:
            # Test adding to collection (this might fail if no vector database is configured)
            try:
                success = pdf_image_extractor.add_extracted_images_to_collection(
                    extracted_images
                )
                # Should succeed or fail gracefully, but not raise an exception
                self.assertIsInstance(success, bool)
            except Exception as e:
                # If vector database is not configured, that's okay for unit tests
                self.assertIn("vector database", str(e).lower())


if __name__ == "__main__":
    unittest.main()
