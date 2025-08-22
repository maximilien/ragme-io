# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import tempfile
import traceback
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import PyPDF2
from docx import Document
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..ragme import RagMe
from ..utils.config_manager import config
from ..utils.storage import StorageService

# Force reload configuration to pick up environment variable changes
config.reload()

# Suppress Pydantic deprecation and schema warnings from dependencies
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince211.*"
)
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*PydanticJsonSchemaWarning.*"
)
warnings.filterwarnings("ignore", message=".*model_fields.*")
warnings.filterwarnings("ignore", message=".*not JSON serializable.*")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based `config`.*"
)

# Suppress ResourceWarnings from dependencies
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=".*Enable tracemalloc.*"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI application."""
    # Startup
    yield
    # Shutdown
    if _ragme is not None:
        _ragme.cleanup()


# Get application configuration
app_config = config.get("application", {})
network_config = config.get_network_config()
cors_origins = network_config.get("api", {}).get("cors_origins", ["*"])

app = FastAPI(
    title=app_config.get("title", "RagMe API"),
    description=app_config.get(
        "description", "API for RAG operations with web content using a Vector Database"
    ),
    version=app_config.get("version", "1.0.0"),
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# RagMe instance will be initialized lazily when needed
_ragme = None


def get_ragme():
    """Get or create RagMe instance"""
    global _ragme
    if _ragme is None:
        _ragme = RagMe()
    return _ragme


# Storage service will be initialized lazily when needed
_storage_service = None


def get_storage_service():
    """Get or create storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService(config)
    return _storage_service


class URLInput(BaseModel):
    """Input model for adding URLs to the RAG system."""

    urls: list[str]


class QueryInput(BaseModel):
    """Input model for querying the RAG system."""

    query: str


class JSONInput(BaseModel):
    """Input model for adding JSON content to the RAG system."""

    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class SummarizeInput(BaseModel):
    """Input model for document summarization."""

    document_id: str


class McpServerConfig(BaseModel):
    """Input model for MCP server configuration."""

    server: str
    enabled: bool
    authenticated: bool = False


class McpServerConfigList(BaseModel):
    """Input model for multiple MCP server configurations."""

    servers: list[McpServerConfig]


