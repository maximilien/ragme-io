"""
Safe logging utilities for RAGme system.
Prevents log pollution from verbose data like base64 images.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_log_image_results(
    image_results: list[dict[str, Any]], context: str = "", max_images: int = 3
) -> None:
    """
    Safely log image results without exposing base64 data or other verbose fields.

    Args:
        image_results: List of image result dictionaries
        context: Context string for the log message
        max_images: Maximum number of images to log details for
    """
    if not image_results:
        logger.info(f"📸 {context}: No image results")
        return

    logger.info(f"📸 {context}: {len(image_results)} images found")

    # Log safe information for each image
    for i, img in enumerate(image_results[:max_images]):
        safe_info = create_safe_image_info(img)
        logger.info(f"📸 Image {i + 1}: {safe_info}")

    if len(image_results) > max_images:
        logger.info(f"📸 ... and {len(image_results) - max_images} more images")


def create_safe_image_info(img: dict[str, Any]) -> dict[str, Any]:
    """
    Create a safe copy of image info for logging, excluding verbose fields.

    Args:
        img: Image result dictionary

    Returns:
        Safe image info dictionary for logging
    """
    # Safely handle ID - convert to string first, then truncate
    img_id = img.get("id", "unknown")
    if img_id != "unknown":
        img_id_str = str(img_id)
        if len(img_id_str) > 20:
            img_id_str = img_id_str[:20] + "..."
    else:
        img_id_str = "unknown"

    safe_info = {
        "id": img_id_str,
        "filename": img.get("metadata", {}).get("filename", "unknown"),
        "url": truncate_string(img.get("url", "unknown"), 50),
    }

    # Add AI classification if available
    classification = img.get("metadata", {}).get("classification", {})
    top_pred = classification.get("top_prediction", {})
    if top_pred:
        safe_info["ai_label"] = top_pred.get("label", "unknown")
        safe_info["ai_confidence"] = f"{top_pred.get('confidence', 0):.2%}"

    return safe_info


def safe_log_sample_image(img: dict[str, Any], context: str = "Sample image") -> None:
    """
    Safely log a single sample image without exposing base64 data.

    Args:
        img: Image result dictionary
        context: Context string for the log message
    """
    safe_info = create_safe_image_info(img)
    logger.info(f"🔍 {context}: {safe_info}")


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string if it exceeds the maximum length.

    Args:
        text: String to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def safe_log_search_results(
    results: list[dict[str, Any]], context: str = "", result_type: str = "results"
) -> None:
    """
    Safely log search results without exposing verbose data.

    Args:
        results: List of search result dictionaries
        context: Context string for the log message
        result_type: Type of results being logged
    """
    if not results:
        logger.info(f"🔍 {context}: No {result_type}")
        return

    logger.info(f"🔍 {context}: {len(results)} {result_type} found")

    # Log safe information for first few results
    for i, result in enumerate(results[:3]):
        safe_info = create_safe_result_info(result)
        logger.info(f"🔍 {result_type.capitalize()} {i + 1}: {safe_info}")

    if len(results) > 3:
        logger.info(f"🔍 ... and {len(results) - 3} more {result_type}")


def create_safe_result_info(result: dict[str, Any]) -> dict[str, Any]:
    """
    Create safe result info for logging, excluding verbose fields.

    Args:
        result: Search result dictionary

    Returns:
        Safe result info dictionary for logging
    """
    # Safely handle ID - convert to string first, then truncate
    result_id = result.get("id", "unknown")
    if result_id != "unknown":
        result_id_str = str(result_id)
        if len(result_id_str) > 20:
            result_id_str = result_id_str[:20] + "..."
    else:
        result_id_str = "unknown"

    safe_info = {
        "id": result_id_str,
        "url": truncate_string(result.get("url", "unknown"), 50),
        "score": result.get("score", "no_score"),
    }

    # Add filename if available
    filename = result.get("metadata", {}).get("filename", "")
    if filename:
        safe_info["filename"] = filename

    # Add text preview if available (truncated)
    text = result.get("text", "")
    if text:
        safe_info["text_preview"] = truncate_string(text, 100)

    return safe_info
