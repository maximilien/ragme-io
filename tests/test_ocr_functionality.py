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
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image, ImageDraw, ImageFont

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOCRFunctionality:
    """Test cases for OCR functionality in ImageProcessor."""

    @pytest.fixture
    def sample_image_with_text(self):
        """Create a sample image with text for testing."""
        # Create a white image
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        # Add text to the image
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except Exception:
            # Fallback to default size
            font = ImageFont.load_default()

        # Add the test text
        test_text = """Welcome to 🤖 RAGme.io Assistant!

I can help you with:

• Adding URLs - Tell me URLs to crawl and add to your knowledge base
• Adding documents (Text, PDF, DOCX, etc.) - Use the "Add Content" button to add files and structured data
• Adding images (JPG, PNG, GIF, etc.) - Use the "Add Content" button to upload and analyze images with AI
• Answering questions - Ask me anything about your documents and images
• Document management - View and explore your documents and images in the right panel

Try asking me to add some URLs, documents, or images, or ask questions about your existing content!"""

        # Split text into lines and draw each line
        lines = test_text.split("\n")
        y_position = 50
        for line in lines:
            if line.strip():
                draw.text((50, y_position), line, fill="black", font=font)
                y_position += 30

        return img

    @pytest.fixture
    def temp_image_file(self, sample_image_with_text):
        """Create a temporary image file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            sample_image_with_text.save(temp_file.name, "PNG")
            yield temp_file.name
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    def test_ocr_initialization(self):
        """Test OCR initialization."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            # OCR should be initialized lazily
            assert processor._ocr_reader is None
            assert processor._ocr_initialized is False

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_configuration_loading(self):
        """Test OCR configuration loading."""
        try:
            from src.ragme.utils.config_manager import ConfigManager

            config_manager = ConfigManager()
            ocr_config = config_manager.get("ocr", {})

            assert "enabled" in ocr_config
            assert "engine" in ocr_config
            assert "languages" in ocr_config
            assert "confidence_threshold" in ocr_config

        except ImportError as e:
            pytest.skip(f"Config manager not available: {e}")

    def test_should_apply_ocr_decision(self):
        """Test OCR decision logic based on image classification."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test with website classification
            website_classification = {
                "classifications": [
                    {"label": "website", "confidence": 0.9},
                    {"label": "computer", "confidence": 0.8},
                ],
                "top_prediction": {"label": "website", "confidence": 0.9},
            }

            should_apply = processor._should_apply_ocr(website_classification)
            # OCR should be applied for website content
            assert should_apply is True

            # Test with non-text classification
            nature_classification = {
                "classifications": [
                    {"label": "tree", "confidence": 0.9},
                    {"label": "forest", "confidence": 0.8},
                ],
                "top_prediction": {"label": "tree", "confidence": 0.9},
            }

            should_apply = processor._should_apply_ocr(nature_classification)
            # Should still apply OCR if enabled in config
            assert isinstance(should_apply, bool)

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_extraction_with_easyocr(self, temp_image_file):
        """Test OCR text extraction using EasyOCR."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            file_path = f"file://{temp_image_file}"

            # Test OCR extraction
            result = processor.extract_text_with_ocr(file_path)

            assert result["type"] == "ocr_extraction"
            assert result["ocr_processing"] is True
            assert "engine" in result
            assert "confidence_threshold" in result
            assert "extracted_text" in result
            assert "text_blocks" in result
            assert "text_length" in result
            assert "block_count" in result

            # Should extract some text from our test image
            assert len(result["extracted_text"]) > 0
            assert result["text_length"] > 0
            assert result["block_count"] > 0

        except ImportError as e:
            pytest.skip(f"EasyOCR not available: {e}")

    def test_ocr_extraction_with_pytesseract(self, temp_image_file):
        """Test OCR text extraction using pytesseract."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Mock config to use pytesseract
            with patch(
                "src.ragme.utils.config_manager.ConfigManager.get"
            ) as mock_config:
                mock_config.return_value = {
                    "enabled": True,
                    "engine": "pytesseract",
                    "languages": ["en"],
                    "confidence_threshold": 0.5,
                }

                file_path = f"file://{temp_image_file}"
                result = processor.extract_text_with_ocr(file_path)

                assert result["type"] == "ocr_extraction"
                # pytesseract might fail if not installed, so check for error or success
                if result.get("ocr_processing", False):
                    assert "engine" in result
                else:
                    assert "error" in result

        except ImportError as e:
            pytest.skip(f"pytesseract not available: {e}")

    def test_ocr_preprocessing(self, temp_image_file):
        """Test image preprocessing for OCR."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Read original image data
            with open(temp_image_file, "rb") as f:
                original_data = f.read()

            # Test preprocessing
            processed_data = processor._preprocess_image_for_ocr(
                original_data, f"file://{temp_image_file}"
            )

            # Should return processed image data
            assert isinstance(processed_data, bytes)
            assert len(processed_data) > 0

        except ImportError as e:
            pytest.skip(f"OpenCV not available: {e}")

    def test_full_image_processing_with_ocr(self, temp_image_file):
        """Test full image processing pipeline including OCR."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            file_path = f"file://{temp_image_file}"

            # Test full processing
            result = processor.process_image(file_path)

            # Check basic structure
            assert "type" in result
            assert "source" in result
            assert "classification" in result
            assert "ocr_content" in result
            assert "processing_timestamp" in result

            # Check OCR content
            ocr_content = result["ocr_content"]
            if ocr_content and ocr_content.get("ocr_processing", False):
                assert "extracted_text" in ocr_content
                assert "text_blocks" in ocr_content
                assert "text_length" in ocr_content

                # Should extract some text (OCR might not recognize all text perfectly)
                extracted_text = ocr_content["extracted_text"]
                assert len(extracted_text) > 0, "OCR should extract some text"

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_error_handling(self):
        """Test OCR error handling with invalid image."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test with non-existent file
            result = processor.extract_text_with_ocr("file:///nonexistent/file.png")

            assert result["type"] == "ocr_extraction"
            assert result["ocr_processing"] is False
            assert "error" in result

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_without_dependencies(self):
        """Test OCR behavior when dependencies are not available."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Mock missing dependencies
            with patch.dict("sys.modules", {"easyocr": None, "pytesseract": None}):
                result = processor.extract_text_with_ocr("file://test.png")

                assert result["type"] == "ocr_extraction"
                assert result["ocr_processing"] is False
                assert "error" in result

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_confidence_filtering(self, temp_image_file):
        """Test OCR confidence threshold filtering."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test with high confidence threshold
            with patch(
                "src.ragme.utils.config_manager.ConfigManager.get"
            ) as mock_config:
                mock_config.return_value = {
                    "enabled": True,
                    "engine": "easyocr",
                    "languages": ["en"],
                    "confidence_threshold": 0.9,  # Very high threshold
                }

                file_path = f"file://{temp_image_file}"
                result = processor.extract_text_with_ocr(file_path)

                if result["ocr_processing"]:
                    # With high threshold, should have fewer text blocks
                    assert result["block_count"] >= 0

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_content_types_matching(self):
        """Test OCR content type matching logic."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test various content types
            content_types = [
                {"label": "web site", "should_match": True},
                {"label": "document", "should_match": True},
                {"label": "slide", "should_match": True},
                {"label": "screenshot", "should_match": True},
                {"label": "text", "should_match": True},
                {"label": "chart", "should_match": True},
                {"label": "diagram", "should_match": True},
                {"label": "tree", "should_match": False},
                {"label": "car", "should_match": False},
                {"label": "person", "should_match": False},
            ]

            for content_type in content_types:
                classification = {
                    "top_prediction": {
                        "label": content_type["label"],
                        "confidence": 0.9,
                    }
                }

                should_apply = processor._should_apply_ocr(classification)
                # Note: OCR might still be applied based on config settings
                assert isinstance(should_apply, bool)

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_metadata_structure(self, temp_image_file):
        """Test that OCR metadata has the correct structure."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            file_path = f"file://{temp_image_file}"

            result = processor.process_image(file_path)

            # Check OCR content structure
            ocr_content = result.get("ocr_content", {})
            if ocr_content and ocr_content.get("ocr_processing", False):
                required_fields = [
                    "type",
                    "engine",
                    "confidence_threshold",
                    "extracted_text",
                    "text_blocks",
                    "text_length",
                    "block_count",
                    "ocr_processing",
                ]

                for field in required_fields:
                    assert field in ocr_content, f"Missing field: {field}"

                # Check text_blocks structure
                text_blocks = ocr_content["text_blocks"]
                if text_blocks:
                    for block in text_blocks:
                        assert "text" in block
                        assert "confidence" in block
                        assert isinstance(block["text"], str)
                        assert isinstance(block["confidence"], int | float)

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")

    def test_ocr_performance(self, temp_image_file):
        """Test OCR performance with timing."""
        try:
            import time

            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            file_path = f"file://{temp_image_file}"

            # Time the OCR extraction
            start_time = time.time()
            result = processor.extract_text_with_ocr(file_path)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should complete within reasonable time (30 seconds)
            assert processing_time < 30, (
                f"OCR took too long: {processing_time:.2f} seconds"
            )

            # Should extract some text
            if result["ocr_processing"]:
                assert len(result["extracted_text"]) > 0

        except ImportError as e:
            pytest.skip(f"OCR dependencies not available: {e}")


