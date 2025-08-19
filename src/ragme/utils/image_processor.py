# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import base64
from typing import Any

import requests
from exif import Image as ExifImage

# Import HEIC support
try:
    import pillow_heif

    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False
    print("pillow-heif not installed. HEIC files will not be supported.")


class ImageProcessor:
    """
    Image processing utilities for EXIF extraction, PyTorch classification,
    OCR text extraction, and metadata handling.
    """

    def __init__(self):
        """Initialize the image processor."""
        self._ocr_reader = None
        self._ocr_initialized = False

    def _load_image_with_heic_support(self, image_data: bytes, file_path: str = None):
        """
        Load an image with HEIC support using PIL.

        Args:
            image_data: Raw image data as bytes
            file_path: Optional file path for format detection

        Returns:
            PIL Image object
        """
        try:
            import io

            from PIL import Image

            # Check if this is a HEIC file
            if file_path and file_path.lower().endswith((".heic", ".heif")):
                if HEIC_SUPPORT:
                    # Use pillow_heif to load HEIC files
                    heif_file = pillow_heif.read_heif(image_data)
                    image = Image.frombytes(
                        heif_file.mode,
                        heif_file.size,
                        heif_file.data,
                        "raw",
                        heif_file.mode,
                        heif_file.stride,
                    )
                    print(
                        f"Successfully loaded HEIC image: {file_path}, size: {image.size}, mode: {image.mode}"
                    )
                    return image
                else:
                    raise ValueError(
                        "HEIC support not available. Install pillow-heif package."
                    )

            # For other formats, use standard PIL
            img = Image.open(io.BytesIO(image_data))
            return img

        except Exception as e:
            print(f"Error loading image with HEIC support: {e}")
            # Fallback to standard PIL
            import io

            from PIL import Image

            return Image.open(io.BytesIO(image_data))

    def _initialize_ocr(self) -> bool:
        """Initialize OCR engine based on configuration."""
        try:
            from ..utils.config_manager import config

            ocr_config = config.get("ocr", {})
            if not ocr_config.get("enabled", True):
                return False

            engine = ocr_config.get("engine", "easyocr")

            if engine == "easyocr":
                import easyocr

                languages = ocr_config.get("languages", ["en"])
                self._ocr_reader = easyocr.Reader(languages)
                self._ocr_initialized = True
                return True
            elif engine == "pytesseract":
                # pytesseract is initialized on-demand
                self._ocr_initialized = True
                return True
            else:
                print(f"Unsupported OCR engine: {engine}")
                return False

        except ImportError as e:
            print(f"OCR dependencies not installed: {e}")
            print("Install with: pip install easyocr pytesseract opencv-python")
            return False
        except Exception as e:
            print(f"Error initializing OCR: {e}")
            return False

    def _should_apply_ocr(self, classification_info: dict) -> bool:
        """Determine if OCR should be applied based on image classification."""
        try:
            from ..utils.config_manager import config

            ocr_config = config.get("ocr", {})
            if not ocr_config.get("enabled", True):
                return False

            content_types = ocr_config.get("content_types", [])

            # Check if any classification matches content types that typically contain text
            classifications = classification_info.get("classifications", [])
            for classification in classifications:
                label = classification.get("label", "").lower()
                for content_type in content_types:
                    if content_type.lower() in label:
                        return True

            # Also check top prediction
            top_prediction = classification_info.get("top_prediction", {})
            if top_prediction:
                label = top_prediction.get("label", "").lower()
                for content_type in content_types:
                    if content_type.lower() in label:
                        return True

            return False

        except Exception as e:
            print(f"Error determining OCR applicability: {e}")
            return False

    def _preprocess_image_for_ocr(
        self, image_data: bytes, file_path: str = None
    ) -> bytes:
        """Preprocess image for better OCR results."""
        try:
            import cv2
            import numpy as np

            from ..utils.config_manager import config

            ocr_config = config.get("ocr", {})
            preprocessing = ocr_config.get("preprocessing", {})

            if not preprocessing.get("enabled", True):
                return image_data

            # Load image with HEIC support first
            pil_img = self._load_image_with_heic_support(image_data, file_path)
            pil_img = pil_img.convert("RGB")  # Ensure RGB format

            # Convert PIL image to OpenCV format
            img_array = np.array(pil_img)

            # Check if the image array is valid
            if (
                img_array.size == 0
                or img_array.shape[0] == 0
                or img_array.shape[1] == 0
            ):
                print(f"Warning: Invalid image array for {file_path}")
                return image_data

            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            if img is None:
                print(
                    f"Warning: Failed to convert image to OpenCV format for {file_path}"
                )
                return image_data

            # For UI screenshots, use lighter preprocessing
            # Apply preprocessing steps
            if preprocessing.get("denoise", True):
                # Use lighter denoising for UI screenshots
                img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 7, 21)

            if preprocessing.get("deskew", True):
                # Skip deskewing for UI screenshots as they're usually already aligned
                pass

            if preprocessing.get("contrast_enhancement", True):
                # Use lighter contrast enhancement for UI screenshots
                # Convert to LAB color space
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l_channel, a_channel, b_channel = cv2.split(lab)

                # Apply CLAHE to L channel with lighter settings
                clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
                l_channel = clahe.apply(l_channel)

                # Merge channels and convert back to BGR
                lab = cv2.merge([l_channel, a_channel, b_channel])
                img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            # Convert back to bytes
            _, buffer = cv2.imencode(".png", img)
            return buffer.tobytes()

        except Exception as e:
            print(f"Error preprocessing image for OCR: {e}")
            return image_data

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

            # Try to extract EXIF data, but handle format errors gracefully
            try:
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
            except (ValueError, TypeError) as exif_error:
                # Handle TIFF format errors and other EXIF parsing issues
                print(f"EXIF extraction failed (format not supported): {exif_error}")
                # Return basic metadata without EXIF
                return {
                    "type": "image",
                    "source": image_source,
                    "exif": {},
                    "exif_error": "Format not supported for EXIF extraction",
                }

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
            import torch
            import torch.nn.functional as F
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

            # Load and preprocess the image with HEIC support
            img = self._load_image_with_heic_support(image_data, image_source)
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

    def extract_text_with_ocr(self, image_source: str) -> dict[str, Any]:
        """
        Extract text from an image using OCR.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Dictionary containing OCR results and extracted text
        """
        try:
            from ..utils.config_manager import config

            # Initialize OCR if not already done
            if not self._ocr_initialized:
                if not self._initialize_ocr():
                    return {
                        "source": image_source,
                        "type": "ocr_extraction",
                        "error": "OCR not available",
                        "ocr_processing": False,
                    }

            # Load image data
            if image_source.startswith("file://"):
                file_path = image_source[7:]  # Remove file:// prefix
                with open(file_path, "rb") as f:
                    image_data = f.read()
            else:
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                image_data = response.content

            # Preprocess image for better OCR results
            processed_image_data = self._preprocess_image_for_ocr(
                image_data, image_source
            )

            ocr_config = config.get("ocr", {})
            engine = ocr_config.get("engine", "easyocr")
            confidence_threshold = ocr_config.get("confidence_threshold", 0.5)

            extracted_text = ""
            text_blocks = []
            used_engine = engine

            # Try the configured engine first
            if engine == "easyocr":
                # Use EasyOCR
                results = self._ocr_reader.readtext(processed_image_data)

                for bbox, text, confidence in results:
                    if confidence >= confidence_threshold:
                        extracted_text += text + " "
                        # Convert numpy types to native Python types for JSON serialization
                        bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else bbox
                        confidence_float = (
                            float(confidence)
                            if hasattr(confidence, "item")
                            else confidence
                        )
                        text_blocks.append(
                            {
                                "text": text,
                                "confidence": confidence_float,
                                "bbox": bbox_list,
                            }
                        )

            elif engine == "pytesseract":
                # Use pytesseract
                import pytesseract

                img = self._load_image_with_heic_support(
                    processed_image_data, image_source
                )

                # Get text with confidence scores
                data = pytesseract.image_to_data(
                    img, output_type=pytesseract.Output.DICT
                )

                for i, conf in enumerate(data["conf"]):
                    if (
                        conf >= confidence_threshold * 100
                    ):  # pytesseract uses 0-100 scale
                        text = data["text"][i].strip()
                        if text:
                            extracted_text += text + " "
                            text_blocks.append(
                                {
                                    "text": text,
                                    "confidence": conf / 100.0,  # Convert to 0-1 scale
                                    "bbox": None,  # pytesseract doesn't provide bbox in this mode
                                }
                            )

            # If EasyOCR didn't produce good results, try pytesseract as fallback
            if engine == "easyocr" and (
                len(extracted_text.strip()) < 10
                or not any(
                    word in extracted_text.lower()
                    for word in [
                        "welcome",
                        "assistant",
                        "help",
                        "add",
                        "content",
                        "documents",
                        "images",
                    ]
                )
            ):
                try:
                    import pytesseract

                    img = self._load_image_with_heic_support(
                        processed_image_data, image_source
                    )

                    # Try pytesseract with different configurations
                    # First try with default settings
                    pytesseract_text = pytesseract.image_to_string(img).strip()

                    if len(pytesseract_text) > len(extracted_text):
                        extracted_text = pytesseract_text
                        text_blocks = [
                            {"text": pytesseract_text, "confidence": 0.8, "bbox": None}
                        ]
                        used_engine = "pytesseract_fallback"

                except Exception as e:
                    print(f"Pytesseract fallback failed: {e}")

            # Clean up extracted text
            extracted_text = extracted_text.strip()

            # Ensure all values are JSON serializable
            def convert_numpy_types(obj):
                """Convert numpy types to native Python types for JSON serialization."""
                import numpy as np

                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {
                        key: convert_numpy_types(value) for key, value in obj.items()
                    }
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                else:
                    return obj

            # Convert any remaining numpy types
            text_blocks = convert_numpy_types(text_blocks)

            return {
                "source": image_source,
                "type": "ocr_extraction",
                "engine": used_engine,
                "confidence_threshold": confidence_threshold,
                "extracted_text": extracted_text,
                "text_blocks": text_blocks,
                "text_length": len(extracted_text),
                "block_count": len(text_blocks),
                "ocr_processing": True,
            }

        except ImportError:
            return {
                "source": image_source,
                "type": "ocr_extraction",
                "error": "OCR dependencies not installed",
                "ocr_processing": False,
            }
        except Exception as e:
            print(f"Error extracting text with OCR: {e}")
            return {
                "source": image_source,
                "type": "ocr_extraction",
                "error": str(e),
                "ocr_processing": False,
            }

    def process_image(self, image_source: str) -> dict[str, Any]:
        """
        Process an image by extracting metadata, performing classification, and OCR if applicable.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Dictionary containing all image processing results including OCR content
        """
        # Get EXIF metadata
        metadata = self.get_image_metadata(image_source)

        # Get image classification
        classification = self.classify_image_with_pytorch(image_source)

        # Initialize OCR result
        ocr_result = None

        # Check if OCR should be applied based on classification
        if self._should_apply_ocr(classification):
            ocr_result = self.extract_text_with_ocr(image_source)
        else:
            # Still try OCR if classification failed or OCR is forced
            from ..utils.config_manager import config

            ocr_config = config.get("ocr", {})
            if ocr_config.get("enabled", True):
                ocr_result = self.extract_text_with_ocr(image_source)

        # Combine results
        processed_data = {
            **metadata,
            "classification": classification,
            "ocr_content": ocr_result,
            "processing_timestamp": self._get_timestamp(),
        }

        return processed_data

    def encode_image_to_base64(self, image_source: str) -> str:
        """
        Encode an image to base64 from URL or local file path.
        For HEIC images, converts to JPEG format for web compatibility.

        Args:
            image_source: URL of the image or local file path (with file:// prefix)

        Returns:
            Base64 encoded string of the image (JPEG for HEIC, original format for others)
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

            # Check if this is a HEIC file and convert to JPEG for web compatibility
            if image_source.lower().endswith((".heic", ".heif")):
                # Load HEIC image and convert to JPEG
                pil_img = self._load_image_with_heic_support(image_data, image_source)
                pil_img = pil_img.convert("RGB")  # Ensure RGB format

                # Convert to JPEG bytes
                import io

                jpeg_buffer = io.BytesIO()
                pil_img.save(jpeg_buffer, format="JPEG", quality=85)
                jpeg_data = jpeg_buffer.getvalue()

                print(f"Converted HEIC image to JPEG: {image_source}")
                return base64.b64encode(jpeg_data).decode("utf-8")
            else:
                # For other formats, encode as-is
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
