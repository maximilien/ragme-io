# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import base64
from typing import Any

import requests
from exif import Image as ExifImage


class ImageProcessor:
    """
    Image processing utilities for EXIF extraction, PyTorch classification,
    and metadata handling.
    """

    def __init__(self):
        """Initialize the image processor."""

    def get_image_metadata(self, image_source: str) -> dict[str, Any]:
        """
        Get the EXIF metadata of an image from URL or local file path.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Dictionary containing EXIF metadata and basic image info
        """
        try:
            if image_source.startswith("file://"):
                # Local file path
                file_path = image_source[7:]  # Remove file:// prefix
                with open(file_path, "rb") as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content

            image = ExifImage(image_data)
            metadata = {"type": "image", "source": image_source, "exif": {}}

            # Extract EXIF data
            for tag in image.list_all():
                try:
                    metadata["exif"][tag] = str(image.get(tag))
                except Exception:
                    # Skip problematic EXIF tags
                    continue

            return metadata

        except Exception as e:
            print(f"Error getting image metadata: {e}")
            return {"type": "image", "source": image_source, "error": str(e)}

    def classify_image_with_pytorch(
        self, image_source: str, top_k: int = 5
    ) -> dict[str, Any]:
        """
        Classify an image using PyTorch with a pre-trained ResNet50 model.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)
            top_k: Number of top predictions to return

        Returns:
            Dictionary containing image classification results
        """
        try:
            import io

            import torch
            import torch.nn.functional as F
            from PIL import Image
            from torchvision import models, transforms

            # Set PyTorch to use CPU to avoid GPU conflicts
            device = torch.device("cpu")

            if image_source.startswith("file://"):
                # Local file path
                file_path = image_source[7:]  # Remove file:// prefix
                with open(file_path, "rb") as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content

            # Load and preprocess the image
            img = Image.open(io.BytesIO(image_data))
            img = img.convert("RGB")  # Ensure RGB format

            # Define the same transforms as used in training
            transform = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                    ),
                ]
            )

            # Apply transforms
            img_tensor = transform(img).unsqueeze(0).to(device)

            # Load pre-trained ResNet50 model (lazy loading)
            if not hasattr(self, "_pytorch_model"):
                self._pytorch_model = models.resnet50(pretrained=True)
                self._pytorch_model.eval()
                self._pytorch_model.to(device)

            # Make prediction
            with torch.no_grad():
                output = self._pytorch_model(img_tensor)
                probabilities = F.softmax(output, dim=1)
                top_probs, top_indices = torch.topk(probabilities, top_k)

            # Load ImageNet class labels
            if not hasattr(self, "_imagenet_labels"):
                # Load ImageNet labels from torchvision
                from torchvision.models.resnet import _IMAGENET_CATEGORIES

                self._imagenet_labels = _IMAGENET_CATEGORIES

            # Format results
            classifications = []
            for i in range(top_k):
                idx = top_indices[0][i].item()
                prob = top_probs[0][i].item()
                label = self._imagenet_labels[idx]

                classifications.append(
                    {
                        "rank": i + 1,
                        "label": label,
                        "confidence": prob,
                        "imagenet_id": str(idx),
                    }
                )

            # Create classification info
            classification_info = {
                "source": image_source,
                "type": "image_classification",
                "model": "ResNet50",
                "dataset": "ImageNet",
                "top_k": top_k,
                "classifications": classifications,
                "top_prediction": classifications[0] if classifications else None,
                "pytorch_processing": True,
            }

            return classification_info

        except ImportError:
            print("PyTorch not installed. Install with: pip install torch torchvision")
            return {
                "source": image_source,
                "type": "image_classification",
                "error": "PyTorch not available",
                "pytorch_processing": False,
            }
        except Exception as e:
            print(f"Error classifying image with PyTorch: {e}")
            return {
                "source": image_source,
                "type": "image_classification",
                "error": str(e),
                "pytorch_processing": False,
            }

    def process_image(self, image_source: str) -> dict[str, Any]:
        """
        Process an image by extracting metadata and performing classification.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Dictionary containing all image processing results
        """
        # Get EXIF metadata
        metadata = self.get_image_metadata(image_source)

        # Get image classification
        classification = self.classify_image_with_pytorch(image_source)

        # Combine results
        processed_data = {
            **metadata,
            "classification": classification,
            "processing_timestamp": self._get_timestamp(),
        }

        return processed_data

    def encode_image_to_base64(self, image_source: str) -> str:
        """
        Encode an image to base64 from URL or local file path.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Base64 encoded string of the image
        """
        try:
            if image_source.startswith("file://"):
                # Local file path
                file_path = image_source[7:]  # Remove file:// prefix
                with open(file_path, "rb") as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content

            return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            raise ValueError(
                f"Failed to download and encode image from {image_source}: {e}"
            ) from e

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime

        return datetime.now().isoformat()


# Global instance
image_processor = ImageProcessor()
