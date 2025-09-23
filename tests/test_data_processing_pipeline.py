# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.ragme.data_processing.pipeline import DocumentProcessingPipeline


class TestDocumentProcessingPipeline(unittest.TestCase):
    """Test cases for the DocumentProcessingPipeline class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_init_valid_directory(self, mock_report_gen, mock_processor):
        """Test pipeline initialization with valid directory."""
        pipeline = DocumentProcessingPipeline(
            self.temp_dir, batch_size=4, retry_limit=5, verbose=True
        )

        self.assertEqual(pipeline.batch_size, 4)
        self.assertEqual(pipeline.retry_limit, 5)
        self.assertTrue(pipeline.verbose)
        self.assertEqual(str(pipeline.input_directory), self.temp_dir)

        # Check that components were initialized
        mock_processor.assert_called_once_with(batch_size=4, retry_limit=5)
        mock_report_gen.assert_called_once_with(self.temp_dir)

    def test_init_invalid_directory(self):
        """Test pipeline initialization with invalid directory."""
        invalid_dir = "/nonexistent/directory"

        with self.assertRaises(ValueError) as context:
            DocumentProcessingPipeline(invalid_dir)

        self.assertIn("does not exist", str(context.exception))

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_discover_files_empty_directory(self, mock_report_gen, mock_processor):
        """Test file discovery in empty directory."""
        # Mock processor to support some file types
        mock_processor_instance = Mock()
        mock_processor_instance.is_supported_file.side_effect = (
            lambda path: path.endswith((".pdf", ".jpg"))
        )
        mock_processor.return_value = mock_processor_instance

        pipeline = DocumentProcessingPipeline(self.temp_dir)
        files_to_process, already_processed = pipeline.discover_files()

        self.assertEqual(len(files_to_process), 0)
        self.assertEqual(len(already_processed), 0)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_discover_files_with_files(self, mock_report_gen, mock_processor):
        """Test file discovery with mixed files."""
        # Mock processor
        mock_processor_instance = Mock()
        mock_processor_instance.is_supported_file.side_effect = (
            lambda path: path.endswith((".pdf", ".jpg"))
        )
        mock_processor.return_value = mock_processor_instance

        # Create test files
        test_files = ["document1.pdf", "image1.jpg", "unsupported.txt"]

        for filename in test_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write(f"content of {filename}")

        # Create .processed file for one
        processed_file = os.path.join(self.temp_dir, "document1.pdf.processed")
        with open(processed_file, "w") as f:
            f.write("processed")

        pipeline = DocumentProcessingPipeline(self.temp_dir)
        files_to_process, already_processed = pipeline.discover_files()

        # Should find image1.jpg to process
        self.assertEqual(len(files_to_process), 1)
        self.assertTrue(any("image1.jpg" in f for f in files_to_process))

        # Should find document1.pdf as already processed
        self.assertEqual(len(already_processed), 1)
        self.assertTrue(any("document1.pdf" in f for f in already_processed))

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_create_and_remove_lock_file(self, mock_report_gen, mock_processor):
        """Test lock file creation and removal."""
        mock_processor.return_value = Mock()

        pipeline = DocumentProcessingPipeline(self.temp_dir)

        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("test content")

        # Test lock creation
        success = pipeline._create_lock_file(test_file)
        self.assertTrue(success)

        lock_file = test_file + ".lock"
        self.assertTrue(os.path.exists(lock_file))
        self.assertIn(lock_file, pipeline.lock_files)

        # Test duplicate lock fails
        success2 = pipeline._create_lock_file(test_file)
        self.assertFalse(success2)

        # Test lock removal
        pipeline._remove_lock_file(test_file)
        self.assertFalse(os.path.exists(lock_file))
        self.assertNotIn(lock_file, pipeline.lock_files)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_cleanup_lock_files(self, mock_report_gen, mock_processor):
        """Test cleanup of all lock files."""
        mock_processor.return_value = Mock()

        pipeline = DocumentProcessingPipeline(self.temp_dir)

        # Create multiple test files and lock them
        test_files = []
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"test{i}.pdf")
            with open(test_file, "w") as f:
                f.write(f"test content {i}")
            test_files.append(test_file)
            pipeline._create_lock_file(test_file)

        # Verify locks were created
        self.assertEqual(len(pipeline.lock_files), 3)
        for test_file in test_files:
            lock_file = test_file + ".lock"
            self.assertTrue(os.path.exists(lock_file))

        # Test cleanup
        pipeline._cleanup_lock_files()

        # Verify all locks were removed
        self.assertEqual(len(pipeline.lock_files), 0)
        for test_file in test_files:
            lock_file = test_file + ".lock"
            self.assertFalse(os.path.exists(lock_file))

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_optimize_processing_order(self, mock_report_gen, mock_processor):
        """Test file processing order optimization."""
        # Mock processor
        mock_processor_instance = Mock()
        mock_processor_instance.get_file_type.side_effect = lambda path: (
            "document" if path.endswith((".pdf", ".docx")) else "image"
        )
        mock_processor.return_value = mock_processor_instance

        # Create test files with known sizes
        test_files = []
        file_info = [
            ("large_doc.pdf", 1000),
            ("small_img.jpg", 100),
            ("medium_doc.docx", 500),
            ("large_img.png", 800),
            ("small_doc.pdf", 200),
        ]

        for filename, size in file_info:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "w") as f:
                f.write("x" * size)
            test_files.append(filepath)

        pipeline = DocumentProcessingPipeline(self.temp_dir)
        optimized_order = pipeline.optimize_processing_order(test_files)

        # Should have all files
        self.assertEqual(len(optimized_order), len(test_files))

        # All original files should be present
        optimized_names = {Path(f).name for f in optimized_order}
        original_names = {filename for filename, _ in file_info}
        self.assertEqual(optimized_names, original_names)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_process_single_file_success(self, mock_report_gen, mock_processor):
        """Test processing single file successfully."""
        # Mock processor
        mock_processor_instance = Mock()
        mock_processor_instance.process_file_with_retry.return_value = {
            "file_name": "test.pdf",
            "success": True,
            "file_type": "document",
            "chunk_count": 3,
            "extracted_images": [],
            "timing": {"total": 1.5},
            "errors": [],
        }
        mock_processor.return_value = mock_processor_instance

        # Mock report generator
        mock_report_gen_instance = Mock()
        mock_report_gen.return_value = mock_report_gen_instance

        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("test content")

        pipeline = DocumentProcessingPipeline(self.temp_dir, verbose=True)
        result = pipeline._process_single_file(test_file)

        self.assertTrue(result["success"])
        self.assertEqual(result["file_name"], "test.pdf")

        # Verify processor and report generator were called
        mock_processor_instance.process_file_with_retry.assert_called_once_with(
            test_file, pipeline.retry_limit
        )
        mock_report_gen_instance.create_processed_file.assert_called_once_with(
            test_file, result
        )

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_process_single_file_locked(self, mock_report_gen, mock_processor):
        """Test processing file that's already locked."""
        mock_processor.return_value = Mock()

        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("test content")

        # Create lock file manually
        lock_file = test_file + ".lock"
        with open(lock_file, "w") as f:
            f.write("locked")

        pipeline = DocumentProcessingPipeline(self.temp_dir)
        result = pipeline._process_single_file(test_file)

        self.assertFalse(result["success"])
        self.assertTrue(result.get("skipped", False))
        self.assertIn("locked by another process", result["errors"][0])

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    @patch("src.ragme.data_processing.pipeline.ThreadPoolExecutor")
    def test_process_files_parallel(
        self, mock_thread_pool, mock_report_gen, mock_processor
    ):
        """Test parallel file processing."""
        # Mock thread pool executor
        mock_executor = Mock()
        mock_future1 = Mock()
        mock_future1.result.return_value = {"file_name": "file1.pdf", "success": True}
        mock_future2 = Mock()
        mock_future2.result.return_value = {"file_name": "file2.jpg", "success": True}

        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        mock_executor.__enter__ = Mock(return_value=mock_executor)
        mock_executor.__exit__ = Mock(return_value=None)

        # Mock as_completed to return futures in order
        from unittest.mock import patch

        with patch(
            "src.ragme.data_processing.pipeline.as_completed"
        ) as mock_as_completed:
            mock_as_completed.return_value = [mock_future1, mock_future2]

            mock_thread_pool.return_value = mock_executor
            mock_processor.return_value = Mock()

            test_files = ["file1.pdf", "file2.jpg"]

            pipeline = DocumentProcessingPipeline(self.temp_dir, batch_size=2)
            results = pipeline.process_files_parallel(test_files)

            # Should have processed both files
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["file_name"], "file1.pdf")
            self.assertEqual(results[1]["file_name"], "file2.jpg")

            # Thread pool should have been configured with correct batch size
            mock_thread_pool.assert_called_once_with(max_workers=2)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_run_no_files(self, mock_report_gen, mock_processor):
        """Test pipeline run with no files to process."""
        mock_processor_instance = Mock()
        mock_processor_instance.is_supported_file.return_value = False
        mock_processor.return_value = mock_processor_instance

        pipeline = DocumentProcessingPipeline(self.temp_dir)
        stats = pipeline.run()

        self.assertEqual(stats["processed_files"], 0)
        self.assertEqual(stats["total_files"], 0)
        self.assertEqual(len(stats["results"]), 0)
        self.assertGreaterEqual(stats["processing_time"], 0)

    @patch("src.ragme.data_processing.pipeline.DocumentProcessor")
    @patch("src.ragme.data_processing.pipeline.ReportGenerator")
    def test_context_manager(self, mock_report_gen, mock_processor):
        """Test pipeline as context manager."""
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance

        with DocumentProcessingPipeline(self.temp_dir) as pipeline:
            self.assertIsInstance(pipeline, DocumentProcessingPipeline)

        # Cleanup should have been called
        mock_processor_instance.cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
