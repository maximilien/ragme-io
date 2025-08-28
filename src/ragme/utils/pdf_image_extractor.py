# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .config_manager import config
from .image_processor import image_processor


class PDFImageExtractor:
    """
    Extract images from PDF files and process them using the existing image processing pipeline.
    """

    def __init__(self):
        """Initialize the PDF image extractor."""
        self.logger = logging.getLogger(__name__)

    def extract_images_from_pdf(
        self, pdf_path: str, pdf_filename: str, storage_path: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Extract images from a PDF file and process them.

        Args:
            pdf_path: Path to the PDF file
            pdf_filename: Original filename of the PDF
            storage_path: Storage path of the PDF file (optional)

        Returns:
            List of processed image data dictionaries
        """
        extracted_images = []

        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)

            self.logger.info(f"Processing PDF: {pdf_filename} with {len(doc)} pages")

            for page_num in range(len(doc)):
                try:
                    page_images = self._extract_images_from_page(
                        doc[page_num], page_num + 1, pdf_filename, storage_path
                    )
                    extracted_images.extend(page_images)
                except Exception as e:
                    self.logger.warning(
                        f"Error extracting images from page {page_num + 1} of {pdf_filename}: {e}"
                    )
                    continue

            doc.close()

            self.logger.info(
                f"Extracted {len(extracted_images)} images from PDF: {pdf_filename}"
            )

        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_filename}: {e}")

        return extracted_images

    def _extract_images_from_page(
        self,
        page: fitz.Page,
        page_num: int,
        pdf_filename: str,
        storage_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract images from a single PDF page using PyMuPDF.

        Args:
            page: PyMuPDF page object
            page_num: Page number (1-based)
            pdf_filename: Original PDF filename
            storage_path: Storage path of the PDF file

        Returns:
            List of processed image data dictionaries
        """
        page_images = []

        try:
            # Get images from the page
            image_list = page.get_images()

            for img_index, img in enumerate(image_list, 1):
                try:
                    # Get image info
                    xref = img[0]  # xref number
                    img[1]  # bounding box
                    img[2]  # width
                    img[3]  # height
                    img[4]  # colorspace
                    img[5]  # bits per component

                    # Extract image data using PyMuPDF
                    pix = fitz.Pixmap(page.parent, xref)

                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                    else:  # CMYK: convert to RGB first
                        pix1 = fitz.Pixmap(fitz.csRGB, pix)
                        img_data = pix1.tobytes("png")
                        pix1 = None

                    img_name = f"image_{img_index}"

                    # Check image size constraints
                    if not self._check_image_size_constraints(img_data):
                        self.logger.debug(
                            f"Skipping image {img_index} from page {page_num}: size constraints not met"
                        )
                        pix = None
                        continue

                    # Check if image format is supported and get format info
                    format_info = self._get_image_format_info(img_data)
                    if not format_info["supported"]:
                        self.logger.debug(
                            f"Skipping image {img_index} from page {page_num}: unsupported format {format_info['format']}"
                        )
                        pix = None
                        continue

                    # Process the image
                    processed_image = self._process_extracted_image(
                        img_data,
                        img_name,
                        page_num,
                        pdf_filename,
                        storage_path,
                        format_info,
                    )

                    if processed_image:
                        page_images.append(processed_image)

                    pix = None

                except Exception as e:
                    self.logger.warning(
                        f"Error processing image {img_index} from page {page_num}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.warning(f"Error extracting images from page {page_num}: {e}")

        return page_images

    def _process_extracted_image(
        self,
        img_data: bytes,
        img_name: str,
        page_num: int,
        pdf_filename: str,
        storage_path: str | None = None,
        format_info: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Process an extracted image using the existing image processing pipeline.

        Args:
            img_data: Raw image data
            img_name: Name of the image in the PDF
            page_num: Page number where the image was found
            pdf_filename: Original PDF filename
            storage_path: Storage path of the PDF file

        Returns:
            Processed image data dictionary or None if processing failed
        """
        try:
            # Create a temporary file for the image
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(img_data)
                temp_file_path = temp_file.name

            try:
                # Process the image using the existing image processor
                file_path = f"file://{temp_file_path}"

                # Check if AI processing is enabled
                if config.get("pdf_image_extraction", {}).get("process_with_ai", True):
                    processed_data = image_processor.process_image(file_path)
                else:
                    # Basic processing without AI classification and OCR
                    processed_data = image_processor.get_image_metadata(file_path)
                    processed_data.update(
                        {
                            "classification": {
                                "top_prediction": {"label": "pdf_extracted_image"}
                            },
                            "ocr_content": None,
                            "processing_timestamp": self._get_timestamp(),
                        }
                    )

                # PyMuPDF extracts as PNG, which is already web-compatible
                # Just encode to base64 directly
                import base64

                base64_data = base64.b64encode(img_data).decode("utf-8")

                # Copy image to storage if enabled
                image_storage_path = None
                if config.is_copy_uploaded_images_enabled():
                    try:
                        from datetime import datetime

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        image_storage_path = f"images/{timestamp}_{pdf_filename}_page_{page_num}_{img_name}.png"

                        # Get storage service and upload the image data
                        from ..apis.mcp import get_storage_service

                        get_storage_service().upload_data(
                            data=img_data,
                            object_name=image_storage_path,
                            content_type="image/png",
                        )
                        self.logger.info(
                            f"Copied extracted image to storage: {image_storage_path}"
                        )

                    except Exception as storage_error:
                        self.logger.warning(
                            f"Failed to copy extracted image to storage: {storage_error}"
                        )
                        image_storage_path = None

                # Create metadata for the extracted image
                metadata = self._create_image_metadata(
                    img_name,
                    page_num,
                    pdf_filename,
                    storage_path,
                    processed_data,
                    format_info,
                    image_storage_path,
                )

                # Update metadata to reflect PNG format
                metadata["format"] = "png"
                metadata["mime_type"] = "image/png"

                # Create the final image data structure
                image_data = {
                    "url": f"pdf://{pdf_filename}/page_{page_num}/{img_name}",
                    "image_data": base64_data,
                    "metadata": metadata,
                }

                self.logger.info(
                    f"Successfully processed extracted image: {img_name} from page {page_num}"
                )

                return image_data

            finally:
                # Clean up temporary file
                try:
                    Path(temp_file_path).unlink()
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"Error processing extracted image {img_name}: {e}")
            return None

    def _create_image_metadata(
        self,
        img_name: str,
        page_num: int,
        pdf_filename: str,
        storage_path: str | None,
        processed_data: dict[str, Any],
        format_info: dict[str, Any] | None = None,
        image_storage_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Create metadata for an extracted image.

        Args:
            img_name: Name of the image in the PDF
            page_num: Page number where the image was found
            pdf_filename: Original PDF filename
            storage_path: Storage path of the PDF file
            processed_data: Data from image processing
            format_info: Optional format information for the image
            image_storage_path: Storage path of the extracted image file

        Returns:
            Metadata dictionary
        """
        # Start with the processed image data
        metadata = {**processed_data}

        # Add PDF-specific metadata
        metadata.update(
            {
                "source_type": "pdf_extracted_image",
                "pdf_filename": pdf_filename,
                "pdf_page_number": page_num,
                "pdf_image_name": img_name,
                "extraction_timestamp": datetime.now().isoformat(),
                "date_added": datetime.now().isoformat(),  # Add date_added for frontend compatibility
                "filename": f"{pdf_filename}_page_{page_num}_{img_name}.png",  # Add proper filename for AI summary
            }
        )

        # Add format information if available
        if format_info:
            metadata.update(
                {
                    "format": format_info["format"],
                    "mime_type": format_info["mime_type"],
                }
            )

        # Add PDF storage path if available
        if storage_path:
            metadata["pdf_storage_path"] = storage_path

        # Add image storage path if available
        if image_storage_path:
            metadata["storage_path"] = image_storage_path

        # Try to extract caption from OCR content if enabled and available
        if config.get("pdf_image_extraction", {}).get("extract_captions", True):
            ocr_content = processed_data.get("ocr_content", {})
            if ocr_content and ocr_content.get("text"):
                metadata["extracted_caption"] = ocr_content["text"]

        return metadata

    def add_extracted_images_to_collection(
        self, extracted_images: list[dict[str, Any]]
    ) -> bool:
        """
        Add extracted images to the image collection.

        Args:
            extracted_images: List of processed image data dictionaries

        Returns:
            True if successful, False otherwise
        """
        if not extracted_images:
            return True

        try:
            # Get image collection name from config
            image_collection_name = config.get_image_collection_name()

            # Create image-specific vector database instance
            from ..vdbs.vector_db_factory import create_vector_database

            image_vdb = create_vector_database(collection_name=image_collection_name)

            # Ensure the image collection is set up
            image_vdb.setup()

            # Check if the vector database supports images
            if image_vdb.supports_images():
                # Write to image collection with improved error handling
                success = image_vdb.write_images(extracted_images)
                if success:
                    self.logger.info(
                        "Successfully added extracted images to collection"
                    )
                else:
                    self.logger.warning(
                        "Some images failed to insert due to Weaviate embed API issues"
                    )
            else:
                # Fallback: store as text documents with image metadata
                self.logger.warning(
                    "Image collection not supported, storing as text documents"
                )
                for img in extracted_images:
                    classification = img["metadata"].get("classification", {})
                    top_pred = classification.get("top_prediction", {})
                    label = top_pred.get("label", "unknown")

                    text_representation = (
                        f"PDF Extracted Image: {img['url']}\n"
                        f"Classification: {label}\n"
                        f"Metadata: {str(img['metadata'])}"
                    )

                    image_vdb.write_documents(
                        [
                            {
                                "url": img["url"],
                                "text": text_representation,
                                "metadata": img["metadata"],
                            }
                        ]
                    )

            return True

        except Exception as e:
            self.logger.error(f"Error adding extracted images to collection: {e}")
            return False

    def _check_image_size_constraints(self, img_data: bytes) -> bool:
        """
        Check if image meets size constraints from configuration.

        Args:
            img_data: Raw image data

        Returns:
            True if image meets size constraints, False otherwise
        """
        try:
            # Get size constraints from config
            min_size_kb = config.get("pdf_image_extraction", {}).get(
                "min_image_size_kb", 1
            )
            max_size_mb = config.get("pdf_image_extraction", {}).get(
                "max_image_size_mb", 10
            )

            # Calculate image size
            img_size_kb = len(img_data) / 1024
            img_size_mb = img_size_kb / 1024

            # Check constraints
            if img_size_kb < min_size_kb:
                return False
            if img_size_mb > max_size_mb:
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Error checking image size constraints: {e}")
            return True  # Default to allowing the image if check fails

    def _get_image_format_info(self, img_data: bytes) -> dict[str, Any]:
        """
        Get image format information and check if it's supported.

        Args:
            img_data: Raw image data

        Returns:
            Dictionary with format information and support status
        """
        try:
            # Get supported formats from config
            supported_formats = config.get("pdf_image_extraction", {}).get(
                "supported_formats", []
            )

            # Try to detect image format using PIL
            import io

            from PIL import Image

            try:
                img = Image.open(io.BytesIO(img_data))
                format_name = img.format.lower() if img.format else "unknown"

                # Determine MIME type based on format
                mime_type_map = {
                    "jpeg": "image/jpeg",
                    "jpg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif",
                    "bmp": "image/bmp",
                    "tiff": "image/tiff",
                    "webp": "image/webp",
                }
                mime_type = mime_type_map.get(format_name, "image/jpeg")

                # Check if format is supported
                supported = True
                if supported_formats:
                    supported = format_name in supported_formats

                return {
                    "format": format_name,
                    "mime_type": mime_type,
                    "supported": supported,
                }

            except Exception:
                # If PIL can't read it, assume it's not supported
                return {
                    "format": "unknown",
                    "mime_type": "image/jpeg",
                    "supported": False,
                }

        except Exception as e:
            self.logger.warning(f"Error checking image format: {e}")
            return {
                "format": "unknown",
                "mime_type": "image/jpeg",
                "supported": True,  # Default to allowing the image if check fails
            }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()


# Create a singleton instance
pdf_image_extractor = PDFImageExtractor()