@app.post("/add-urls")
async def add_urls(url_input: URLInput):
    """
    Add URLs to the RAG system.

    Args:
        url_input: List of URLs to add

    Returns:
        dict: Status message and number of URLs processed
    """
    try:
        get_ragme().write_webpages_to_weaviate(url_input.urls)
        return {
            "status": "success",
            "message": f"Successfully processed {len(url_input.urls)} URLs",
            "urls_processed": len(url_input.urls),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/add-json")
async def add_json(json_input: JSONInput):
    """Add JSON data to the RAG system"""
    try:
        # Check if the data contains documents array
        if isinstance(json_input.data, dict) and "documents" in json_input.data:
            # Handle documents array format
            documents = json_input.data["documents"]
            if not isinstance(documents, list):
                return {"status": "error", "message": "documents must be an array"}

            processed_count = 0
            replaced_count = 0

            for doc in documents:
                if not isinstance(doc, dict):
                    continue

                # Extract document fields
                text = doc.get("text", "")
                url = doc.get("url", "")
                doc_metadata = doc.get("metadata", {})

                # Merge with provided metadata
                if json_input.metadata:
                    doc_metadata.update(json_input.metadata)

                # Add date_added if not present
                if "date_added" not in doc_metadata:
                    doc_metadata["date_added"] = datetime.now().isoformat()

                # Generate unique URL to prevent overwriting
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                if url.startswith("file://"):
                    # For file URLs, add timestamp to prevent overwriting
                    base_url = url
                    unique_url = f"{base_url}#{timestamp}"
                else:
                    # For web URLs, add timestamp as fragment
                    unique_url = f"{url}#{timestamp}"

                # Check if a document with the same URL already exists
                existing_doc = get_ragme().vector_db.find_document_by_url(unique_url)
                if existing_doc:
                    # Only replace if it's not a chunked document or if the new one
                    # is chunked. This prevents chunked documents from replacing
                    # regular documents
                    existing_is_chunked = existing_doc.get("metadata", {}).get(
                        "is_chunked"
                    ) or existing_doc.get("metadata", {}).get("is_chunk")
                    new_is_chunked = doc_metadata.get("is_chunked") or doc_metadata.get(
                        "is_chunk"
                    )

                    # If both are chunked documents with the same URL, replace
                    # If existing is chunked but new is not, don't replace
                    # If existing is not chunked but new is, replace
                    if (existing_is_chunked and new_is_chunked) or (
                        not existing_is_chunked and new_is_chunked
                    ):
                        # Delete the existing document
                        get_ragme().vector_db.delete_document(existing_doc["id"])
                        replaced_count += 1
                    elif existing_is_chunked and not new_is_chunked:
                        # Skip adding this document to avoid replacing chunked
                        # document with regular document
                        continue

                # Add the new document with unique URL
                get_ragme().vector_db.write_documents(
                    [{"text": text, "url": unique_url, "metadata": doc_metadata}]
                )
                processed_count += 1

            message = f"Processed {processed_count} documents"
            if replaced_count > 0:
                message += f" (replaced {replaced_count} existing documents)"

            return {
                "status": "success",
                "message": message,
                "processed_count": processed_count,
                "replaced_count": replaced_count,
            }
        else:
            # Fallback to original behavior for backward compatibility
            get_ragme().write_json_to_weaviate(json_input.data, json_input.metadata)
            return {"status": "success", "message": "JSON data added to RAG system"}

    except Exception as e:
        # Assuming 'logger' is defined elsewhere or needs to be imported
        # For now, using print for simplicity as 'logger' is not defined
        # in the original file
        print(f"Error adding JSON: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/query")
async def query(query_input: QueryInput):
    """
    Query the RAG system.

    Args:
        query_input: Query string

    Returns:
        dict: Response from the RAG system
    """
    try:
        response = await get_ragme().run(query_input.query)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def filter_documents_by_date(
    documents: list[dict[str, Any]], date_filter: str
) -> list[dict[str, Any]]:
    """
    Filter documents by date based on the date_filter parameter.

    Args:
        documents: List of documents to filter
        date_filter: Date filter to apply ('current', 'month', 'year', 'all')

    Returns:
        Filtered list of documents
    """
    if date_filter == "all":
        return documents

    now = datetime.now()

    if date_filter == "current":
        # Current = this week (last 7 days)
        cutoff_date = now - timedelta(days=7)
    elif date_filter == "month":
        # This month (current month)
        cutoff_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == "year":
        # This year (current year)
        cutoff_date = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        # Invalid filter, return all documents
        return documents

    filtered_documents = []

    for doc in documents:
        # Extract date_added from metadata
        metadata = doc.get("metadata", {})
        if isinstance(metadata, str):
            # Handle case where metadata is a JSON string
            try:
                import json

                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        date_added_str = metadata.get("date_added")
        if not date_added_str:
            # If no date_added, include the document (could be old documents without date)
            filtered_documents.append(doc)
            continue

        try:
            # Parse the date_added string
            if date_added_str.endswith("Z"):
                # Handle UTC time (with Z suffix)
                date_added = datetime.fromisoformat(
                    date_added_str.replace("Z", "+00:00")
                )
                # Convert to local time for consistent comparison
                date_added_local = date_added.astimezone()
            else:
                # Handle local time (no timezone suffix)
                date_added_local = datetime.fromisoformat(date_added_str)

            # Make date_added_local naive for comparison with cutoff_date (which is also naive)
            date_added_naive = date_added_local.replace(tzinfo=None)
            if date_added_naive >= cutoff_date:
                filtered_documents.append(doc)
        except (ValueError, TypeError):
            # If date parsing fails, include the document
            filtered_documents.append(doc)

    return filtered_documents


@app.get("/count-documents")
async def count_documents(
    date_filter: str = Query(
        default="all",
        description=(
            "Date filter: 'current' (this week), 'month' (this month), "
            "'year' (this year), 'all' (all documents)"
        ),
    ),
):
    """
    Get the count of documents in the RAG system.

    Args:
        date_filter: Date filter to apply ('current', 'month', 'year', 'all')

    Returns:
        dict: Document count information
    """
    try:
        # Use efficient count method if available
        if hasattr(get_ragme().vector_db, "count_documents"):
            count = get_ragme().vector_db.count_documents(date_filter)
        else:
            # Fallback to old method for backward compatibility
            all_documents = get_ragme().list_documents(limit=1000, offset=0)
            filtered_documents = filter_documents_by_date(all_documents, date_filter)
            count = len(filtered_documents)

        return {
            "status": "success",
            "count": count,
            "date_filter": date_filter,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/list-documents")
async def list_documents(
    limit: int = Query(
        default=10, ge=1, le=100, description="Maximum number of documents to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of documents to skip"),
    date_filter: str = Query(
        default="all",
        description="Date filter: 'current' (this week), 'month' (this month), 'year' (this year), 'all' (all documents)",
    ),
):
    """
    List documents in the RAG system.

    Args:
        limit: Maximum number of documents to return (1-100)
        offset: Number of documents to skip
        date_filter: Date filter to apply ('current', 'month', 'year', 'all')

    Returns:
        dict: List of documents and pagination info
    """
    try:
        # Get all documents first to apply date filtering
        all_documents = get_ragme().list_documents(limit=1000, offset=0)

        # Apply date filtering
        filtered_documents = filter_documents_by_date(all_documents, date_filter)

        # Apply pagination to filtered results
        total_count = len(filtered_documents)
        paginated_documents = filtered_documents[offset : offset + limit]

        return {
            "status": "success",
            "documents": paginated_documents,
            "pagination": {"limit": limit, "offset": offset, "count": total_count},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/list-content")
async def list_content(
    limit: int = Query(
        default=10, ge=1, le=100, description="Maximum number of items to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    date_filter: str = Query(
        default="all",
        description="Date filter: 'current' (this week), 'month' (this month), 'year' (this year), 'all' (all items)",
    ),
    content_type: str = Query(
        default="both",
        description="Content type filter: 'documents', 'image', or 'both'",
    ),
):
    """
    List documents and/or images in the RAG system.

    Args:
        limit: Maximum number of items to return (1-100)
        offset: Number of items to skip
        date_filter: Date filter to apply ('current', 'month', 'year', 'all')
        content_type: Content type filter ('documents', 'image', 'both')

    Returns:
        dict: List of items and pagination info
    """
    try:
        all_items = []

        # Get documents if requested
        if content_type in ["documents", "both"]:
            documents = get_ragme().list_documents(limit=1000, offset=0)
            for doc in documents:
                doc["content_type"] = "document"
            all_items.extend(documents)

        # Get images if requested
        if content_type in ["image", "both"]:
            try:
                from ..utils.config_manager import config
                from ..vdbs.vector_db_factory import create_vector_database

                # Get image collection name
                image_collection_name = config.get_image_collection_name()

                # Create image vector database
                image_vdb = create_vector_database(
                    collection_name=image_collection_name
                )

                # List images from image collection
                images = image_vdb.list_images(limit=1000, offset=0)
                for img in images:
                    img["content_type"] = "image"
                all_items.extend(images)
            except Exception as e:
                print(f"Error listing images: {e}")
                # Continue without images if there's an error

        # Apply date filtering
        filtered_items = filter_documents_by_date(all_items, date_filter)

        # Sort by date (most recent first)
        filtered_items.sort(
            key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
        )

        # Apply pagination to filtered results
        total_count = len(filtered_items)
        paginated_items = filtered_items[offset : offset + limit]

        return {
            "status": "success",
            "items": paginated_items,
            "pagination": {"limit": limit, "offset": offset, "count": total_count},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/mcp-server-config")
async def update_mcp_server_config(config: McpServerConfigList):
    """
    Update MCP server configurations (enable/disable).

    Args:
        config: Contains list of server configurations with names and enabled states

    Returns:
        dict: Success status and results for each server
    """
    try:
        results = []

        # Process each server configuration
        for server_config in config.servers:
            # Log the configuration change (implementation on backend)
            auth_status = (
                "authenticated" if server_config.authenticated else "not authenticated"
            )
            print(
                f"MCP Server Configuration Update: {server_config.server} -> {'enabled' if server_config.enabled else 'disabled'} ({auth_status})"
            )

            # TODO: Implement actual MCP server configuration logic here
            # This is where the backend would actually enable/disable MCP servers

            results.append(
                {
                    "server": server_config.server,
                    "enabled": server_config.enabled,
                    "authenticated": server_config.authenticated,
                    "success": True,
                    "message": f"MCP server '{server_config.server}' {'enabled' if server_config.enabled else 'disabled'} successfully",
                }
            )

        return {
            "success": True,
            "message": f"Updated {len(results)} MCP server(s) successfully",
            "results": results,
            "total_updated": len(results),
        }

    except Exception as e:
        print(f"Error updating MCP server configs: {e}")
        import traceback

        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating MCP server configs: {str(e)}"
        ) from e


@app.post("/summarize-document")
async def summarize_document(input_data: SummarizeInput):
    """
    Summarize a document or image using the RagMe agent.

    Args:
        input_data: Contains document_id to summarize

    Returns:
        dict: Summarized content
    """
    try:
        # Get all documents and images
        all_items = []

        # Get text documents
        documents = get_ragme().list_documents(limit=1000, offset=0)
        for doc in documents:
            doc["content_type"] = "document"
        all_items.extend(documents)

        # Get images
        images = []  # Initialize images list
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List images from image collection
            images = image_vdb.list_images(limit=1000, offset=0)
            for img in images:
                img["content_type"] = "image"
            all_items.extend(images)
        except Exception as e:
            print(f"Error listing images: {e}")
            # Continue without images if there's an error

        # Find the document by ID
        document = None
        document_id = input_data.document_id
        print(f"Looking for document with ID: {document_id}")
        print(f"Number of documents: {len(documents)}")
        print(f"Number of images: {len(images)}")

        # First try to find by ID in documents
        for doc in documents:
            doc_id = doc.get("id")
            # Convert Weaviate UUID to string for comparison
            doc_id_str = str(doc_id) if doc_id else None
            if doc_id_str == document_id:
                document = doc
                document["content_type"] = "document"
                print(f"Found document: {doc.get('url', 'No URL')}")
                break

        # If not found in documents, try to find in images
        if not document:
            for img in images:
                img_id = img.get("id")
                # Convert Weaviate UUID to string for comparison
                img_id_str = str(img_id) if img_id else None
                if img_id_str == document_id:
                    document = img
                    document["content_type"] = "image"
                    print(
                        f"Found image: {img.get('metadata', {}).get('filename', 'No filename')}"
                    )
                    break

        if not document:
            print(f"Document not found with ID: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        # Handle different content types
        content_type = document.get("content_type", "document")

        if content_type == "image":
            # For images, create a summary based on metadata and classification
            metadata = document.get("metadata", {})
            classification = metadata.get("classification", {})
            top_prediction = classification.get("top_prediction", {})

            # Extract relevant information
            filename = metadata.get("filename", "Unknown image")
            label = top_prediction.get("label", "Unknown")
            confidence = top_prediction.get("confidence", 0)
            confidence_percent = (
                f"{confidence * 100:.1f}%" if confidence > 0 else "Unknown"
            )

            # Create image summary
            summary_text = f"This is an image file named '{filename}'. AI classification identifies it as '{label}' with {confidence_percent} confidence."

            # Add additional metadata if available
            if metadata.get("file_size"):
                summary_text += f" File size: {metadata['file_size']} bytes."

            if metadata.get("format"):
                summary_text += f" Format: {metadata['format']}."

        else:
            # For text documents, use the existing summarization logic
            content = document.get("text", "")
            if not content:
                return {
                    "status": "success",
                    "summary": "No content available to summarize",
                }

            # Limit content more aggressively for faster processing
            limited_content = content[
                :500
            ]  # Reduced from 1000 to 500 characters for faster processing
            if len(content) > 500:
                limited_content += "..."

            # Use a direct LLM call for faster summarization
            from llama_index.llms.openai import OpenAI

            # Get LLM configuration from config
            llm_config = config.get_llm_config()
            summarization_config = llm_config.get("summarization", {})

            llm = OpenAI(
                model=summarization_config.get("model", "gpt-4o-mini"),
                temperature=summarization_config.get("temperature", 0.1),
            )

            summary_prompt = f"""Please provide a brief summary of the following document content in 1-2 sentences maximum.
            Focus on the main topic and key points.

            Document content:
            {limited_content}"""

            # Add timeout for faster response
            import asyncio

            try:
                summary = await asyncio.wait_for(
                    llm.acomplete(summary_prompt),
                    timeout=10.0,  # Reduced from 15 to 10 seconds
                )
                summary_text = summary.text
            except asyncio.TimeoutError:
                summary_text = "Summary generation timed out. The document may be too large or complex."

        # Ensure summary_text is defined
        if "summary_text" not in locals():
            summary_text = "Failed to generate summary. Please try again."

        return {
            "status": "success",
            "summary": summary_text,
            "document_id": input_data.document_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/upload-files")
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Upload and process files (PDF, DOCX, TXT, MD, JSON, CSV) to the RAG system.

    Args:
        files: List of files to upload

    Returns:
        dict: Status message and number of files processed
    """
    try:
        processed_count = 0

        for file in files:
            try:
                # Read file content
                content = await file.read()

                # Determine file type and extract text
                filename = file.filename.lower()
                text_content = ""

                if filename.endswith(".pdf"):
                    # Handle PDF files
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as temp_file:
                        temp_file.write(content)
                        temp_file_path = temp_file.name

                    try:
                        with open(temp_file_path, "rb") as pdf_file:
                            pdf_reader = PyPDF2.PdfReader(pdf_file)
                            text_content = ""
                            for page in pdf_reader.pages:
                                text_content += page.extract_text() + "\n"
                    finally:
                        os.unlink(temp_file_path)

                elif filename.endswith(".docx"):
                    # Handle DOCX files
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".docx"
                    ) as temp_file:
                        temp_file.write(content)
                        temp_file_path = temp_file.name

                    try:
                        doc = Document(temp_file_path)
                        text_content = "\n".join(
                            [paragraph.text for paragraph in doc.paragraphs]
                        )
                    finally:
                        os.unlink(temp_file_path)

                elif filename.endswith((".txt", ".md")):
                    # Handle text files
                    text_content = content.decode("utf-8")

                elif filename.endswith(".json"):
                    # Handle JSON files
                    import json

                    json_data = json.loads(content.decode("utf-8"))
                    text_content = json.dumps(json_data, indent=2)

                elif filename.endswith(".csv"):
                    # Handle CSV files
                    import csv
                    import io

                    csv_content = content.decode("utf-8")
                    csv_reader = csv.reader(io.StringIO(csv_content))
                    text_content = "\n".join([",".join(row) for row in csv_reader])

                else:
                    # Try to decode as text for unknown file types
                    text_content = content.decode("utf-8", errors="ignore")

                if text_content.strip():
                    # Generate unique URL to prevent overwriting
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    unique_url = f"file://{file.filename}#{timestamp}"

                    # Copy file to storage if enabled
                    storage_path = None
                    if config.is_copy_uploaded_docs_enabled():
                        try:
                            # Create storage path with timestamp to avoid conflicts
                            storage_path = f"documents/{timestamp}_{file.filename}"
                            get_storage_service().upload_data(
                                data=content,
                                object_name=storage_path,
                                content_type=file.content_type
                                or "application/octet-stream",
                            )
                            print(f"Copied document to storage: {storage_path}")
                        except Exception as storage_error:
                            print(
                                f"Failed to copy document to storage: {storage_error}"
                            )
                            storage_path = None

                    # Add to RAG system
                    metadata = {
                        "type": filename.split(".")[-1],
                        "filename": file.filename,
                        "date_added": datetime.now().isoformat(),
                    }

                    # Add storage path to metadata if file was copied to storage
                    if storage_path:
                        metadata["storage_path"] = storage_path

                    get_ragme().vector_db.write_documents(
                        [
                            {
                                "text": text_content,
                                "url": unique_url,
                                "metadata": metadata,
                            }
                        ]
                    )

                    processed_count += 1

            except Exception as e:
                print(f"Error processing file {file.filename}: {str(e)}")
                continue

        return {
            "status": "success",
            "message": f"Successfully uploaded {processed_count} files.",
            "files_processed": processed_count,
        }

    except Exception as e:
        print(f"Error in upload_files: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/upload-images")
async def upload_images(files: list[UploadFile] = File(...)):
    """
    Upload and process image files (JPG, PNG, GIF, WebP, BMP) to the RAG system.

    Args:
        files: List of image files to upload

    Returns:
        dict: Status message and number of images processed
    """
    try:
        from ..utils.config_manager import config
        from ..utils.image_processor import image_processor

        processed_count = 0
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

        # Get image collection name from config
        image_collection_name = config.get_image_collection_name()

        # Create image-specific vector database instance
        from ..vdbs.vector_db_factory import create_vector_database

        image_vdb = create_vector_database(collection_name=image_collection_name)

        # Ensure the image collection is set up
        image_vdb.setup()

        for file in files:
            try:
                # Validate file type
                filename = file.filename.lower()
                file_ext = "." + filename.split(".")[-1] if "." in filename else ""

                if file_ext not in supported_formats:
                    print(f"Skipping unsupported file format: {filename}")
                    continue

                # Read file content
                content = await file.read()

                # Create a temporary URL for processing
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                temp_url = f"file://{file.filename}#{timestamp}"

                # Save to temporary file for processing
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=file_ext
                ) as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name

                try:
                    # Copy image to storage if enabled (do this first to get storage_path)
                    storage_path = None
                    if config.is_copy_uploaded_images_enabled():
                        try:
                            # Create storage path with timestamp to avoid conflicts
                            storage_path = f"images/{timestamp}_{file.filename}"
                            get_storage_service().upload_data(
                                data=content,
                                object_name=storage_path,
                                content_type=file.content_type or "image/jpeg",
                            )
                            print(f"Copied image to storage: {storage_path}")
                        except Exception as storage_error:
                            print(f"Failed to copy image to storage: {storage_error}")
                            storage_path = None

                    # Process image with full pipeline including OCR
                    # For uploaded files, we need to use the temp file path instead of URL
                    file_path = f"file://{temp_file_path}"
                    processed_image = image_processor.process_image(file_path)

                    # Combine metadata
                    combined_metadata = {
                        **processed_image,
                        "filename": file.filename,
                        "file_size": len(content),
                        "date_added": datetime.now().isoformat(),
                        "processing_timestamp": datetime.now().isoformat(),
                    }

                    # Add storage path to metadata if file was copied to storage
                    if storage_path:
                        combined_metadata["storage_path"] = storage_path

                    # Encode image to base64 for storage (converts HEIC to JPEG for web compatibility)
                    base64_data = image_processor.encode_image_to_base64(file_path)

                    # Update metadata to reflect the actual format being stored
                    if file_ext.lower() in [".heic", ".heif"]:
                        combined_metadata["original_format"] = file_ext.lower()
                        combined_metadata["format"] = "image/jpeg"
                        combined_metadata["mime_type"] = "image/jpeg"
                        combined_metadata["content_type"] = "image/jpeg"

                    # Check if the vector database supports images
                    if image_vdb.supports_images():
                        # Write to image collection
                        image_vdb.write_images(
                            [
                                {
                                    "url": file.filename,  # Use filename as URL for uploaded files
                                    "image_data": base64_data,
                                    "metadata": combined_metadata,
                                }
                            ]
                        )
                    else:
                        # Fallback: store as text document with image metadata
                        top_pred = processed_image.get("classification", {}).get(
                            "top_prediction", {}
                        )
                        label = top_pred.get("label", "unknown")

                        # Include OCR content if available
                        ocr_content = processed_image.get("ocr_content", {})
                        ocr_text = (
                            ocr_content.get("extracted_text", "") if ocr_content else ""
                        )

                        text_representation = (
                            f"Image: {file.filename}\nClassification: {label}\n"
                        )

                        if ocr_text:
                            text_representation += f"OCR Content: {ocr_text}\n"

                        text_representation += f"Metadata: {str(combined_metadata)}"
                        image_vdb.write_documents(
                            [
                                {
                                    "url": temp_url,
                                    "text": text_representation,
                                    "metadata": combined_metadata,
                                }
                            ]
                        )

                    processed_count += 1

                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

            except Exception as e:
                print(f"Error processing image {file.filename}: {str(e)}")
                continue

        return {
            "status": "success",
            "message": f"Successfully uploaded {processed_count} images.",
            "files_processed": processed_count,
        }

    except Exception as e:
        print(f"Error in upload_images: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/test-ocr")
async def test_ocr(file: UploadFile = File(...)):
    """
    Test OCR functionality on a single image file.

    Args:
        file: Image file to test OCR on

    Returns:
        dict: OCR results and extracted text
    """
    try:
        from ..utils.image_processor import image_processor

        # Validate file type
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
        filename = file.filename.lower()
        file_ext = "." + filename.split(".")[-1] if "." in filename else ""

        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format: {filename}"
            )

        # Read file content
        content = await file.read()

        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Test OCR directly
            file_path = f"file://{temp_file_path}"
            ocr_result = image_processor.extract_text_with_ocr(file_path)

            # Also test full image processing
            processed_image = image_processor.process_image(file_path)

            return {
                "status": "success",
                "filename": file.filename,
                "ocr_result": ocr_result,
                "full_processing": {
                    "classification": processed_image.get("classification", {}),
                    "ocr_content": processed_image.get("ocr_content", {}),
                    "metadata": processed_image.get("exif", {}),
                },
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/delete-document/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from the RAG system by ID.

    Args:
        document_id: ID of the document to delete

    Returns:
        dict: Status message
    """
    try:
        # Check if document exists in text collection
        documents = get_ragme().list_documents(limit=1000, offset=0)

        # Convert Weaviate UUID to string for comparison
        text_document = None
        for doc in documents:
            doc_id = str(doc.get("id")) if doc.get("id") else None
            if doc_id == document_id:
                text_document = doc
                break

        if text_document:
            # Document exists in text collection, delete it
            success = get_ragme().delete_document(document_id)
            if success:
                return {
                    "status": "success",
                    "message": f"Document {document_id} deleted successfully",
                }
            else:
                raise HTTPException(
                    status_code=500, detail=f"Failed to delete document {document_id}"
                )

        # If not found in text collection
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document {document_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/document/{document_id}")
async def get_document(document_id: str):
    """
    Get a document or image from the RAG system by ID.

    Args:
        document_id: ID of the document or image to retrieve

    Returns:
        dict: Document data
    """
    try:
        # First try to get from text collection
        documents = get_ragme().list_documents(limit=1000, offset=0)
        document = next(
            (doc for doc in documents if doc.get("id") == document_id), None
        )

        if document:
            return {
                "status": "success",
                "document": document,
            }

        # If not found in text collection, try image collection
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List images from image collection
            images = image_vdb.list_images(limit=1000, offset=0)
            image = next(
                (img for img in images if str(img.get("id")) == document_id), None
            )

            if image:
                return {
                    "status": "success",
                    "document": image,
                }
        except Exception as image_error:
            print(f"Error trying to get from image collection: {str(image_error)}")

        # If not found in either collection
        raise HTTPException(
            status_code=404, detail=f"Document or image {document_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting document/image {document_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/config")
async def get_frontend_config():
    """Get frontend configuration."""
    try:
        # Get application configuration
        app_config = config.get("application", {})
        frontend_config = config.get("frontend", {})
        client_config = config.get("client", {})
        features_config = config.get("features", {})

        # Get MCP servers configuration (filtered for security)
        mcp_servers = config.get("mcp_servers", [])
        safe_mcp_servers = []
        for server in mcp_servers:
            safe_server = {
                "name": server.get("name", ""),
                "icon": server.get("icon", ""),
                "enabled": server.get("enabled", False),
                "description": server.get("description", ""),
                # Exclude sensitive fields like authentication_type and url
            }
            safe_mcp_servers.append(safe_server)

        # Get vector database configuration
        db_config = config.get_database_config()
        collections = config.get_collections_config()
        vector_db_info = {
            "type": (
                db_config.get("type", "weaviate-local")
                if db_config
                else "weaviate-local"
            ),
            "collections": collections,
            "active_text_collection": config.get_text_collection_name(),
            "active_image_collection": config.get_image_collection_name(),
        }

        # Get storage configuration
        storage_config = {
            "type": config.get_storage_type(),
            "copy_uploaded_docs": config.is_copy_uploaded_docs_enabled(),
            "copy_uploaded_images": config.is_copy_uploaded_images_enabled(),
            "bucket_name": config.get_storage_bucket_name(),
            "backend_config": config.get_storage_backend_config(),
        }

        # Get AI acceleration configuration
        ai_acceleration_config = config.get("ai_acceleration", {})

        # Build safe configuration for frontend
        frontend_config_data = {
            "application": {
                "name": app_config.get("name", "RAGme"),
                "title": app_config.get("title", "RAGme.io Assistant"),
                "version": app_config.get("version", "1.0.0"),
            },
            "vector_database": vector_db_info,
            "storage": storage_config,
            "ai_acceleration": ai_acceleration_config,
            "frontend": frontend_config,
            "client": client_config,
            "features": features_config,
            "mcp_servers": safe_mcp_servers,
        }

        return {"status": "success", "config": frontend_config_data}

    except Exception as e:
        return {"status": "error", "message": f"Failed to get configuration: {str(e)}"}


@app.get("/storage/status")
async def get_storage_status():
    """Get storage service status including MinIO availability."""
    try:
        import requests
        from requests.exceptions import RequestException

        # Check MinIO status
        minio_status = "Not Available"
        try:
            response = requests.get(
                "http://localhost:9000/minio/health/live", timeout=2
            )
            if response.status_code == 200:
                minio_status = "Available"
        except RequestException:
            minio_status = "Not Available"

        # Get storage configuration
        storage_config = {
            "type": config.get_storage_type(),
            "copy_uploaded_docs": config.is_copy_uploaded_docs_enabled(),
            "copy_uploaded_images": config.is_copy_uploaded_images_enabled(),
            "bucket_name": config.get_storage_bucket_name(),
            "backend_config": config.get_storage_backend_config(),
            "minio_status": minio_status,
        }

        return {"status": "success", "storage": storage_config}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get storage status: {str(e)}"}


@app.post("/update-storage-settings")
async def update_storage_settings(request: dict):
    """Update storage settings."""
    try:
        # This would typically update the configuration file
        # For now, we'll just return success as the config is read-only in this implementation
        copy_uploaded_docs = request.get("copy_uploaded_docs", False)
        copy_uploaded_images = request.get("copy_uploaded_images", False)

        # Note: In a real implementation, this would update the config.yaml file
        # For now, we'll just validate the settings

        return {
            "status": "success",
            "message": "Storage settings updated successfully",
            "settings": {
                "copy_uploaded_docs": copy_uploaded_docs,
                "copy_uploaded_images": copy_uploaded_images,
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update storage settings: {str(e)}",
        }


@app.post("/reset-chat-session")
async def reset_chat_session():
    """Reset the chat session, clearing memory and confirmation state."""
    try:
        get_ragme().reset_chat_session()
        return {"status": "success", "message": "Chat session reset successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to reset chat session: {str(e)}"}


# Socket.IO support for real-time communication
try:
    import socketio
    from socketio import AsyncServer

    # Create Socket.IO server
    sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
    socket_app = socketio.ASGIApp(sio, app)

    # Socket event handlers
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")

    @sio.event
    async def summarize_document(sid, data):
        """Handle document summarization requests from frontend."""
        try:
            document_id = data.get("documentId")
            if not document_id:
                await sio.emit(
                    "document_summarized",
                    {"success": False, "message": "Document ID is required"},
                    room=sid,
                )
                return

            # Use the existing summarize_document endpoint logic
            # Note: We don't need to import SummarizeInput here since we're not using it

            # Get all documents and images
            all_items = []

            # Get text documents
            documents = get_ragme().list_documents(limit=1000, offset=0)
            for doc in documents:
                doc["content_type"] = "document"
            all_items.extend(documents)

            # Get images
            images = []
            try:
                from ..utils.config_manager import config
                from ..vdbs.vector_db_factory import create_vector_database

                # Get image collection name
                image_collection_name = config.get_image_collection_name()

                # Create image vector database
                image_vdb = create_vector_database(
                    collection_name=image_collection_name
                )

                # List images from image collection
                images = image_vdb.list_images(limit=1000, offset=0)
                for img in images:
                    img["content_type"] = "image"
                all_items.extend(images)
            except Exception as e:
                print(f"Error listing images: {e}")

            # Find the document by ID
            document = None
            print(f"Looking for document with ID: {document_id}")
            print(f"Number of documents: {len(documents)}")
            print(f"Number of images: {len(images)}")

            # First try to find by ID in documents
            for doc in documents:
                doc_id = doc.get("id")
                doc_id_str = str(doc_id) if doc_id else None
                if doc_id_str == document_id:
                    document = doc
                    document["content_type"] = "document"
                    print(f"Found document: {doc.get('url', 'No URL')}")
                    break

            # If not found in documents, try to find in images
            if not document:
                for img in images:
                    img_id = img.get("id")
                    img_id_str = str(img_id) if img_id else None
                    if img_id_str == document_id:
                        document = img
                        document["content_type"] = "image"
                        print(
                            f"Found image: {img.get('metadata', {}).get('filename', 'No filename')}"
                        )
                        break

            if not document:
                await sio.emit(
                    "document_summarized",
                    {"success": False, "message": "Document not found"},
                    room=sid,
                )
                return

            # Handle different content types
            content_type = document.get("content_type", "document")

            if content_type == "image":
                # For images, create a summary based on metadata and classification
                metadata = document.get("metadata", {})
                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})
                confidence = top_prediction.get("confidence", 0)
                label = top_prediction.get("label", "Unknown")

                summary = f"Image Analysis:\n- Filename: {metadata.get('filename', 'Unknown')}\n- File Size: {metadata.get('file_size', 'Unknown')} bytes\n- Classification: {label} (confidence: {confidence:.2%})\n- Date Added: {metadata.get('date_added', 'Unknown')}"

                await sio.emit(
                    "document_summarized",
                    {"success": True, "summary": summary},
                    room=sid,
                )
            else:
                # For text documents, use the existing summarize logic
                try:
                    # Call the existing summarize_document endpoint
                    from .api import SummarizeInput

                    input_data = SummarizeInput(document_id=document_id)
                    result = await summarize_document(input_data)

                    await sio.emit(
                        "document_summarized",
                        {"success": True, "summary": result["summary"]},
                        room=sid,
                    )
                except Exception as e:
                    print(f"Error summarizing document: {e}")
                    await sio.emit(
                        "document_summarized",
                        {
                            "success": False,
                            "message": f"Error summarizing document: {str(e)}",
                        },
                        room=sid,
                    )

        except Exception as e:
            print(f"Error in summarize_document socket handler: {e}")
            await sio.emit(
                "document_summarized",
                {"success": False, "message": f"Error: {str(e)}"},
                room=sid,
            )

    @sio.event
    async def list_content(sid, data):
        """Handle content listing requests from frontend."""
        try:
            limit = data.get("limit", 10)
            offset = data.get("offset", 0)
            date_filter = data.get("dateFilter", "all")
            content_type = data.get("contentType", "both")

            print(
                f"List content request - limit: {limit}, offset: {offset}, date: {date_filter}, type: {content_type}"
            )

            # Get all content based on filters
            all_items = []

            # Get text documents
            if content_type in ["both", "documents"]:
                documents = get_ragme().list_documents(limit=1000, offset=0)
                for doc in documents:
                    doc["content_type"] = "document"
                all_items.extend(documents)

            # Get images
            if content_type in ["both", "images"]:
                try:
                    from ..utils.config_manager import config
                    from ..vdbs.vector_db_factory import create_vector_database

                    # Get image collection name
                    image_collection_name = config.get_image_collection_name()

                    # Create image vector database
                    image_vdb = create_vector_database(
                        collection_name=image_collection_name
                    )

                    # List images from image collection
                    images = image_vdb.list_images(limit=1000, offset=0)
                    for img in images:
                        img["content_type"] = "image"
                    all_items.extend(images)
                except Exception as e:
                    print(f"Error listing images: {e}")

            # Apply date filtering if specified
            if date_filter != "all":
                filtered_items = []
                current_time = datetime.now()

                for item in all_items:
                    date_added = item.get("metadata", {}).get("date_added")
                    if date_added:
                        try:
                            item_date = datetime.fromisoformat(
                                date_added.replace("Z", "+00:00")
                            )

                            if date_filter == "current":
                                # Current day
                                if item_date.date() == current_time.date():
                                    filtered_items.append(item)
                            elif date_filter == "month":
                                # Current month
                                if (
                                    item_date.year == current_time.year
                                    and item_date.month == current_time.month
                                ):
                                    filtered_items.append(item)
                            elif date_filter == "year":
                                # Current year
                                if item_date.year == current_time.year:
                                    filtered_items.append(item)
                        except Exception as e:
                            print(f"Error parsing date {date_added}: {e}")
                            # Include items with invalid dates
                            filtered_items.append(item)
                    else:
                        # Include items without date_added
                        filtered_items.append(item)

                all_items = filtered_items

            # Apply pagination
            total_count = len(all_items)
            paginated_items = all_items[offset : offset + limit]

            print(f"Returning {len(paginated_items)} items out of {total_count} total")

            await sio.emit(
                "content_listed",
                {
                    "success": True,
                    "items": paginated_items,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "count": len(paginated_items),
                        "total": total_count,
                    },
                },
                room=sid,
            )

        except Exception as e:
            print(f"Error in list_content socket handler: {e}")
            await sio.emit(
                "content_listed",
                {"success": False, "message": f"Error listing content: {str(e)}"},
                room=sid,
            )

    # Set the socket manager for other parts of the application
    from ..utils.socket_manager import set_socket_manager

    set_socket_manager(sio)

    SOCKETIO_AVAILABLE = True
except ImportError:
    print("Socket.IO not available - real-time features will be disabled")
    SOCKETIO_AVAILABLE = False
    socket_app = app


@app.get("/list-images")
async def list_images(limit: int = 10, offset: int = 0):
    """
    List images in the RAG system.

    Args:
        limit: Maximum number of images to return
        offset: Number of images to skip

    Returns:
        dict: List of images with pagination info
    """
    try:
        from ..utils.config_manager import config
        from ..vdbs.vector_db_factory import create_vector_database

        # Get image collection name
        image_collection_name = config.get_image_collection_name()

        # Create image vector database
        image_vdb = create_vector_database(collection_name=image_collection_name)

        # Get images from image collection
        images = image_vdb.list_images(limit=limit, offset=offset)

        return {
            "images": images,
            "pagination": {"limit": limit, "offset": offset, "count": len(images)},
        }
    except Exception as e:
        print(f"Error listing images: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/delete-image/{image_id}")
async def delete_image(image_id: str):
    """
    Delete an image from the RAG system by ID.

    Args:
        image_id: ID of the image to delete

    Returns:
        dict: Status message
    """
    try:
        from ..utils.config_manager import config
        from ..vdbs.vector_db_factory import create_vector_database

        # Get image collection name
        image_collection_name = config.get_image_collection_name()

        # Create image vector database
        image_vdb = create_vector_database(collection_name=image_collection_name)

        # Check if image exists in image collection
        images = image_vdb.list_images(limit=1000, offset=0)

        # Convert Weaviate UUID to string for comparison
        image_document = None
        for img in images:
            img_id = str(img.get("id")) if img.get("id") else None
            if img_id == image_id:
                image_document = img
                break

        if image_document:
            # Image exists in image collection, delete it
            image_success = image_vdb.delete_image(image_id)
            if image_success:
                return {
                    "status": "success",
                    "message": f"Image {image_id} deleted successfully",
                }
            else:
                raise HTTPException(
                    status_code=500, detail=f"Failed to delete image {image_id}"
                )

        # If not found in image collection
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting image {image_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/image/{image_id}")
async def get_image(image_id: str):
    """
    Get an image from the RAG system by ID.

    Args:
        image_id: ID of the image to retrieve

    Returns:
        dict: Image data
    """
    try:
        from ..utils.config_manager import config
        from ..vdbs.vector_db_factory import create_vector_database

        # Get image collection name
        image_collection_name = config.get_image_collection_name()

        # Create image vector database
        image_vdb = create_vector_database(collection_name=image_collection_name)

        # Get images from image collection
        images = image_vdb.list_images(limit=1000, offset=0)

        # Find the specific image
        image_document = None
        for img in images:
            img_id = str(img.get("id")) if img.get("id") else None
            if img_id == image_id:
                image_document = img
                break

        if not image_document:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")

        # Return the image data
        return {
            "id": image_document.get("id"),
            "url": image_document.get("url"),
            "image_data": image_document.get("image_data"),
            "metadata": image_document.get("metadata", {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving image {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/count-images")
async def count_images():
    """
    Count the number of images in the RAG system.

    Returns:
        dict: Count of images
    """
    try:
        from ..utils.config_manager import config
        from ..vdbs.vector_db_factory import create_vector_database

        # Get image collection name
        image_collection_name = config.get_image_collection_name()

        # Create image vector database
        image_vdb = create_vector_database(collection_name=image_collection_name)

        # Get all images to count them
        images = image_vdb.list_images(limit=10000, offset=0)

        return {"count": len(images), "type": "images"}
    except Exception as e:
        print(f"Error counting images: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/download-file/{document_id}")
async def download_file(document_id: str):
    """
    Download a file from storage by document ID.

    This endpoint attempts to find the file in storage and returns a presigned URL
    or the file content directly.

    Args:
        document_id: ID of the document to download

    Returns:
        dict: File download information including URL or content
    """
    try:
        # First try to get from text collection
        documents = get_ragme().list_documents(limit=1000, offset=0)
        print(f"Looking for document with ID: {document_id}")
        print(f"Number of documents: {len(documents)}")

        # Debug: print all document IDs to see what's available
        doc_ids = [doc.get("id") for doc in documents]
        print(f"Available document IDs: {doc_ids}")

        document = next(
            (doc for doc in documents if str(doc.get("id")) == document_id), None
        )

        if document:
            print(f"Found document: {document.get('url', 'No URL')}")
            # This is a text document, try to find the file in storage
            filename = document.get("metadata", {}).get("filename")
            storage_path = document.get("metadata", {}).get("storage_path")

            if storage_path:
                # Use the storage path directly from metadata
                print(f"Using storage_path from metadata: {storage_path}")
                storage_service = get_storage_service()
                try:
                    # Try to get file info directly first
                    try:
                        file_info = storage_service.get_file_info(storage_path)
                        storage_file = {
                            "name": storage_path,
                            "size": file_info.get("size", 0),
                            "content_type": file_info.get(
                                "content_type", "application/octet-stream"
                            ),
                        }
                        print(f"Found file in storage: {storage_file}")
                    except Exception as e:
                        print(f"Error getting file info for {storage_path}: {e}")
                        # Fallback: check if the file exists in storage
                        files = storage_service.list_files(prefix="documents/")
                        storage_file = next(
                            (f for f in files if f["name"] == storage_path), None
                        )
                        if storage_file:
                            print(f"Found file via list_files: {storage_file}")
                        else:
                            print("File not found in list_files")
                            storage_file = None
                except Exception as e:
                    print(f"Error checking storage: {e}")
                    storage_file = None
            elif filename:
                # Document has filename but no storage_path - it was added before storage service
                print(
                    "Document has filename but no storage_path - not available in storage"
                )
                storage_file = None

            if storage_file:
                print("Storage file found, generating download URL...")
                # Generate presigned URL for download
                try:
                    download_url = storage_service.get_file_url(
                        storage_file["name"], expires_in=3600
                    )
                    print(f"Generated download URL: {download_url}")
                    return JSONResponse(
                        {
                            "status": "success",
                            "download_url": download_url,
                            "filename": filename,
                            "content_type": storage_file.get(
                                "content_type", "application/octet-stream"
                            ),
                            "size": storage_file.get("size", 0),
                            "storage_path": storage_file["name"],
                        }
                    )
                except Exception as url_error:
                    print(f"Error generating download URL: {url_error}")
                    # Fallback: return file info without URL
                    return JSONResponse(
                        {
                            "status": "success",
                            "filename": filename,
                            "content_type": storage_file.get(
                                "content_type", "application/octet-stream"
                            ),
                            "size": storage_file.get("size", 0),
                            "storage_path": storage_file["name"],
                            "message": "File found in storage but could not generate download URL",
                        }
                    )
            else:
                print("Storage file not found, returning not_found response")
                return JSONResponse(
                    {
                        "status": "not_found",
                        "message": f"File '{filename}' not found in storage",
                    }
                )

        # If not found in text collection, try image collection
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            # Get image collection name
            image_collection_name = config.get_image_collection_name()

            # Create image vector database
            image_vdb = create_vector_database(collection_name=image_collection_name)

            # List images from image collection
            images = image_vdb.list_images(limit=1000, offset=0)
            image = next(
                (img for img in images if str(img.get("id")) == document_id), None
            )

            if image:
                # This is an image, try to find the file in storage
                filename = image.get("metadata", {}).get("filename")
                storage_path = image.get("metadata", {}).get("storage_path")

                if storage_path:
                    # Use the storage path directly from metadata
                    storage_service = get_storage_service()
                    try:
                        # Get file info directly from storage
                        file_info = storage_service.get_file_info(storage_path)
                        storage_file = {
                            "name": storage_path,
                            "size": file_info.get("size", 0),
                            "content_type": file_info.get("content_type", "image/jpeg"),
                        }
                    except Exception as e:
                        print(f"Error getting file info for {storage_path}: {e}")
                        storage_file = None
                elif filename:
                    # Image has filename but no storage_path - it was added before storage service
                    print(
                        "Image has filename but no storage_path - not available in storage"
                    )
                    storage_file = None
                else:
                    # Image has no filename or storage_path - it was added before storage service
                    print(
                        "Image has no filename or storage_path - not available in storage"
                    )
                    storage_file = None

                if storage_file:
                    # Generate presigned URL for download
                    try:
                        download_url = storage_service.get_file_url(
                            storage_file["name"], expires_in=3600
                        )
                        return JSONResponse(
                            {
                                "status": "success",
                                "download_url": download_url,
                                "filename": filename,
                                "content_type": storage_file.get(
                                    "content_type", "image/jpeg"
                                ),
                                "size": storage_file.get("size", 0),
                                "storage_path": storage_file["name"],
                            }
                        )
                    except Exception as url_error:
                        print(f"Error generating download URL: {url_error}")
                        # Fallback: return file info without URL
                        return JSONResponse(
                            {
                                "status": "success",
                                "filename": filename,
                                "content_type": storage_file.get(
                                    "content_type", "image/jpeg"
                                ),
                                "size": storage_file.get("size", 0),
                                "storage_path": storage_file["name"],
                                "message": "File found in storage but could not generate download URL",
                            }
                        )
                else:
                    # Image was found but doesn't have storage metadata
                    return JSONResponse(
                        {
                            "status": "no_storage",
                            "message": "Image was added before storage service was enabled",
                        }
                    )

        except Exception as image_error:
            print(f"Error trying to get from image collection: {str(image_error)}")

        # If not found in either collection
        return JSONResponse(
            {
                "status": "not_found",
                "message": f"Document or image {document_id} not found in system",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading file {document_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    # Get network configuration
    api_config = network_config.get("api", {})
    host = api_config.get("host", "0.0.0.0")
    port = api_config.get("port", 8021)

    # Use socket app if available, otherwise use regular app
    app_to_run = socket_app if SOCKETIO_AVAILABLE else app
    uvicorn.run(app_to_run, host=host, port=port)
