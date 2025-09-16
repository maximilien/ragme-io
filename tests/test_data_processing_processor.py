# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.ragme.data_processing.processor import DocumentProcessor


class TestDocumentProcessor(unittest.TestCase):
    """Test cases for the DocumentProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = DocumentProcessor(batch_size=2, retry_limit=2)
    
    def tearDown(self):
        """Clean up after tests."""
        self.processor.cleanup()
    
    def test_init(self):
        """Test processor initialization."""
        self.assertEqual(self.processor.batch_size, 2)
        self.assertEqual(self.processor.retry_limit, 2)
        self.assertIsNotNone(self.processor.text_collection_name)
        self.assertIsNotNone(self.processor.image_collection_name)
    
    def test_is_supported_file(self):
        """Test file type detection."""
        # Supported document types
        self.assertTrue(self.processor.is_supported_file("test.pdf"))
        self.assertTrue(self.processor.is_supported_file("test.docx"))
        self.assertTrue(self.processor.is_supported_file("test.PDF"))  # Case insensitive
        
        # Supported image types
        self.assertTrue(self.processor.is_supported_file("test.jpg"))
        self.assertTrue(self.processor.is_supported_file("test.png"))
        self.assertTrue(self.processor.is_supported_file("test.heic"))
        
        # Unsupported types
        self.assertFalse(self.processor.is_supported_file("test.txt"))
        self.assertFalse(self.processor.is_supported_file("test.doc"))  # Old Word format
        self.assertFalse(self.processor.is_supported_file("test.pptx"))
    
    def test_get_file_type(self):
        """Test file type categorization."""
        self.assertEqual(self.processor.get_file_type("test.pdf"), "document")
        self.assertEqual(self.processor.get_file_type("test.docx"), "document")
        self.assertEqual(self.processor.get_file_type("test.jpg"), "image")
        self.assertEqual(self.processor.get_file_type("test.png"), "image")
        self.assertIsNone(self.processor.get_file_type("test.txt"))
    
    def test_chunk_text_simple(self):
        """Test text chunking with simple text."""
        text = "Short text that fits in one chunk."
        chunks = self.processor.chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)
    
    def test_chunk_text_long(self):
        """Test text chunking with long text."""
        # Create text longer than chunk size
        text = "This is a sentence. " * 100  # Should be > 1000 characters
        chunks = self.processor.chunk_text(text)
        
        self.assertGreater(len(chunks), 1)
        
        # Check that chunks don't exceed the size limit (plus some tolerance for sentence boundaries)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), self.processor.chunk_size * 1.2)  # 20% tolerance
    
    def test_chunk_text_sentence_boundaries(self):
        """Test that chunking respects sentence boundaries."""
        # Create text with clear sentence boundaries
        sentence = "This is a complete sentence with proper punctuation. "
        text = sentence * 50  # Create long text with sentence boundaries
        
        chunks = self.processor.chunk_text(text)
        
        if len(chunks) > 1:
            # Most chunks should end with sentence-ending punctuation
            sentence_endings = ['.', '!', '?']
            chunks_ending_properly = sum(
                1 for chunk in chunks[:-1]  # Exclude last chunk
                if chunk.strip()[-1] in sentence_endings
            )
            
            # At least 50% of chunks should end properly (heuristic)
            self.assertGreater(chunks_ending_properly / max(len(chunks) - 1, 1), 0.3)
    
    @patch('src.ragme.data_processing.processor.fitz')  # Mock PyMuPDF
    def test_process_pdf_with_fallback_success(self, mock_fitz):
        """Test successful PDF processing with PyMuPDF."""
        # Mock PyMuPDF document
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=2)
        mock_doc.metadata = {"title": "Test PDF", "author": "Test Author"}
        
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Page 1 content"
        mock_page1.get_images.return_value = []
        
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Page 2 content"
        mock_page2.get_images.return_value = []
        
        mock_doc.__iter__ = Mock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.__getitem__ = Mock(side_effect=[mock_page1, mock_page2])
        mock_doc.close = Mock()
        
        mock_fitz.open.return_value = mock_doc
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(b'fake pdf content')
            temp_pdf_path = temp_pdf.name
        
        try:
            text, page_count, metadata, extracted_images = self.processor.process_pdf_with_fallback(temp_pdf_path)
            
            self.assertEqual(text, "Page 1 content\nPage 2 content\n")
            self.assertEqual(page_count, 2)
            self.assertEqual(metadata["title"], "Test PDF")
            self.assertEqual(len(extracted_images), 0)
            
        finally:
            os.unlink(temp_pdf_path)
    
    @patch('src.ragme.data_processing.processor.Document')
    def test_process_docx_file_success(self, mock_document_class):
        """Test successful DOCX processing."""
        # Mock docx Document
        mock_doc = Mock()
        
        # Mock paragraphs
        mock_para1 = Mock()
        mock_para1.text = "First paragraph"
        mock_para2 = Mock()
        mock_para2.text = "Second paragraph"
        mock_doc.paragraphs = [mock_para1, mock_para2]
        
        # Mock tables
        mock_doc.tables = []
        
        # Mock core properties
        mock_core_props = Mock()
        mock_core_props.author = "Test Author"
        mock_core_props.title = "Test Document"
        mock_core_props.subject = "Test Subject"
        mock_core_props.created = None
        mock_core_props.modified = None
        mock_doc.core_properties = mock_core_props
        
        mock_document_class.return_value = mock_doc
        
        # Create temporary DOCX file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
            temp_docx.write(b'fake docx content')
            temp_docx_path = temp_docx.name
        
        try:
            text, metadata = self.processor.process_docx_file(temp_docx_path)
            
            self.assertEqual(text, "First paragraph\nSecond paragraph")
            self.assertEqual(metadata["author"], "Test Author")
            self.assertEqual(metadata["title"], "Test Document")
            self.assertEqual(metadata["tables_count"], 0)
            self.assertEqual(metadata["paragraph_count"], 2)
            
        finally:
            os.unlink(temp_docx_path)
    
    @patch('src.ragme.data_processing.processor.image_processor')
    def test_process_image_success(self, mock_image_processor):
        """Test successful image processing."""
        # Mock image processor response
        mock_processed_image = {
            "exif": {"camera": "Test Camera", "date": "2023:01:01 12:00:00"},
            "classification": {
                "classifications": [{"label": "cat", "confidence": 0.9}],
                "top_prediction": {"label": "cat", "confidence": 0.9}
            },
            "ocr_content": {
                "extracted_text": "Sample text",
                "ocr_processing": True
            }
        }
        mock_image_processor.process_image.return_value = mock_processed_image
        
        # Create temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
            temp_img.write(b'fake image content')
            temp_img_path = temp_img.name
        
        try:
            result = self.processor.process_image(temp_img_path)
            
            self.assertTrue(result["success"])
            self.assertEqual(result["file_type"], "image")
            self.assertTrue(result["exif_extracted"])
            self.assertEqual(result["ai_classification_features"], 1)
            self.assertTrue(result["ocr_success"])
            self.assertEqual(result["ocr_text_length"], 11)  # "Sample text"
            
        finally:
            os.unlink(temp_img_path)
    
    def test_process_file_with_retry_unsupported(self):
        """Test processing unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b'unsupported content')
            temp_file_path = temp_file.name
        
        try:
            result = self.processor.process_file_with_retry(temp_file_path)
            
            self.assertFalse(result["success"])
            self.assertEqual(result["file_type"], "unsupported")
            self.assertIn("Unsupported file type", result["errors"][0])
            
        finally:
            os.unlink(temp_file_path)


