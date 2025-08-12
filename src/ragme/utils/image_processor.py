# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import base64
import json
import os
import tempfile
import warnings
from typing import Dict, Any

import requests
from PIL import Image
from exif import Image as ExifImage

# Suppress TensorFlow warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="tensorflow")
warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow")


class ImageProcessor:
    """
    Image processing utilities for EXIF extraction, TensorFlow classification, and metadata handling.
    """

    def __init__(self):
        """Initialize the image processor."""
        self._tf_model = None

    def get_image_metadata(self, image_source: str) -> Dict[str, Any]:
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
                with open(file_path, 'rb') as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content
            
            image = ExifImage(image_data)
            metadata = {
                "type": "image",
                "source": image_source,
                "exif": {}
            }
            
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

    def classify_image_with_tensorflow(self, image_source: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Classify an image using TensorFlow with a pre-trained ResNet50 model.
        
        Args:
            image_source: URL of the image or local file path (with file:// prefix)
            top_k: Number of top predictions to return
            
        Returns:
            Dictionary containing image classification results
        """
        try:
            import tensorflow as tf
            from tensorflow.keras.applications import ResNet50
            from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
            from tensorflow.keras.preprocessing import image
            import numpy as np
            import io

            if image_source.startswith("file://"):
                # Local file path
                file_path = image_source[7:]  # Remove file:// prefix
                with open(file_path, 'rb') as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content

            # Load and preprocess the image
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGB')  # Ensure RGB format
            img = img.resize((224, 224))  # ResNet50 expects 224x224

            # Convert to numpy array and preprocess
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)

            # Load pre-trained ResNet50 model (lazy loading)
            if self._tf_model is None:
                self._tf_model = ResNet50(weights='imagenet')

            # Make prediction
            preds = self._tf_model.predict(x, verbose=0)

            # Decode predictions
            results = decode_predictions(preds, top=top_k)[0]

            # Format results
            classifications = []
            for i, (imagenet_id, label, score) in enumerate(results):
                classifications.append({
                    "rank": i + 1,
                    "label": label,
                    "confidence": float(score),
                    "imagenet_id": imagenet_id
                })

            # Create classification info
            classification_info = {
                "source": image_source,
                "type": "image_classification",
                "model": "ResNet50",
                "dataset": "ImageNet",
                "top_k": top_k,
                "classifications": classifications,
                "top_prediction": classifications[0] if classifications else None,
                "tensorflow_processing": True
            }

            return classification_info

        except ImportError:
            print("TensorFlow not installed. Install with: pip install tensorflow")
            return {
                "source": image_source,
                "type": "image_classification",
                "error": "TensorFlow not available",
                "tensorflow_processing": False
            }
        except Exception as e:
            print(f"Error classifying image with TensorFlow: {e}")
            return {
                "source": image_source,
                "type": "image_classification",
                "error": str(e),
                "tensorflow_processing": False
            }

    def process_image(self, image_source: str) -> Dict[str, Any]:
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
        classification = self.classify_image_with_tensorflow(image_source)
        
        # Combine results
        processed_data = {
            **metadata,
            "classification": classification,
            "processing_timestamp": self._get_timestamp()
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
                with open(file_path, 'rb') as f:
                    image_data = f.read()
            else:
                # URL
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content
                
            return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to download and encode image from {image_source}: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()


# Global instance
image_processor = ImageProcessor()