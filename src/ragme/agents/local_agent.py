# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import atexit
import json
import logging
import os
import signal
import time
import traceback
import warnings
from collections.abc import Callable
from pathlib import Path

import dotenv
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Suppress ResourceWarnings and other common warnings
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*PydanticJsonSchemaWarning.*"
)
warnings.filterwarnings("ignore", message=".*model_fields.*")
warnings.filterwarnings("ignore", message=".*not JSON serializable.*")

# Suppress ResourceWarnings from dependencies
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=".*Enable tracemalloc.*"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Load environment variables
dotenv.load_dotenv()

# Import configuration manager
try:
    from ..utils.config_manager import config

    # Get configuration from config.yaml
    network_config = config.get_network_config()
    RAGME_API_URL = (
        f"http://localhost:{network_config.get('api', {}).get('port', 8021)}"
    )
    RAGME_MCP_URL = (
        f"http://localhost:{network_config.get('mcp', {}).get('port', 8022)}"
    )

    # Get chunk size from agent configuration
    agent_config = config.get_agent_config("local-agent")
    DEFAULT_CHUNK_SIZE = agent_config.get("chunk_size", 1000) if agent_config else 1000

except ImportError:
    # Fallback to environment variables if config manager not available
    RAGME_API_URL = os.getenv("RAGME_API_URL")
    RAGME_MCP_URL = os.getenv("RAGME_MCP_URL")
    DEFAULT_CHUNK_SIZE = 1000

# Global reference to monitor for cleanup
_monitor = None