class TestDocumentProcessorIntegration(unittest.TestCase):
    """Integration tests for DocumentProcessor with actual VDB."""

    def setUp(self):
        """Set up test fixtures with test collections."""
        # Use test collection names
        with patch('src.ragme.data_processing.processor.config') as mock_config:
            mock_config.get_text_collection_name.return_value = "test_integration"
            mock_config.get_image_collection_name.return_value = "test_integration_images"
            
            self.processor = DocumentProcessor(batch_size=1, retry_limit=1)
    
    def tearDown(self):
        """Clean up after tests."""
        self.processor.cleanup()
    
    def test_process_fixture_pdf(self):
        """Test processing actual PDF fixture."""
        # Use fixture from tests directory
        fixture_path = "tests/fixtures/pdfs/ragme-io.pdf"
        if not os.path.exists(fixture_path):
            self.skipTest("PDF fixture not available")
        
        result = self.processor.process_file_with_retry(fixture_path)
        
        # Basic validation
        self.assertIsNotNone(result)
        self.assertEqual(result["file_type"], "document")
        self.assertEqual(result["document_type"], "pdf")
        self.assertGreater(result["file_size_kb"], 0)
        
        # If processing was successful, check results
        if result.get("success", False):
            self.assertGreater(result.get("chunk_count", 0), 0)
            self.assertIn("timing", result)
            self.assertGreater(result["timing"]["total"], 0)
    
    def test_process_fixture_image(self):
        """Test processing actual image fixture."""
        # Use fixture from tests directory
        fixture_path = "tests/fixtures/images/test_image.png"
        if not os.path.exists(fixture_path):
            self.skipTest("Image fixture not available")
        
        result = self.processor.process_file_with_retry(fixture_path)
        
        # Basic validation
        self.assertIsNotNone(result)
        self.assertEqual(result["file_type"], "image")
        self.assertGreater(result["file_size_kb"], 0)
        
        # If processing was successful, check results
        if result.get("success", False):
            self.assertIn("timing", result)
            self.assertGreater(result["timing"]["total"], 0)
            self.assertIn("exif_extracted", result)
            self.assertIn("ai_classification_features", result)
            self.assertIn("ocr_success", result)


if __name__ == '__main__':
    unittest.main()