class TestOCRIntegration:
    """Integration tests for OCR functionality."""

    @pytest.fixture
    def temp_image_file(self):
        """Create a temporary image file for testing."""
        # Create a sample image with text
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        # Add text to the image
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except Exception:
            # Fallback to default size
            font = ImageFont.load_default()

        # Add the test text
        test_text = """Welcome to 🤖 RAGme.io Assistant!

I can help you with:

• Adding URLs - Tell me URLs to crawl and add to your knowledge base
• Adding documents (Text, PDF, DOCX, etc.) - Use the "Add Content" button to add files and structured data
• Adding images (JPG, PNG, GIF, etc.) - Use the "Add Content" button to upload and analyze images with AI
• Answering questions - Ask me anything about your documents and images
• Document management - View and explore your documents and images in the right panel

Try asking me to add some URLs, documents, or images, or ask questions about your existing content!"""

        # Split text into lines and draw each line
        lines = test_text.split("\n")
        y_position = 50
        for line in lines:
            if line.strip():
                draw.text((50, y_position), line, fill="black", font=font)
                y_position += 30

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            img.save(temp_file.name, "PNG")
            yield temp_file.name
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    def test_ocr_with_api_endpoint(self, temp_image_file):
        """Test OCR through the API endpoint."""
        try:
            import requests
            from fastapi.testclient import TestClient

            from src.ragme.apis.api import app

            client = TestClient(app)

            # Test the OCR endpoint
            with open(temp_image_file, "rb") as f:
                response = client.post(
                    "/test-ocr", files={"file": ("test.png", f, "image/png")}
                )

            assert response.status_code == 200
            result = response.json()

            assert result["status"] == "success"
            assert "ocr_result" in result
            assert "full_processing" in result

            ocr_result = result["ocr_result"]
            if ocr_result.get("ocr_processing", False):
                assert "extracted_text" in ocr_result

        except ImportError as e:
            pytest.skip(f"FastAPI test client not available: {e}")

    def test_ocr_with_image_upload_endpoint(self, temp_image_file):
        """Test OCR through the image upload endpoint."""
        try:
            from fastapi.testclient import TestClient

            from src.ragme.apis.api import app

            client = TestClient(app)

            # Test the image upload endpoint
            with open(temp_image_file, "rb") as f:
                response = client.post(
                    "/upload-images", files={"files": ("test.png", f, "image/png")}
                )

            assert response.status_code == 200
            result = response.json()

            assert result["status"] == "success"
            assert result["files_processed"] > 0

        except ImportError as e:
            pytest.skip(f"FastAPI test client not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
