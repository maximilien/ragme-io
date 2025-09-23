# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ragme.data_processing.pipeline import DocumentProcessingPipeline


class TestDataProcessingIntegration(unittest.TestCase):
    """Integration tests for the complete data processing pipeline."""

    def setUp(self):
        """Set up test fixtures with temporary directory and test collections."""
        self.temp_dir = tempfile.mkdtemp()

        # Copy fixture files to temp directory for testing
        self._copy_test_fixtures()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _copy_test_fixtures(self):
        """Copy test fixtures to temporary directory."""
        fixtures_dir = Path("tests/fixtures")

        # Copy PDF fixtures if they exist
        pdf_dir = fixtures_dir / "pdfs"
        if pdf_dir.exists():
            for pdf_file in pdf_dir.glob("*.pdf"):
                shutil.copy2(pdf_file, self.temp_dir)

        # Copy image fixtures if they exist
        image_dir = fixtures_dir / "images"
        if image_dir.exists():
            for img_file in image_dir.glob("*"):
                if img_file.is_file():
                    shutil.copy2(img_file, self.temp_dir)

        # Create a test DOCX file (simple text file with .docx extension for testing)
        test_docx_path = os.path.join(self.temp_dir, "test_document.docx")
        with open(test_docx_path, "w") as f:
            f.write("This is a test document for DOCX processing.")

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_empty_directory(self, mock_config):
        """Test pipeline with empty directory."""
        # Configure mock to use test collections
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        empty_dir = tempfile.mkdtemp()
        try:
            with DocumentProcessingPipeline(
                empty_dir, batch_size=1, verbose=False
            ) as pipeline:
                stats = pipeline.run()

            self.assertEqual(stats["processed_files"], 0)
            self.assertEqual(stats["total_files"], 0)
            self.assertEqual(len(stats["results"]), 0)

        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_discover_files(self, mock_config):
        """Test file discovery functionality."""
        # Configure mock
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Create test files
        test_files = [
            "document1.pdf",
            "document2.docx",
            "image1.jpg",
            "image2.png",
            "unsupported.txt",  # Should be ignored
            "README.md",  # Should be ignored
        ]

        for filename in test_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write(f"test content for {filename}")

        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=1, verbose=False
        ) as pipeline:
            files_to_process, already_processed = pipeline.discover_files()

        # Should find 4 supported files (2 docs + 2 images)
        supported_files = [
            f
            for f in files_to_process
            if Path(f).name
            in ["document1.pdf", "document2.docx", "image1.jpg", "image2.png"]
        ]
        self.assertEqual(len(supported_files), 4)
        self.assertEqual(len(already_processed), 0)

        # Unsupported files should not be in the list
        unsupported_found = any(
            "unsupported.txt" in f or "README.md" in f for f in files_to_process
        )
        self.assertFalse(unsupported_found)

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_skip_processed_files(self, mock_config):
        """Test that already processed files are skipped."""
        # Configure mock
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Create test files
        test_pdf = os.path.join(self.temp_dir, "test.pdf")
        test_jpg = os.path.join(self.temp_dir, "test.jpg")

        with open(test_pdf, "w") as f:
            f.write("test pdf content")
        with open(test_jpg, "w") as f:
            f.write("test jpg content")

        # Create .processed file for PDF
        with open(test_pdf + ".processed", "w") as f:
            f.write("already processed")

        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=1, verbose=False
        ) as pipeline:
            files_to_process, already_processed = pipeline.discover_files()

        # Should find only the JPG to process
        self.assertEqual(len(files_to_process), 1)
        self.assertIn("test.jpg", files_to_process[0])

        # Should find the PDF as already processed
        self.assertEqual(len(already_processed), 1)
        self.assertIn("test.pdf", already_processed[0])

    @patch("src.ragme.data_processing.processor.config")
    @patch("src.ragme.data_processing.processor.image_processor")
    def test_pipeline_process_single_image(self, mock_image_processor, mock_config):
        """Test processing a single image file."""
        # Configure mocks
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        mock_image_processor.process_image.return_value = {
            "exif": {"camera": "Test Camera"},
            "classification": {
                "classifications": [{"label": "cat", "confidence": 0.9}],
                "top_prediction": {"label": "cat", "confidence": 0.9},
            },
            "ocr_content": {"extracted_text": "Test text", "ocr_processing": True},
        }

        # Create single test image
        test_image = os.path.join(self.temp_dir, "single_test.jpg")
        with open(test_image, "wb") as f:
            f.write(b"fake image content")

        # Remove any existing fixture files to test only our single image
        for file_path in Path(self.temp_dir).iterdir():
            if file_path.name != "single_test.jpg":
                file_path.unlink()

        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=1, verbose=True
        ) as pipeline:
            stats = pipeline.run()

        # Verify processing results
        self.assertEqual(stats["processed_files"], 1)
        self.assertEqual(stats["successful_files"], 1)
        self.assertEqual(stats["failed_files"], 0)
        self.assertEqual(len(stats["results"]), 1)

        result = stats["results"][0]
        self.assertEqual(result["file_type"], "image")
        self.assertTrue(result["success"])

        # Verify .processed file was created
        processed_file = test_image + ".processed"
        self.assertTrue(os.path.exists(processed_file))

        # Verify CSV report was created
        csv_file = os.path.join(self.temp_dir, "processing_results.csv")
        self.assertTrue(os.path.exists(csv_file))

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_file_locking(self, mock_config):
        """Test file locking mechanism to prevent concurrent processing."""
        # Configure mock
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Create test image
        test_image = os.path.join(self.temp_dir, "locked_test.jpg")
        with open(test_image, "wb") as f:
            f.write(b"fake image content")

        # Manually create a lock file
        lock_file = test_image + ".lock"
        with open(lock_file, "w") as f:
            f.write("manually locked")

        try:
            with DocumentProcessingPipeline(
                self.temp_dir, batch_size=1, verbose=False
            ) as pipeline:
                result = pipeline._process_single_file(test_image)

            # Should be skipped due to lock
            self.assertFalse(result["success"])
            self.assertTrue(result.get("skipped", False))
            self.assertIn("locked by another process", result["errors"][0])

        finally:
            # Clean up lock file
            if os.path.exists(lock_file):
                os.unlink(lock_file)

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_optimize_processing_order(self, mock_config):
        """Test file processing order optimization."""
        # Configure mock
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Create test files of different sizes
        files_with_sizes = [
            ("small_doc.pdf", 100),
            ("large_doc.pdf", 1000),
            ("small_img.jpg", 50),
            ("large_img.jpg", 500),
            ("medium_doc.docx", 300),
        ]

        test_files = []
        for filename, size in files_with_sizes:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("x" * size)  # Create file of specified size
            test_files.append(filepath)

        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=2, verbose=False
        ) as pipeline:
            optimized_order = pipeline.optimize_processing_order(test_files)

        # Should have all files
        self.assertEqual(len(optimized_order), len(test_files))

        # All original files should be present
        optimized_names = [Path(f).name for f in optimized_order]
        original_names = [filename for filename, _ in files_with_sizes]
        for name in original_names:
            self.assertIn(name, optimized_names)

    def test_pipeline_signal_handling(self):
        """Test signal handling for cleanup (basic test without actual signals)."""
        # This test verifies that cleanup methods exist and can be called
        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=1, verbose=False
        ) as pipeline:
            # Test cleanup methods exist
            self.assertTrue(hasattr(pipeline, "_cleanup_lock_files"))
            self.assertTrue(hasattr(pipeline, "_signal_handler"))

            # Test that cleanup can be called without errors
            pipeline._cleanup_lock_files()

            # Test processor cleanup
            pipeline.processor.cleanup()

    @patch("src.ragme.data_processing.processor.config")
    def test_pipeline_context_manager(self, mock_config):
        """Test pipeline context manager functionality."""
        # Configure mock
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Test context manager entry/exit
        with DocumentProcessingPipeline(
            self.temp_dir, batch_size=1, verbose=False
        ) as pipeline:
            self.assertIsNotNone(pipeline)
            self.assertIsInstance(pipeline, DocumentProcessingPipeline)

        # Pipeline should have cleaned up after exiting context
        # This is mainly testing that no exceptions are raised

    def test_pipeline_nonexistent_directory(self):
        """Test pipeline with nonexistent directory."""
        nonexistent_dir = "/this/directory/does/not/exist"

        with self.assertRaises(ValueError) as context:
            DocumentProcessingPipeline(nonexistent_dir)

        self.assertIn("does not exist", str(context.exception))


