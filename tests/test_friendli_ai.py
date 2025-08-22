# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import unittest
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ragme.utils.friendli_client import FriendliAIClient
from src.ragme.utils.image_processor import ImageProcessor


class TestFriendliAIClient:
    """Test cases for FriendliAIClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "friendli_token": "test_token",
            "friendli_team_id": "test_team",
            "friendli_model": {
                "acceleration_type": ["image_classification", "image_ocr"],
                "endpoint_url": "https://api.friendli.ai/dedicated",
                "endpoint_id": "test_model",
            },
        }

        # Sample image data
        self.sample_image_data = b"fake_image_data"
        self.sample_filename = "test_image.jpg"

    def test_init_success(self):
        """Test successful initialization of FriendliAIClient."""
        client = FriendliAIClient(self.config)
        assert client.token == "test_token"
        assert client.team_id == "test_team"
        assert (
            client.endpoint_url
            == "https://api.friendli.ai/dedicated/v1/chat/completions"
        )
        assert client.endpoint_id == "test_model"
        assert client.acceleration_types == ["image_classification", "image_ocr"]

    def test_url_transformation(self):
        """Test that the endpoint URL is correctly transformed."""
        # Test with /dedicated ending
        config = self.config.copy()
        config["friendli_model"]["endpoint_url"] = "https://api.friendli.ai/dedicated"
        client = FriendliAIClient(config)
        assert (
            client.endpoint_url
            == "https://api.friendli.ai/dedicated/v1/chat/completions"
        )

        # Test with trailing slash
        config["friendli_model"]["endpoint_url"] = "https://api.friendli.ai/dedicated/"
        client = FriendliAIClient(config)
        assert (
            client.endpoint_url
            == "https://api.friendli.ai/dedicated/v1/chat/completions"
        )

        # Test with already correct URL
        config["friendli_model"]["endpoint_url"] = (
            "https://api.friendli.ai/dedicated/v1/chat/completions"
        )
        client = FriendliAIClient(config)
        assert (
            client.endpoint_url
            == "https://api.friendli.ai/dedicated/v1/chat/completions"
        )

    def test_init_missing_config(self):
        """Test initialization with missing configuration."""
        incomplete_config = {
            "friendli_token": "test_token"
            # Missing other required fields
        }

        with pytest.raises(
            ValueError, match="Missing required FriendliAI configuration parameters"
        ):
            FriendliAIClient(incomplete_config)

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_classify_image_success(self, mock_session):
        """Test successful image classification."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                    {
                        "classifications": [
                            {
                                "rank": 1,
                                "label": "golden retriever",
                                "confidence": 0.95,
                                "description": "A golden retriever dog"
                            }
                        ],
                        "top_prediction": {
                            "label": "golden retriever",
                            "confidence": 0.95,
                            "description": "A golden retriever dog"
                        },
                        "content_type": "animal",
                        "contains_text": false,
                        "text_confidence": 0.0
                    }
                    """
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.return_value.post.return_value = mock_response

        client = FriendliAIClient(self.config)
        result = client.classify_image(self.sample_image_data, self.sample_filename)

        assert result["type"] == "image_classification"
        assert result["model"] == "FriendliAI"
        assert result["friendli_processing"] is True
        assert len(result["classifications"]) == 1
        assert result["classifications"][0]["label"] == "golden retriever"

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_classify_image_invalid_json(self, mock_session):
        """Test image classification with invalid JSON response."""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is not valid JSON"}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.return_value.post.return_value = mock_response

        client = FriendliAIClient(self.config)
        result = client.classify_image(self.sample_image_data, self.sample_filename)

        assert result["type"] == "image_classification"
        assert result["friendli_processing"] is True
        assert result["classifications"][0]["label"] == "unknown"

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_extract_text_with_ocr_success(self, mock_session):
        """Test successful OCR text extraction."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                    {
                        "extracted_text": "Hello World",
                        "text_blocks": [
                            {
                                "text": "Hello World",
                                "confidence": 0.95,
                                "bbox": [10, 20, 100, 30]
                            }
                        ],
                        "text_length": 11,
                        "block_count": 1,
                        "language": "en",
                        "text_quality": "high"
                    }
                    """
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.return_value.post.return_value = mock_response

        client = FriendliAIClient(self.config)
        result = client.extract_text_with_ocr(
            self.sample_image_data, self.sample_filename
        )

        assert result["type"] == "ocr_extraction"
        assert result["engine"] == "FriendliAI"
        assert result["friendli_processing"] is True
        assert result["extracted_text"] == "Hello World"
        assert result["text_length"] == 11

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_extract_text_with_ocr_no_text(self, mock_session):
        """Test OCR with no text found."""
        # Mock response for no text
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                    {
                        "extracted_text": "",
                        "text_blocks": [],
                        "text_length": 0,
                        "block_count": 0,
                        "language": "unknown",
                        "text_quality": "none"
                    }
                    """
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.return_value.post.return_value = mock_response

        client = FriendliAIClient(self.config)
        result = client.extract_text_with_ocr(
            self.sample_image_data, self.sample_filename
        )

        assert result["type"] == "ocr_extraction"
        assert result["extracted_text"] == ""
        assert result["text_length"] == 0
        assert result["block_count"] == 0

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_process_image_parallel_success(self, mock_session):
        """Test parallel processing of image with classification and OCR."""
        # Mock response for both classification and OCR
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                    {
                        "classifications": [
                            {
                                "rank": 1,
                                "label": "document",
                                "confidence": 0.9,
                                "description": "A document with text"
                            }
                        ],
                        "top_prediction": {
                            "label": "document",
                            "confidence": 0.9,
                            "description": "A document with text"
                        },
                        "content_type": "document",
                        "contains_text": true,
                        "text_confidence": 0.8
                    }
                    """
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_session.return_value.post.return_value = mock_response

        client = FriendliAIClient(self.config)
        result = client.process_image_parallel(
            self.sample_image_data, self.sample_filename
        )

        assert "classification" in result
        assert "ocr_content" in result
        assert result["classification"]["friendli_processing"] is True
        assert result["ocr_content"]["friendli_processing"] is True

    def test_classify_image_disabled_acceleration(self):
        """Test classification when acceleration type is disabled."""
        config = self.config.copy()
        config["friendli_model"]["acceleration_type"] = [
            "image_ocr"
        ]  # Only OCR enabled

        client = FriendliAIClient(config)

        with pytest.raises(ValueError, match="Image classification not enabled"):
            client.classify_image(self.sample_image_data, self.sample_filename)

    def test_extract_text_disabled_acceleration(self):
        """Test OCR when acceleration type is disabled."""
        config = self.config.copy()
        config["friendli_model"]["acceleration_type"] = [
            "image_classification"
        ]  # Only classification enabled

        client = FriendliAIClient(config)

        with pytest.raises(ValueError, match="Image OCR not enabled"):
            client.extract_text_with_ocr(self.sample_image_data, self.sample_filename)

    @patch("src.ragme.utils.friendli_client.requests.Session")
    def test_request_timeout(self, mock_session):
        """Test handling of request timeout."""
        mock_session.return_value.post.side_effect = Exception("Request timeout")

        client = FriendliAIClient(self.config)
        result = client.classify_image(self.sample_image_data, self.sample_filename)

        assert result["type"] == "image_classification"
        assert result["friendli_processing"] is False
        assert "error" in result


class TestImageProcessorWithFriendliAI:
    """Test cases for ImageProcessor with FriendliAI integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ImageProcessor()

    @patch("src.ragme.utils.image_processor.FRIENDLI_AVAILABLE", True)
    @patch("src.ragme.utils.config_manager.config")
    def test_initialize_friendli_success(self, mock_config):
        """Test successful FriendliAI initialization."""
        mock_config.get.return_value = {
            "enabled": True,
            "friendli_ai": {
                "friendli_token": "test_token",
                "friendli_team_id": "test_team",
                "friendli_model": {
                    "acceleration_type": ["image_classification", "image_ocr"],
                    "endpoint_url": "https://api.friendli.ai/v1/chat/completions",
                    "endpoint_id": "test_model",
                },
            },
        }

        with patch("src.ragme.utils.image_processor.FriendliAIClient"):
            result = self.processor._initialize_friendli()
            assert result is True
            assert self.processor._friendli_initialized is True

    @patch("src.ragme.utils.image_processor.FRIENDLI_AVAILABLE", False)
    def test_initialize_friendli_not_available(self):
        """Test FriendliAI initialization when not available."""
        result = self.processor._initialize_friendli()
        assert result is False

    @patch("src.ragme.utils.image_processor.FRIENDLI_AVAILABLE", True)
    @patch("src.ragme.utils.config_manager.config")
    def test_initialize_friendli_disabled(self, mock_config):
        """Test FriendliAI initialization when disabled in config."""
        mock_config.get.return_value = {"enabled": False}

        result = self.processor._initialize_friendli()
        assert result is False

    @patch("src.ragme.utils.image_processor.FRIENDLI_AVAILABLE", True)
    @patch("src.ragme.utils.config_manager.config")
    def test_process_image_with_friendli_success(self, mock_config):
        """Test image processing with FriendliAI success."""
        # Mock config
        mock_config.get.return_value = {
            "enabled": True,
            "friendli_ai": {
                "friendli_token": "test_token",
                "friendli_team_id": "test_team",
                "friendli_model": {
                    "acceleration_type": ["image_classification", "image_ocr"],
                    "endpoint_url": "https://api.friendli.ai/v1/chat/completions",
                    "endpoint_id": "test_model",
                },
            },
        }

        # Mock FriendliAI client
        mock_client = Mock()
        mock_client.process_image_parallel.return_value = {
            "classification": {
                "type": "image_classification",
                "friendli_processing": True,
                "classifications": [{"label": "test", "confidence": 0.9}],
            },
            "ocr_content": {
                "type": "ocr_extraction",
                "friendli_processing": True,
                "extracted_text": "test text",
            },
        }

        with patch(
            "src.ragme.utils.image_processor.FriendliAIClient", return_value=mock_client
        ):
            self.processor._friendli_initialized = True
            self.processor._friendli_client = mock_client

            result = self.processor.process_image_with_friendli(
                b"test_data", "test.jpg"
            )

            assert result["classification"]["friendli_processing"] is True
            assert result["ocr_content"]["friendli_processing"] is True

    @patch("src.ragme.utils.image_processor.FRIENDLI_AVAILABLE", True)
    @patch("src.ragme.utils.config_manager.config")
    def test_process_image_fallback_to_standard(self, mock_config):
        """Test image processing falls back to standard when AI acceleration fails."""
        # Mock config with AI acceleration enabled
        mock_config.get.return_value = {
            "enabled": True,
            "friendli_ai": {
                "friendli_token": "test_token",
                "friendli_team_id": "test_team",
                "friendli_model": {
                    "acceleration_type": ["image_classification", "image_ocr"],
                    "endpoint_url": "https://api.friendli.ai/v1/chat/completions",
                    "endpoint_id": "test_model",
                },
            },
        }

        # Mock FriendliAI client that fails
        mock_client = Mock()
        mock_client.process_image_parallel.return_value = {
            "classification": {"friendli_processing": False, "error": "test error"},
            "ocr_content": {"friendli_processing": False, "error": "test error"},
        }

        with patch(
            "src.ragme.utils.image_processor.FriendliAIClient", return_value=mock_client
        ):
            with patch.object(self.processor, "get_image_metadata") as mock_metadata:
                with patch.object(
                    self.processor, "classify_image_with_pytorch"
                ) as mock_classify:
                    with patch.object(
                        self.processor, "extract_text_with_ocr"
                    ) as mock_ocr:
                        mock_metadata.return_value = {"type": "image", "exif": {}}
                        mock_classify.return_value = {"type": "image_classification"}
                        mock_ocr.return_value = {"type": "ocr_extraction"}

                        result = self.processor.process_image("file://test.jpg")

                        # Should fall back to standard processing
                        assert "classification" in result
                        assert "ocr_content" in result


if __name__ == "__main__":
    pytest.main([__file__])
