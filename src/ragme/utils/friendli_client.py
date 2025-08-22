# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import base64
import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class FriendliAIClient:
    """
    Client for FriendliAI acceleration services.

    Handles image classification and OCR acceleration using FriendliAI endpoints.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the FriendliAI client.

        Args:
            config: Configuration dictionary containing FriendliAI settings
        """
        self.config = config
        self.token = config.get("friendli_token")
        self.team_id = config.get("friendli_team_id")
        self.endpoint_url = config.get("friendli_model", {}).get("endpoint_url")
        self.endpoint_id = config.get("friendli_model", {}).get("endpoint_id")
        self.acceleration_types = config.get("friendli_model", {}).get(
            "acceleration_type", []
        )

        if not all([self.token, self.team_id, self.endpoint_url, self.endpoint_id]):
            raise ValueError("Missing required FriendliAI configuration parameters")

        # Ensure the URL is in the correct format
        if self.endpoint_url and not self.endpoint_url.endswith("/v1/chat/completions"):
            if self.endpoint_url.endswith("/dedicated"):
                self.endpoint_url = f"{self.endpoint_url}/v1/chat/completions"
            elif self.endpoint_url.endswith("/"):
                self.endpoint_url = f"{self.endpoint_url}v1/chat/completions"
            else:
                self.endpoint_url = f"{self.endpoint_url}/v1/chat/completions"

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )

    def _encode_image_to_base64(self, image_data: bytes) -> str:
        """Encode image data to base64 string."""
        return base64.b64encode(image_data).decode("utf-8")

    def _make_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Make a request to the FriendliAI endpoint.

        Args:
            payload: Request payload

        Returns:
            Response from FriendliAI endpoint
        """
        try:
            response = self.session.post(self.endpoint_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"FriendliAI request failed: {e}")
            raise

    def classify_image(
        self, image_data: bytes, filename: str = "image"
    ) -> dict[str, Any]:
        """
        Classify an image using FriendliAI acceleration.

        Args:
            image_data: Raw image data as bytes
            filename: Original filename for context

        Returns:
            Classification results
        """
        if "image_classification" not in self.acceleration_types:
            raise ValueError(
                "Image classification not enabled in FriendliAI configuration"
            )

        # Encode image to base64
        image_b64 = self._encode_image_to_base64(image_data)

        # Create classification prompt
        classification_prompt = f"""
        Analyze this image and provide a detailed classification.

        Image filename: {filename}

        Please provide the classification in the following JSON format:
        {{
            "classifications": [
                {{
                    "rank": 1,
                    "label": "descriptive_label",
                    "confidence": 0.95,
                    "description": "brief_description"
                }}
            ],
            "top_prediction": {{
                "label": "best_label",
                "confidence": 0.95,
                "description": "best_description"
            }},
            "content_type": "image_type",
            "contains_text": true/false,
            "text_confidence": 0.8
        }}

        Focus on:
        1. Main subject/content of the image
        2. Whether the image contains readable text
        3. Type of content (document, screenshot, photo, etc.)
        4. Confidence levels for each classification
        """

        payload = {
            "model": self.endpoint_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": classification_prompt},
                    ],
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
        }

        try:
            response = self._make_request(payload)

            # Extract the response content
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]

                # Try to parse JSON from the response
                try:
                    # Extract JSON from the response (handle cases where there's extra text)
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        classification_result = json.loads(json_content)
                    else:
                        # Fallback: create a basic classification from text
                        classification_result = {
                            "classifications": [
                                {
                                    "rank": 1,
                                    "label": "unknown",
                                    "confidence": 0.5,
                                    "description": content[:100],
                                }
                            ],
                            "top_prediction": {
                                "label": "unknown",
                                "confidence": 0.5,
                                "description": content[:100],
                            },
                            "content_type": "unknown",
                            "contains_text": "text" in content.lower(),
                            "text_confidence": 0.5,
                        }
                except json.JSONDecodeError:
                    # Fallback: create a basic classification from text
                    classification_result = {
                        "classifications": [
                            {
                                "rank": 1,
                                "label": "unknown",
                                "confidence": 0.5,
                                "description": content[:100],
                            }
                        ],
                        "top_prediction": {
                            "label": "unknown",
                            "confidence": 0.5,
                            "description": content[:100],
                        },
                        "content_type": "unknown",
                        "contains_text": "text" in content.lower(),
                        "text_confidence": 0.5,
                    }

                return {
                    "source": filename,
                    "type": "image_classification",
                    "model": "FriendliAI",
                    "dataset": "AI_Accelerated",
                    "classifications": classification_result.get("classifications", []),
                    "top_prediction": classification_result.get("top_prediction", {}),
                    "content_type": classification_result.get(
                        "content_type", "unknown"
                    ),
                    "contains_text": classification_result.get("contains_text", False),
                    "text_confidence": classification_result.get(
                        "text_confidence", 0.0
                    ),
                    "friendli_processing": True,
                }
            else:
                raise ValueError("Invalid response format from FriendliAI")

        except Exception as e:
            logger.error(f"FriendliAI classification failed: {e}")
            return {
                "source": filename,
                "type": "image_classification",
                "error": str(e),
                "friendli_processing": False,
            }

    def extract_text_with_ocr(
        self, image_data: bytes, filename: str = "image"
    ) -> dict[str, Any]:
        """
        Extract text from an image using FriendliAI OCR acceleration.

        Args:
            image_data: Raw image data as bytes
            filename: Original filename for context

        Returns:
            OCR results
        """
        if "image_ocr" not in self.acceleration_types:
            raise ValueError("Image OCR not enabled in FriendliAI configuration")

        # Encode image to base64
        image_b64 = self._encode_image_to_base64(image_data)

        # Create OCR prompt
        ocr_prompt = """
        Extract all readable text from this image. Please provide the results in the following JSON format:

        {
            "extracted_text": "all text found in the image",
            "text_blocks": [
                {
                    "text": "text content",
                    "confidence": 0.95,
                    "bbox": [x1, y1, x2, y2]
                }
            ],
            "text_length": 150,
            "block_count": 5,
            "language": "en",
            "text_quality": "high/medium/low"
        }

        If no text is found, return:
        {
            "extracted_text": "",
            "text_blocks": [],
            "text_length": 0,
            "block_count": 0,
            "language": "unknown",
            "text_quality": "none"
        }

        Focus on:
        1. All readable text in the image
        2. Text confidence levels
        3. Text positioning (if possible)
        4. Language detection
        5. Overall text quality assessment
        """

        payload = {
            "model": self.endpoint_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": ocr_prompt},
                    ],
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1,
        }

        try:
            response = self._make_request(payload)

            # Extract the response content
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]

                # Try to parse JSON from the response
                try:
                    # Extract JSON from the response
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        json_content = content[json_start:json_end]
                        ocr_result = json.loads(json_content)
                    else:
                        # Fallback: treat the entire response as extracted text
                        ocr_result = {
                            "extracted_text": content.strip(),
                            "text_blocks": [
                                {
                                    "text": content.strip(),
                                    "confidence": 0.8,
                                    "bbox": None,
                                }
                            ],
                            "text_length": len(content.strip()),
                            "block_count": 1,
                            "language": "en",
                            "text_quality": "medium",
                        }
                except json.JSONDecodeError:
                    # Fallback: treat the entire response as extracted text
                    ocr_result = {
                        "extracted_text": content.strip(),
                        "text_blocks": [
                            {"text": content.strip(), "confidence": 0.8, "bbox": None}
                        ],
                        "text_length": len(content.strip()),
                        "block_count": 1,
                        "language": "en",
                        "text_quality": "medium",
                    }

                return {
                    "source": filename,
                    "type": "ocr_extraction",
                    "engine": "FriendliAI",
                    "confidence_threshold": 0.5,
                    "extracted_text": ocr_result.get("extracted_text", ""),
                    "text_blocks": ocr_result.get("text_blocks", []),
                    "text_length": ocr_result.get("text_length", 0),
                    "block_count": ocr_result.get("block_count", 0),
                    "language": ocr_result.get("language", "unknown"),
                    "text_quality": ocr_result.get("text_quality", "unknown"),
                    "friendli_processing": True,
                }
            else:
                raise ValueError("Invalid response format from FriendliAI")

        except Exception as e:
            logger.error(f"FriendliAI OCR failed: {e}")
            return {
                "source": filename,
                "type": "ocr_extraction",
                "error": str(e),
                "friendli_processing": False,
            }

    def process_image_parallel(
        self, image_data: bytes, filename: str = "image"
    ) -> dict[str, Any]:
        """
        Process an image with both classification and OCR in parallel using FriendliAI.

        Args:
            image_data: Raw image data as bytes
            filename: Original filename for context

        Returns:
            Combined processing results
        """
        import concurrent.futures

        results = {}

        # Run classification and OCR in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            classification_future = executor.submit(
                self.classify_image, image_data, filename
            )
            ocr_future = executor.submit(
                self.extract_text_with_ocr, image_data, filename
            )

            # Wait for both to complete
            try:
                results["classification"] = classification_future.result(timeout=60)
                results["ocr_content"] = ocr_future.result(timeout=60)
            except concurrent.futures.TimeoutError:
                logger.error("FriendliAI processing timed out")
                results["classification"] = {
                    "source": filename,
                    "type": "image_classification",
                    "error": "Processing timeout",
                    "friendli_processing": False,
                }
                results["ocr_content"] = {
                    "source": filename,
                    "type": "ocr_extraction",
                    "error": "Processing timeout",
                    "friendli_processing": False,
                }
            except Exception as e:
                logger.error(f"FriendliAI parallel processing failed: {e}")
                results["classification"] = {
                    "source": filename,
                    "type": "image_classification",
                    "error": str(e),
                    "friendli_processing": False,
                }
                results["ocr_content"] = {
                    "source": filename,
                    "type": "ocr_extraction",
                    "error": str(e),
                    "friendli_processing": False,
                }

        return results
