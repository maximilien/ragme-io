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
from unittest.mock import Mock, patch

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImageProcessor:
    """Test cases for the ImageProcessor class."""

    def test_image_processor_import(self):
        """Test that ImageProcessor can be imported without errors."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            assert ImageProcessor is not None
        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    def test_image_processor_initialization(self):
        """Test ImageProcessor initialization."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            assert processor is not None
        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    def test_image_processor_timestamp(self):
        """Test the private timestamp method."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()
            timestamp = processor._get_timestamp()
            assert isinstance(timestamp, str)
            assert len(timestamp) > 0
        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    @patch("requests.get")
    def test_get_image_metadata_error_handling(self, mock_requests):
        """Test error handling in get_image_metadata."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            # Mock a failed request
            mock_requests.side_effect = Exception("Network error")

            processor = ImageProcessor()
            result = processor.get_image_metadata("http://example.com/test.jpg")

            # Should return error info instead of raising exception
            assert "error" in result
            assert result["type"] == "image"

        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    def test_heic_support_import(self):
        """Test that HEIC support is properly imported."""
        try:
            from src.ragme.utils.image_processor import HEIC_SUPPORT

            # Should be a boolean indicating whether HEIC support is available
            assert isinstance(HEIC_SUPPORT, bool)
        except ImportError as e:
            pytest.skip(f"HEIC support test skipped due to import error: {e}")

    def test_heic_image_loader_method(self):
        """Test the HEIC-aware image loader method."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test that the method exists
            assert hasattr(processor, "_load_image_with_heic_support")
            assert callable(processor._load_image_with_heic_support)

        except ImportError as e:
            pytest.skip(f"HEIC support test skipped due to import error: {e}")

    def test_classify_image_without_pytorch(self):
        """Test image classification when PyTorch is not available."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # This should handle the ImportError gracefully
            result = processor.classify_image_with_pytorch(
                "http://example.com/test.jpg"
            )

            # Should return error info for missing PyTorch
            assert "error" in result or "pytorch_processing" in result

        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    def test_ocr_functionality_integration(self):
        """Test OCR functionality integration with image processing."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Test that OCR methods exist
            assert hasattr(processor, "extract_text_with_ocr")
            assert hasattr(processor, "_should_apply_ocr")
            assert hasattr(processor, "_preprocess_image_for_ocr")
            assert hasattr(processor, "_initialize_ocr")

            # Test OCR initialization
            assert processor._ocr_initialized is False

        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )

    def test_process_image_with_ocr_field(self):
        """Test that process_image includes OCR content field."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # Mock the classification to trigger OCR
            with patch.object(
                processor, "classify_image_with_pytorch"
            ) as mock_classify:
                mock_classify.return_value = {
                    "classifications": [{"label": "web site", "confidence": 0.9}],
                    "top_prediction": {"label": "web site", "confidence": 0.9},
                }

                # Mock OCR extraction
                with patch.object(processor, "extract_text_with_ocr") as mock_ocr:
                    mock_ocr.return_value = {
                        "type": "ocr_extraction",
                        "extracted_text": "Test text",
                        "ocr_processing": True,
                    }

                    result = processor.process_image("http://example.com/test.jpg")

                    # Should include OCR content field
                    assert "ocr_content" in result
                    assert result["ocr_content"]["extracted_text"] == "Test text"

        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )
