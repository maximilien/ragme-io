# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import csv
import os
import tempfile
import unittest
from pathlib import Path

from src.ragme.data_processing.report_generator import ReportGenerator


class TestReportGenerator(unittest.TestCase):
    """Test cases for the ReportGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.report_generator = ReportGenerator(self.temp_dir)

    def tearDown(self):
        """Clean up after tests."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test report generator initialization."""
        self.assertEqual(str(self.report_generator.output_directory), self.temp_dir)

    def test_aggregate_results_empty(self):
        """Test aggregation with empty results."""
        results = []
        stats = self.report_generator.aggregate_results(results)

        self.assertEqual(stats["total_files"], 0)
        self.assertEqual(stats["successful_files"], 0)
        self.assertEqual(stats["failed_files"], 0)
        self.assertEqual(stats["total_documents"], 0)
        self.assertEqual(stats["total_images"], 0)
        self.assertEqual(stats["avg_processing_time"], 0)

    def test_aggregate_results_mixed(self):
        """Test aggregation with mixed success/failure results."""
        results = [
            {
                "file_name": "doc1.pdf",
                "file_type": "document",
                "success": True,
                "chunk_count": 5,
                "extracted_images": [{"name": "img1"}, {"name": "img2"}],
                "errors": [],
                "timing": {"total": 2.5},
                "file_size_kb": 100.0,
                "retry_count": 0,
            },
            {
                "file_name": "img1.jpg",
                "file_type": "image",
                "success": True,
                "errors": [],
                "timing": {"total": 1.0},
                "file_size_kb": 50.0,
                "retry_count": 1,
            },
            {
                "file_name": "doc2.pdf",
                "file_type": "document",
                "success": False,
                "chunk_count": 0,
                "extracted_images": [],
                "errors": ["Failed to parse", "Corrupted file"],
                "timing": {"total": 0.5},
                "file_size_kb": 75.0,
                "retry_count": 3,
            },
        ]

        stats = self.report_generator.aggregate_results(results)

        self.assertEqual(stats["total_files"], 3)
        self.assertEqual(stats["successful_files"], 2)
        self.assertEqual(stats["failed_files"], 1)
        self.assertEqual(stats["total_documents"], 2)
        self.assertEqual(stats["total_images"], 1)
        self.assertEqual(stats["total_chunks"], 5)
        self.assertEqual(stats["total_extracted_images"], 2)
        self.assertEqual(stats["total_errors"], 2)  # Only from failed file

        # Check averages
        expected_avg_time = (2.5 + 1.0 + 0.5) / 3
        self.assertAlmostEqual(
            stats["avg_processing_time"], expected_avg_time, places=2
        )

        expected_avg_size = (100.0 + 50.0 + 75.0) / 3
        self.assertAlmostEqual(stats["avg_file_size_kb"], expected_avg_size, places=2)

        expected_doc_time = (2.5 + 0.5) / 2  # Two documents
        self.assertAlmostEqual(stats["avg_document_time"], expected_doc_time, places=2)

        self.assertEqual(stats["avg_image_time"], 1.0)  # One image

    def test_create_processed_file(self):
        """Test creation of .processed file."""
        test_result = {
            "file_name": "test.pdf",
            "file_size_kb": 123.45,
            "file_type": "document",
            "document_type": "pdf",
            "success": True,
            "chunk_count": 3,
            "average_chunk_size_kb": 15.5,
            "extracted_images": [
                {
                    "file_size_kb": 10.0,
                    "exif_extracted": True,
                    "ai_classification_features": 5,
                    "ocr_success": True,
                    "ocr_text_length": 25,
                    "errors": [],
                }
            ],
            "errors": [],
            "timing": {"total": 2.5, "text_extraction": 1.0, "chunking": 0.5},
            "processing_start_time": "2025-01-01T12:00:00",
            "metadata": {"author": "Test Author", "title": "Test Document"},
            "retry_count": 0,
        }

        # Create test file path
        test_file_path = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file_path, "w") as f:
            f.write("dummy content")

        # Create processed file
        self.report_generator.create_processed_file(test_file_path, test_result)

        # Check if .processed file was created
        processed_file_path = test_file_path + ".processed"
        self.assertTrue(os.path.exists(processed_file_path))

        # Read and verify content
        with open(processed_file_path, encoding="utf-8") as f:
            content = f.read()

        # Check for key sections
        self.assertIn("RAGme Document Processing Pipeline", content)
        self.assertIn("FILE INFORMATION", content)
        self.assertIn("PROCESSING RESULTS", content)
        self.assertIn("✅ SUCCESS", content)
        self.assertIn("test.pdf", content)
        self.assertIn("123.45 KB", content)
        self.assertIn("Text Chunks: 3", content)
        self.assertIn("EXTRACTED IMAGES PROCESSING", content)
        self.assertIn("TIMING BREAKDOWN", content)
        self.assertIn("Total Time: 2.500s", content)
        self.assertIn("DOCUMENT METADATA", content)
        self.assertIn("Test Author", content)

    def test_create_csv_report(self):
        """Test creation of CSV report."""
        results = [
            {
                "file_name": "doc1.pdf",
                "file_size_kb": 100.0,
                "file_type": "document",
                "document_type": "pdf",
                "chunk_count": 5,
                "average_chunk_size_kb": 20.0,
                "extracted_images": [
                    {
                        "exif_extracted": True,
                        "ai_classification_features": 3,
                        "ocr_success": True,
                        "ocr_text_length": 50,
                    }
                ],
                "errors": [],
                "timing": {"total": 2.5},
                "processing_start_time": "2025-01-01T12:00:00",
                "success": True,
                "retry_count": 0,
            },
            {
                "file_name": "img1.jpg",
                "file_size_kb": 50.0,
                "file_type": "image",
                "document_type": "",
                "extracted_images": [],
                "exif_extracted": False,
                "ai_classification_features": 2,
                "ocr_success": False,
                "ocr_text_length": 0,
                "errors": ["OCR failed"],
                "timing": {"total": 1.0},
                "processing_start_time": "2025-01-01T12:01:00",
                "success": False,
                "retry_count": 2,
            },
        ]

        self.report_generator.create_csv_report(results, "test_results.csv")

        # Check if CSV file was created
        csv_file_path = os.path.join(self.temp_dir, "test_results.csv")
        self.assertTrue(os.path.exists(csv_file_path))

        # Read and verify CSV content
        with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        self.assertEqual(len(rows), 2)

        # Check first row (document)
        row1 = rows[0]
        self.assertEqual(row1["file_name"], "doc1.pdf")
        self.assertEqual(row1["file_size_kb"], "100.0")
        self.assertEqual(row1["file_type"], "document")
        self.assertEqual(row1["document_type"], "pdf")
        self.assertEqual(row1["chunk_count"], "5")
        self.assertEqual(row1["avg_chunk_size_kb"], "20.0")
        self.assertEqual(row1["extracted_images_count"], "1")
        self.assertEqual(row1["total_errors"], "0")
        self.assertEqual(row1["exif_extracted"], "True")
        self.assertEqual(row1["ai_classification_features"], "3")
        self.assertEqual(row1["ocr_success"], "True")
        self.assertEqual(row1["ocr_text_length"], "50")
        self.assertEqual(row1["processing_time_seconds"], "2.5")
        self.assertEqual(row1["success"], "True")
        self.assertEqual(row1["retry_count"], "0")

        # Check second row (image)
        row2 = rows[1]
        self.assertEqual(row2["file_name"], "img1.jpg")
        self.assertEqual(row2["file_size_kb"], "50.0")
        self.assertEqual(row2["file_type"], "image")
        self.assertEqual(row2["document_type"], "")
        self.assertEqual(row2["chunk_count"], "")  # Empty for images
        self.assertEqual(row2["avg_chunk_size_kb"], "")  # Empty for images
        self.assertEqual(row2["extracted_images_count"], "")  # Empty for images
        self.assertEqual(row2["total_errors"], "1")
        self.assertEqual(row2["exif_extracted"], "False")
        self.assertEqual(row2["ai_classification_features"], "2")
        self.assertEqual(row2["ocr_success"], "False")
        self.assertEqual(row2["ocr_text_length"], "0")
        self.assertEqual(row2["processing_time_seconds"], "1.0")
        self.assertEqual(row2["success"], "False")
        self.assertEqual(row2["retry_count"], "2")

    def test_load_processed_files_results_empty(self):
        """Test loading processed files when directory is empty."""
        processed_files = self.report_generator.load_processed_files_results()
        self.assertEqual(len(processed_files), 0)

    def test_load_processed_files_results_with_files(self):
        """Test loading processed files when .processed files exist."""
        # Create some .processed files
        test_files = ["doc1.pdf", "img1.jpg", "doc2.docx"]

        for file_name in test_files:
            processed_path = os.path.join(self.temp_dir, file_name + ".processed")
            with open(processed_path, "w") as f:
                f.write("dummy processed content")

        # Also create a non-.processed file to ensure it's ignored
        with open(os.path.join(self.temp_dir, "other.txt"), "w") as f:
            f.write("not processed")

        processed_files = self.report_generator.load_processed_files_results()

        # Should find the original file names (without .processed extension)
        expected_files = [
            os.path.join(self.temp_dir, "doc1.pdf"),
            os.path.join(self.temp_dir, "img1.jpg"),
            os.path.join(self.temp_dir, "doc2.docx"),
        ]

        self.assertEqual(len(processed_files), 3)
        for expected_file in expected_files:
            self.assertIn(expected_file, processed_files)

    def test_generate_human_readable_summary_document(self):
        """Test human-readable summary generation for document."""
        result = {
            "file_name": "test.pdf",
            "file_size_kb": 123.45,
            "file_type": "document",
            "document_type": "pdf",
            "success": True,
            "chunk_count": 3,
            "average_chunk_size_kb": 41.15,
            "extracted_images": [],
            "errors": [],
            "timing": {
                "total": 2.5,
                "text_extraction": 1.5,
                "chunking": 0.5,
                "vdb_storage": 0.5,
            },
            "processing_start_time": "2025-01-01T12:00:00",
            "metadata": {"page_count": 5, "author": "Test Author"},
            "retry_count": 0,
        }

        summary = self.report_generator._generate_human_readable_summary(result)

        # Check key content
        self.assertIn("RAGme Document Processing Pipeline", summary)
        self.assertIn("test.pdf", summary)
        self.assertIn("123.45 KB", summary)
        self.assertIn("✅ SUCCESS", summary)
        self.assertIn("Text Chunks: 3", summary)
        self.assertIn("Pages: 5", summary)
        self.assertIn("Images Extracted: 0", summary)
        self.assertIn("Text Extraction: 1.500s", summary)
        self.assertIn("Total Time: 2.500s", summary)
        self.assertIn("Test Author", summary)
        self.assertNotIn("❌ ERRORS", summary)  # No errors section

    def test_generate_human_readable_summary_image(self):
        """Test human-readable summary generation for image."""
        result = {
            "file_name": "test.jpg",
            "file_size_kb": 67.89,
            "file_type": "image",
            "success": True,
            "exif_extracted": True,
            "ai_classification_features": 5,
            "ocr_success": True,
            "ocr_text_length": 42,
            "is_extracted": False,
            "errors": [],
            "timing": {"total": 1.8, "image_processing": 1.3, "vdb_storage": 0.5},
            "processing_start_time": "2025-01-01T12:00:00",
            "retry_count": 0,
        }

        summary = self.report_generator._generate_human_readable_summary(result)

        # Check key content
        self.assertIn("test.jpg", summary)
        self.assertIn("67.89 KB", summary)
        self.assertIn("✅ SUCCESS", summary)
        self.assertIn("EXIF Extracted: ✅", summary)
        self.assertIn("AI Classifications: 5", summary)
        self.assertIn("OCR Success: ✅", summary)
        self.assertIn("OCR Text Length: 42 chars", summary)
        self.assertIn("Image Processing: 1.300s", summary)
        self.assertIn("Total Time: 1.800s", summary)

    def test_generate_human_readable_summary_with_errors(self):
        """Test human-readable summary generation with errors."""
        result = {
            "file_name": "bad.pdf",
            "file_size_kb": 50.0,
            "file_type": "document",
            "document_type": "pdf",
            "success": False,
            "errors": ["Failed to extract text", "Corrupted PDF structure"],
            "timing": {"total": 0.5},
            "processing_start_time": "2025-01-01T12:00:00",
            "retry_count": 3,
        }

        summary = self.report_generator._generate_human_readable_summary(result)

        # Check error content
        self.assertIn("❌ FAILED", summary)
        self.assertIn("Retry Attempts: 3", summary)
        self.assertIn("❌ ERRORS ENCOUNTERED", summary)
        self.assertIn("1. Failed to extract text", summary)
        self.assertIn("2. Corrupted PDF structure", summary)


if __name__ == "__main__":
    unittest.main()
