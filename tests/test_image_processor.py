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
            assert processor._tf_model is None
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

    def test_classify_image_without_tensorflow(self):
        """Test image classification when TensorFlow is not available."""
        try:
            from src.ragme.utils.image_processor import ImageProcessor

            processor = ImageProcessor()

            # This should handle the ImportError gracefully
            result = processor.classify_image_with_tensorflow(
                "http://example.com/test.jpg"
            )

            # Should return error info for missing TensorFlow
            assert "error" in result or "tensorflow_processing" in result

        except ImportError as e:
            pytest.skip(
                f"ImageProcessor import failed due to missing dependencies: {e}"
            )