class TestDataProcessingEndToEnd(unittest.TestCase):
    """End-to-end tests using actual fixture files if available."""

    def setUp(self):
        """Set up for end-to-end testing."""
        self.temp_dir = tempfile.mkdtemp()

        # Only copy fixture files that actually exist
        fixtures_dir = Path("tests/fixtures")

        if fixtures_dir.exists():
            # Copy available PDF fixtures
            pdf_dir = fixtures_dir / "pdfs"
            if pdf_dir.exists():
                for pdf_file in pdf_dir.glob("*.pdf"):
                    if pdf_file.stat().st_size < 1024 * 1024:  # Skip large files (>1MB)
                        shutil.copy2(pdf_file, self.temp_dir)

            # Copy available image fixtures
            image_dir = fixtures_dir / "images"
            if image_dir.exists():
                for img_file in image_dir.glob("*"):
                    if (
                        img_file.is_file() and img_file.stat().st_size < 512 * 1024
                    ):  # Skip large files (>512KB)
                        shutil.copy2(img_file, self.temp_dir)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unittest.skipIf(not Path("tests/fixtures").exists(), "Fixture files not available")
    @patch("src.ragme.data_processing.processor.config")
    def test_end_to_end_fixture_processing(self, mock_config):
        """Test end-to-end processing with actual fixture files."""
        # Configure mock to use test collections
        mock_config.get_text_collection_name.return_value = "test_integration"
        mock_config.get_image_collection_name.return_value = "test_integration_images"
        mock_config.get_database_config.return_value = {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "chunk_overlap_ratio": 0.2,
        }

        # Check if we have any files to process
        files_in_temp = list(Path(self.temp_dir).iterdir())
        if not files_in_temp:
            self.skipTest("No fixture files available for testing")

        print(f"Testing with {len(files_in_temp)} fixture files")

        try:
            with DocumentProcessingPipeline(
                self.temp_dir, batch_size=1, retry_limit=1, verbose=True
            ) as pipeline:
                stats = pipeline.run()

            # Basic validation - should process at least one file
            self.assertGreater(stats["processed_files"], 0)
            self.assertGreaterEqual(stats["successful_files"], 0)
            self.assertEqual(len(stats["results"]), stats["processed_files"])

            # Check that reports were generated
            csv_file = os.path.join(self.temp_dir, "processing_results.csv")
            self.assertTrue(os.path.exists(csv_file), "CSV report should be generated")

            # Check that .processed files were created for successful files
            for result in stats["results"]:
                if result.get("success", False):
                    processed_file = result["file_path"] + ".processed"
                    self.assertTrue(
                        os.path.exists(processed_file),
                        f".processed file should be created for {result['file_name']}",
                    )

            print(
                f"Processing completed: {stats['successful_files']}/{stats['processed_files']} files successful"
            )

        except Exception as e:
            self.fail(f"End-to-end test failed with exception: {e}")


if __name__ == "__main__":
    unittest.main()