def chunkText(text: str, chunk_size: int = None) -> list[str]:
    """
    Split text into chunks of specified size.

    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk in characters. If None, uses DEFAULT_CHUNK_SIZE

    Returns:
        List of text chunks
    """
    if chunk_size is None:
        chunk_size = DEFAULT_CHUNK_SIZE
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence endings (., !, ?) followed by whitespace
            for i in range(end, max(start + chunk_size // 2, start), -1):
                if text[i] in ".!?" and i + 1 < len(text) and text[i + 1].isspace():
                    end = i + 1
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end

    return chunks


# Cleanup function
def cleanup():
    """Clean up resources when the application shuts down."""
    global _monitor
    try:
        if _monitor:
            _monitor.stop()
    except Exception as e:
        logging.error(f"Error during local agent cleanup: {e}")


# Register cleanup handlers
atexit.register(cleanup)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\nReceived shutdown signal. Cleaning up...")
    cleanup()
    exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class FileHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable | None = None):
        self.callback = callback
        self.supported_extensions = {".pdf", ".docx"}
        self.recently_processed = {}  # Track recently processed files to prevent duplicates

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed (debouncing mechanism)"""
        current_time = time.time()
        file_key = str(file_path)

        # Check if file was processed recently (within 10 seconds)
        if file_key in self.recently_processed:
            last_processed = self.recently_processed[file_key]
            if current_time - last_processed < 10:  # 10 second debounce
                logging.info(f"Skipping recently processed file: {file_path}")
                return False

        # Update the timestamp
        self.recently_processed[file_key] = current_time

        # Clean up old entries (older than 60 seconds)
        cutoff_time = current_time - 60
        self.recently_processed = {
            k: v for k, v in self.recently_processed.items() if v > cutoff_time
        }

        return True

    def on_created(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                if self._should_process_file(file_path):
                    logging.info(f"New file detected: {file_path}")
                    if self.callback:
                        self.callback(file_path)

    def on_modified(self, event):
        # Completely ignore file modification events to prevent duplicate processing
        # Only process files when they are first created
        pass


class DirectoryMonitor:
    def __init__(self, directory: str, callback: Callable | None = None):
        self.directory = Path(directory)
        self.observer = Observer()
        self.handler = FileHandler(callback)

    def start(self):
        """Start monitoring the directory"""
        if not self.directory.exists():
            logging.error(f"Directory does not exist: {self.directory}")
            return

        logging.info(f"Starting to monitor directory: {self.directory}")
        self.observer.schedule(self.handler, str(self.directory), recursive=False)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop monitoring the directory"""
        self.observer.stop()
        self.observer.join()
        logging.info("Stopped monitoring directory")


class RagMeLocalAgent:
    """Local agent for processing files and adding them to RAG system"""

    def __init__(
        self,
        api_url: str | None = None,
        mcp_url: str | None = None,
        watch_directory: str | None = None,
    ):
        self.api_url = api_url or RAGME_API_URL
        self.mcp_url = mcp_url or RAGME_MCP_URL
        self.watch_directory = (
            Path(watch_directory) if watch_directory else Path("./watch_directory")
        )
        self.processing_files = set()  # Track files currently being processed
        self.processed_files = set()  # Track files that have been processed recently

        if not self.api_url:
            raise ValueError("RAGME_API_URL environment variable is required")
        if not self.mcp_url:
            raise ValueError("RAGME_MCP_URL environment variable is required")

        # Clean up old processed markers on startup
        self._cleanup_old_processed_markers()

    # private methods

    def _cleanup_old_processed_markers(self):
        """Clean up old processed marker files on startup"""
        try:
            # Only look for .processed files in the watch directory
            if self.watch_directory.exists():
                for processed_file in self.watch_directory.rglob("*.processed"):
                    try:
                        # Check if the marker is old (older than 60 seconds)
                        marker_age = time.time() - processed_file.stat().st_mtime
                        if marker_age > 60:
                            processed_file.unlink(missing_ok=True)
                            logging.info(
                                f"Cleaned up old processed marker: {processed_file}"
                            )
                    except Exception as e:
                        logging.warning(
                            f"Failed to clean up processed marker {processed_file}: {e}"
                        )
        except Exception as e:
            logging.warning(f"Error during processed marker cleanup: {e}")

    def _process_pdf_file(self, file_path: Path) -> bool:
        """Process a PDF file using the MCP server"""
        try:
            # Check if file exists and is a PDF
            if not file_path.exists() or file_path.suffix.lower() != ".pdf":
                logging.error(f"Invalid PDF file: {file_path}")
                return False

            # Prepare the file for upload
            with open(file_path, "rb") as pdf_file:
                files = {"file": (file_path.name, pdf_file, "application/pdf")}

                # Call the MCP server
                response = requests.post(
                    f"{self.mcp_url}/tool/process_pdf", files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    if result["success"]:
                        data = result["data"]["data"]
                        logging.info(f"Successfully processed PDF: {file_path}")
                        logging.info(
                            f"Extracted {len(data['text'])} characters of text"
                        )
                        # Log extracted images count if available
                        if "extracted_images_count" in data:
                            logging.info(
                                f"Extracted and processed {data['extracted_images_count']} images from PDF"
                            )
                        # Add to RAG
                        self.add_to_rag(
                            {"data": data, "metadata": result["data"]["metadata"]}
                        )
                        return True
                    else:
                        logging.error(
                            f"Error processing PDF: {result.get('error', 'Unknown error')}"
                        )
                else:
                    logging.error(
                        f"Server error: {response.status_code} - {response.text}"
                    )

                return False

        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error processing PDF file {file_path}: {str(e)}")
            return False

    def _process_docx_file(self, file_path: Path) -> bool:
        """Process a DOCX file using the MCP server"""
        try:
            # Check if file exists and is a DOCX
            if not file_path.exists() or file_path.suffix.lower() != ".docx":
                logging.error(f"Invalid DOCX file: {file_path}")
                return False

            # Prepare the file for upload
            with open(file_path, "rb") as docx_file:
                files = {
                    "file": (
                        file_path.name,
                        docx_file,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                }

                # Call the MCP server
                response = requests.post(
                    f"{self.mcp_url}/tool/process_docx", files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    if result["success"]:
                        data = result["data"]["data"]
                        logging.info(f"Successfully processed DOCX: {file_path}")
                        logging.info(
                            f"Extracted {len(data['text'])} characters of text"
                        )
                        logging.info(f"Found {data['table_count']} tables")
                        # Add to RAG
                        self.add_to_rag(
                            {"data": data, "metadata": result["data"]["metadata"]}
                        )
                        return True
                    else:
                        logging.error(
                            f"Error processing DOCX: {result.get('error', 'Unknown error')}"
                        )
                else:
                    logging.error(
                        f"Server error: {response.status_code} - {response.text}"
                    )

                return False

        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error processing DOCX file {file_path}: {str(e)}")
            return False

    def _process_image_file(self, file_path: Path) -> bool:
        """Process an image file using the RAGme API"""
        try:
            # Check if file exists and is an image
            if not file_path.exists():
                logging.error(f"Image file does not exist: {file_path}")
                return False

            # Check if it's a supported image format
            supported_formats = {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".bmp",
                ".heic",
                ".heif",
            }
            if file_path.suffix.lower() not in supported_formats:
                logging.error(f"Unsupported image format: {file_path}")
                return False

            # Prepare the file for upload
            with open(file_path, "rb") as image_file:
                files = {"files": (file_path.name, image_file, "image/*")}

                # Call the RAGme API directly
                response = requests.post(f"{self.api_url}/upload-images", files=files)

                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "success":
                        logging.info(f"Successfully processed image: {file_path}")
                        logging.info(
                            f"Files processed: {result.get('files_processed', 1)}"
                        )
                        return True
                    else:
                        logging.error(
                            f"Error processing image: {result.get('message', 'Unknown error')}"
                        )
                else:
                    logging.error(
                        f"Server error: {response.status_code} - {response.text}"
                    )

                return False

        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error processing image file {file_path}: {str(e)}")
            return False

    # public methods

    def process_file(self, file_path: Path):
        """Process detected files based on their type"""
        file_ext = file_path.suffix.lower()

        # Only process files that are within the watch directory
        try:
            file_path.relative_to(self.watch_directory)
        except ValueError:
            logging.warning(
                f"File {file_path} is outside watch directory {self.watch_directory}, skipping"
            )
            return

        # Create a lock file to prevent duplicate processing
        lock_file = file_path.with_suffix(file_path.suffix + ".lock")

        # Check if lock file exists (file is being processed)
        if lock_file.exists():
            logging.info(
                f"File is being processed (lock exists), skipping: {file_path}"
            )
            return

        # Check if file was recently processed (within 60 seconds)
        processed_marker = file_path.with_suffix(file_path.suffix + ".processed")
        if processed_marker.exists():
            # Check if marker is recent (within 60 seconds)
            marker_age = time.time() - processed_marker.stat().st_mtime
            if marker_age < 60:
                logging.info(
                    f"File recently processed (marker exists), skipping: {file_path}"
                )
                return
            else:
                # Remove old marker
                processed_marker.unlink(missing_ok=True)

        # Create lock file
        try:
            lock_file.touch()
        except Exception as e:
            logging.error(f"Failed to create lock file for {file_path}: {e}")
            return

        try:
            if file_ext == ".pdf":
                success = self._process_pdf_file(file_path)
            elif file_ext == ".docx":
                success = self._process_docx_file(file_path)
            elif file_ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
                success = self._process_image_file(file_path)
            else:
                logging.warning(f"Unsupported file type: {file_path}")
                success = False

            if success:
                # Create processed marker
                processed_marker.touch()

        finally:
            # Remove lock file
            lock_file.unlink(missing_ok=True)

    def add_to_rag(self, data: dict) -> bool:
        """Add processed data to RAG system"""
        try:
            print(
                f"Adding to RAG: {json.dumps(data, indent=2)}"
            )  # Pretty print error response

            # Extract text and metadata
            text = data["data"]["text"]
            metadata = data["metadata"]

            # Ensure the type field is set correctly based on filename
            filename = metadata.get("filename", "unknown")
            if filename != "unknown":
                file_extension = Path(filename).suffix.lower()
                if file_extension:
                    # Remove the dot and convert to uppercase for consistency
                    file_type = file_extension[1:].upper()
                    metadata["type"] = file_type
                else:
                    metadata["type"] = "unknown"
            else:
                metadata["type"] = "unknown"

            # Chunk the text if it's large
            chunks = chunkText(text)

            # Generate URL like the frontend (no timestamp, API will add one if needed)
            base_filename = metadata.get("filename", "unknown")
            unique_url = f"file://{base_filename}"

            if len(chunks) == 1:
                # Single chunk - send as regular document
                document_data = {
                    "data": {
                        "documents": [
                            {
                                "text": chunks[0],
                                "url": unique_url,
                                "metadata": metadata,
                            }
                        ]
                    }
                }
            else:
                # Multiple chunks - store each chunk as a separate document
                documents = []
                for i, chunk in enumerate(chunks):
                    chunk_metadata = {
                        **metadata,
                        "total_chunks": len(chunks),
                        "is_chunked": True,
                        "chunk_index": i,
                        "chunk_sizes": [len(chunk) for chunk in chunks],
                        "original_filename": metadata.get("filename", "unknown"),
                    }

                    documents.append(
                        {
                            "text": chunk,
                            "url": f"{unique_url}#chunk-{i}",
                            "metadata": chunk_metadata,
                        }
                    )

                document_data = {"data": {"documents": documents}}

            print(f"Chunked into {len(chunks)} chunks, sending to API...")

            # Send to API
            response = requests.post(f"{self.api_url}/add-json", json=document_data)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    logging.info(
                        f"Successfully added data to RAG ({len(chunks)} chunks)"
                    )
                    return True
                else:
                    logging.error(
                        f"Error adding to RAG: {result.get('error', 'Unknown error')}"
                    )
            else:
                logging.error(f"RAG server error: {response.status_code}")
                print(
                    json.dumps(response.json(), indent=2)
                )  # Pretty print error response

            return False
        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error adding to RAG: {str(e)}")
            return False


if __name__ == "__main__":
    # Example usage
    watch_dir = "./watch_directory"
    local_agent = RagMeLocalAgent(watch_directory=watch_dir)
    monitor = DirectoryMonitor(
        directory=watch_dir,  # Directory to monitor
        callback=local_agent.process_file,
    )

    # Set global reference for cleanup
    _monitor = monitor

    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        cleanup()
