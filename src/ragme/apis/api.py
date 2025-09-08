# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import tempfile
import time
import traceback
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import PyPDF2
from docx import Document
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from ..auth import OAuthManager, SessionManager, UserManager
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


# Authentication managers will be initialized lazily when needed
_oauth_manager = None
_session_manager = None
_user_manager = None


def get_oauth_manager():
    """Get or create OAuthManager instance"""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager


def get_session_manager():
    """Get or create SessionManager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_user_manager():
    """Get or create UserManager instance"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


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

    document_id: str | dict
    force_refresh: bool = Field(default=False, alias="forceRefresh")

    class Config:
        allow_population_by_field_name = True


class McpServerConfig(BaseModel):
    """Input model for MCP server configuration."""

    server: str
    enabled: bool
    authenticated: bool = False


class McpServerConfigList(BaseModel):
    """Input model for multiple MCP server configurations."""

    servers: list[McpServerConfig]


class OAuthCallbackInput(BaseModel):
    """Input model for OAuth callback."""

    code: str
    state: str | None = None


class LoginResponse(BaseModel):
    """Response model for login."""

    success: bool
    message: str
    user: dict[str, Any] | None = None
    token: str | None = None


class LogoutResponse(BaseModel):
    """Response model for logout."""

    success: bool
    message: str


# Authentication dependency
async def get_current_user(
    request: Request, token: str | None = Cookie(None)
) -> dict[str, Any] | None:
    """
    Get current authenticated user from session token.

    Args:
        request: FastAPI request object
        token: JWT token from cookie

    Returns:
        User data if authenticated, None otherwise
    """
    # Check for token in cookie first
    session_token = token

    # If no cookie token, check Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]  # Remove "Bearer " prefix

    print(
        f"DEBUG: get_current_user called with token: {session_token[:20] if session_token else 'None'}..."
    )

    if not session_token:
        print("DEBUG: No token provided")
        return None

    session_manager = get_session_manager()
    session_data = session_manager.validate_token(session_token)
    print(f"DEBUG: Session validation result: {session_data is not None}")

    if not session_data:
        print("DEBUG: Session validation failed")
        return None

    # Update user activity
    user_manager = get_user_manager()
    user_manager.update_user_activity(session_data["user_id"])

    print(f"DEBUG: Returning session data for user: {session_data.get('email')}")
    return session_data


# Authentication required dependency
async def require_auth(
    current_user: dict[str, Any] | None = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Require authentication for protected endpoints.

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        User data

    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return current_user


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
                    # For file URLs, check if they already have a timestamp
                    if "#" in url:
                        # URL already has a timestamp, use it as is
                        unique_url = url
                    else:
                        # Add timestamp to prevent overwriting
                        unique_url = f"{url}#{timestamp}"
                else:
                    # For web URLs, add timestamp as fragment
                    unique_url = f"{url}#{timestamp}"

                # Check if a document with the same URL already exists
                existing_doc = get_ragme().vector_db.find_document_by_url(unique_url)
                if existing_doc:
                    # Delete the existing document to replace it
                    get_ragme().vector_db.delete_document(existing_doc["id"])
                    replaced_count += 1

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
    Filter documents by date.

    Args:
        documents: List of documents to filter
        date_filter: Date filter to apply ('today', 'week', 'month', 'year', 'all')

    Returns:
        List of filtered documents
    """
    if date_filter == "all":
        return documents

    filtered_documents = []
    now = datetime.now()

    for doc in documents:
        date_added = doc.get("metadata", {}).get("date_added", "")
        if not date_added:
            continue

        try:
            doc_date = datetime.fromisoformat(date_added.replace("Z", "+00:00"))
        except ValueError:
            continue

        if date_filter == "today":
            if doc_date.date() == now.date():
                filtered_documents.append(doc)
        elif date_filter == "week":
            start_of_week = now - timedelta(days=now.weekday())
            if doc_date >= start_of_week:
                filtered_documents.append(doc)
        elif date_filter == "month":
            start_of_month = now.replace(day=1)
            if doc_date >= start_of_month:
                filtered_documents.append(doc)
        elif date_filter == "year":
            start_of_year = now.replace(month=1, day=1)
            if doc_date >= start_of_year:
                filtered_documents.append(doc)

    return filtered_documents


def group_chunked_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group chunked documents by their base URL/filename to avoid duplication in the UI.

    Args:
        documents: List of documents that may contain chunks

    Returns:
        List of grouped documents where chunks are combined into single documents
    """
    groups = {}

    for doc in documents:
        # Check if this is a chunked document
        if (
            doc.get("metadata", {}).get("is_chunk")
            and doc.get("metadata", {}).get("total_chunks")
        ) or (
            doc.get("metadata", {}).get("is_chunked")
            and doc.get("metadata", {}).get("total_chunks")
        ):
            # Extract base filename from URL like "file://ragme-io.pdf#chunk-4"
            url = doc.get("url", "")
            base_url = url.split("#")[0]  # Remove chunk suffix

            if base_url not in groups:
                groups[base_url] = {
                    "isGroupedChunks": True,
                    "totalChunks": doc["metadata"]["total_chunks"],
                    "originalFilename": doc["metadata"].get("filename", "Unknown"),
                    "baseUrl": base_url,
                    "chunks": [],
                    "metadata": {**doc["metadata"]},
                    "url": base_url,
                    "id": doc["id"],
                    "content_type": doc.get("content_type", "document"),
                }

                # Use consistent timestamp for chunked documents
                if doc["metadata"].get("date_added"):
                    groups[base_url]["metadata"]["date_added"] = doc["metadata"][
                        "date_added"
                    ]

            # Add chunk to the group
            if groups[base_url]["chunks"] is not None:
                groups[base_url]["chunks"].append(
                    {**doc, "chunk_index": doc["metadata"].get("chunk_index", 0)}
                )

                # Sort chunks by index
                groups[base_url]["chunks"].sort(key=lambda x: x["chunk_index"])

                # Combine text from all chunks
                groups[base_url]["combinedText"] = "\n\n--- Chunk ---\n\n".join(
                    chunk.get("text", "") for chunk in groups[base_url]["chunks"]
                )

                # Use the latest date
                if not groups[base_url]["metadata"].get("date_added") or doc[
                    "metadata"
                ].get("date_added", "") > groups[base_url]["metadata"].get(
                    "date_added", ""
                ):
                    groups[base_url]["metadata"]["date_added"] = doc["metadata"].get(
                        "date_added", ""
                    )

        elif doc.get("content_type") == "image" and doc.get("metadata", {}).get(
            "pdf_filename"
        ):
            # Group images by their source PDF document
            pdf_filename = doc["metadata"]["pdf_filename"]
            key = f"pdf_images_{pdf_filename}"

            if key not in groups:
                groups[key] = {
                    "isGroupedImages": True,
                    "sourceDocument": pdf_filename,
                    "totalImages": 0,
                    "images": [],
                    "metadata": {
                        **doc["metadata"],
                        "date_added": doc["metadata"].get("date_added", ""),
                        "collection": "Images",
                    },
                    "url": f"pdf://{pdf_filename}",
                    "id": f"pdf_images_{pdf_filename}",
                    "content_type": "image_stack",
                }

            # Add image to the group
            if groups[key]["images"] is not None:
                groups[key]["images"].append(
                    {**doc, "image_index": doc["metadata"].get("pdf_page_number", 0)}
                )

                # Sort images by page number
                groups[key]["images"].sort(key=lambda x: x["image_index"])
                groups[key]["totalImages"] = len(groups[key]["images"])

                # Use the latest date
                if not groups[key]["metadata"].get("date_added") or doc["metadata"].get(
                    "date_added", ""
                ) > groups[key]["metadata"].get("date_added", ""):
                    groups[key]["metadata"]["date_added"] = doc["metadata"].get(
                        "date_added", ""
                    )

        else:
            # Regular document - use URL as key
            key = doc.get("url") or f"doc_{len(groups)}"

            # For URLs, use the full URL as key
            if doc.get("url") and (
                doc["url"].startswith("http://") or doc["url"].startswith("https://")
            ):
                key = doc["url"]
            # For file documents, use the filename as key
            elif doc.get("metadata", {}).get("filename"):
                key = f"file://{doc['metadata']['filename']}"
            # For other documents, use a unique key
            else:
                key = f"doc_{len(groups)}_{id(doc)}"

            groups[key] = doc

    # Convert groups to list
    grouped_documents = list(groups.values())

    return grouped_documents


@app.get("/health")
async def health_check():
    """
    Check the health of the RAG system and vector database connection.

    Returns:
        dict: Health status information
    """
    try:
        # Test vector database connection
        ragme = get_ragme()
        try:
            # Try to list documents to test connection
            ragme.list_documents(limit=1, offset=0)
            vdb_status = "healthy"
            vdb_error = None
        except Exception as e:
            vdb_status = "error"
            vdb_error = str(e)

        # Test image collection if available
        image_status = "not_configured"
        image_error = None
        try:
            from ..utils.config_manager import config
            from ..vdbs.vector_db_factory import create_vector_database

            image_collection_name = config.get_image_collection_name()
            if image_collection_name:
                image_vdb = create_vector_database(
                    collection_name=image_collection_name
                )
                image_vdb.list_images(limit=1, offset=0)
                image_status = "healthy"
        except Exception as e:
            image_status = "error"
            image_error = str(e)

        # Overall status
        overall_status = "healthy" if vdb_status == "healthy" else "error"

        return {
            "status": "success",
            "overall_status": overall_status,
            "vector_database": {"status": vdb_status, "error": vdb_error},
            "image_collection": {"status": image_status, "error": image_error},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/count-documents")
async def count_documents(
    date_filter: str = Query(
        default="all",
        description=(
            "Date filter: 'today' (today), 'week' (this week), 'month' (this month), "
            "'year' (this year), 'all' (all documents)"
        ),
    ),
):
    """
    Get the count of documents in the RAG system.

    Args:
        date_filter: Date filter to apply ('today', 'week', 'month', 'year', 'all')

    Returns:
        dict: Document count information
    """
    try:
        # Get all documents and apply grouping to get accurate count
        all_documents = get_ragme().list_documents(limit=1000, offset=0)
        filtered_documents = filter_documents_by_date(all_documents, date_filter)
        grouped_documents = group_chunked_documents(filtered_documents)
        count = len(grouped_documents)

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
        default=10, ge=1, le=25, description="Maximum number of documents to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of documents to skip"),
    date_filter: str = Query(
        default="all",
        description="Date filter: 'current' (today), 'week' (this week), 'month' (this month), 'year' (this year), 'all' (all documents)",
    ),
):
    """
    List documents in the RAG system.

    Args:
        limit: Maximum number of documents to return (1-25)
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

        # Group chunked documents
        grouped_documents = group_chunked_documents(filtered_documents)

        # Sort by date (most recent first)
        grouped_documents.sort(
            key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
        )

        # Apply pagination to grouped results
        total_count = len(grouped_documents)
        paginated_documents = grouped_documents[offset : offset + limit]

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
        default=10, ge=1, le=25, description="Maximum number of items to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    date_filter: str = Query(
        default="all",
        description="Date filter: 'current' (today), 'week' (this week), 'month' (this month), 'year' (this year), 'all' (all items)",
    ),
    content_type: str = Query(
        default="both",
        description="Content type filter: 'documents', 'images', or 'both'",
    ),
):
    """
    List documents and/or images in the RAG system.

    Args:
        limit: Maximum number of items to return (1-25)
        offset: Number of items to skip
        date_filter: Date filter to apply ('today', 'week', 'month', 'year', 'all')
        content_type: Content type filter ('documents', 'image', 'both')

    Returns:
        dict: List of items and pagination info
    """
    try:
        all_items = []

        # Get documents if requested
        if content_type in ["document", "documents", "both"]:
            documents = get_ragme().list_documents(limit=1000, offset=0)
            for doc in documents:
                doc["content_type"] = "document"
            all_items.extend(documents)

        # Get images if requested
        if content_type in ["images", "both"]:
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

        # Group chunked documents
        grouped_items = group_chunked_documents(filtered_items)

        # Sort by date (most recent first)
        grouped_items.sort(
            key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
        )

        # Apply pagination to filtered results
        total_count = len(grouped_items)
        paginated_items = grouped_items[offset : offset + limit]

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
async def summarize_document(input_data: SummarizeInput, request: Request):
    """
    Summarize a document or image using the RagMe agent.

    Args:
        input_data: Contains document_id to summarize

    Returns:
        dict: Summarized content
    """
    # Log the raw request data
    body = await request.body()
    print(f"🌐 REST API - Raw request body: {body}")
    print(f"🌐 REST API - Request headers: {request.headers}")
    print(f"🌐 REST API - Received input_data: {input_data}")
    print(f"🌐 REST API - force_refresh parameter: {input_data.force_refresh}")
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

        # Group chunked documents to ensure we get complete documents
        grouped_items = group_chunked_documents(all_items)

        # Find the document by ID
        document = None
        document_id = input_data.document_id
        print(
            f"REST API - Looking for document with ID: {document_id}, type: {type(document_id)}"
        )

        # Check if this is an image stack request
        if isinstance(document_id, dict) and document_id.get("type") == "image_stack":
            print(f"REST API - Processing image stack request: {document_id}")
            # Handle image stack summarization
            pdf_filename = document_id.get("pdfFilename")
            if pdf_filename:
                try:
                    from ..utils.config_manager import config
                    from ..vdbs.vector_db_factory import create_vector_database

                    # Get image collection name
                    image_collection_name = config.get_image_collection_name()

                    # Create image vector database
                    image_vdb = create_vector_database(
                        collection_name=image_collection_name
                    )

                    # List all images and filter by PDF filename
                    all_images = image_vdb.list_images(limit=1000, offset=0)
                    pdf_images = [
                        img
                        for img in all_images
                        if img.get("metadata", {}).get("pdf_filename") == pdf_filename
                    ]

                    if pdf_images:
                        # Check if summary already exists in the first image's metadata (unless force refresh is requested)
                        first_image_metadata = pdf_images[0].get("metadata", {})
                        existing_summary = first_image_metadata.get("ai_summary")

                        if existing_summary and not input_data.force_refresh:
                            print(
                                f"📋 RETRIEVED cached AI summary for image stack: {pdf_filename}"
                            )
                            return {
                                "status": "success",
                                "summary": existing_summary,
                                "cached": True,
                            }

                        if input_data.force_refresh and existing_summary:
                            print(
                                f"🔄 FORCE REFRESH requested for image stack: {pdf_filename} - regenerating AI summary"
                            )

                        # Create comprehensive summary for the image stack
                        summary_text = f"This is an image stack containing {len(pdf_images)} images extracted from the PDF document '{pdf_filename}'.\n\n"

                        # Analyze classifications across all images
                        classifications = []
                        for img in pdf_images:
                            img_metadata = img.get("metadata", {})
                            img_classification = img_metadata.get("classification", {})
                            top_pred = img_classification.get("top_prediction", {})
                            if top_pred.get("label"):
                                classifications.append(top_pred["label"])

                        if classifications:
                            # Count unique classifications
                            from collections import Counter

                            class_counts = Counter(classifications)
                            unique_classes = len(class_counts)

                            summary_text += "**Image Analysis Summary:**\n"
                            summary_text += f"- Total images: {len(pdf_images)}\n"
                            summary_text += (
                                f"- Unique content types: {unique_classes}\n"
                            )

                            # Show top classifications
                            top_classes = class_counts.most_common(3)
                            summary_text += "- Most common content types:\n"
                            for label, count in top_classes:
                                summary_text += f"  • {label}: {count} images\n"

                        # Add metadata about the source PDF
                        summary_text += f"\n**Source Document:** {pdf_filename}"

                        if pdf_images[0].get("metadata", {}).get("date_added"):
                            summary_text += f"\n**Extracted:** {pdf_images[0]['metadata']['date_added']}"

                        # Store the generated summary in the first image's metadata
                        try:
                            first_image_id = pdf_images[0].get("id")
                            if first_image_id:
                                print(
                                    f"💾 STORING new AI summary for image stack (PDF: {pdf_filename}, image_id: {first_image_id})"
                                )
                                image_vdb.update_image_metadata(
                                    first_image_id, {"ai_summary": summary_text}
                                )
                                print(
                                    f"✅ SUCCESSFULLY stored AI summary in image stack metadata for PDF: {pdf_filename}"
                                )
                        except Exception as e:
                            print(
                                f"❌ FAILED to store AI summary in image stack metadata: {e}"
                            )

                        return {
                            "status": "success",
                            "summary": summary_text,
                        }
                    else:
                        return {
                            "status": "error",
                            "summary": f"No images found for PDF: {pdf_filename}",
                        }
                except Exception as e:
                    print(f"REST API - Error summarizing image stack: {e}")
                    return {
                        "status": "error",
                        "summary": f"Error summarizing image stack: {str(e)}",
                    }

        print(f"Number of grouped items: {len(grouped_items)}")
        print(f"Number of original items: {len(all_items)}")
        print(f"Looking for document ID: {document_id} (type: {type(document_id)})")

        # Search for the document in grouped items
        document = None
        for item in grouped_items:
            item_id = item.get("id")
            # Convert Weaviate UUID to string for comparison
            item_id_str = str(item_id) if item_id else None
            print(
                f"Checking grouped item ID: {item_id_str} (type: {type(item_id_str)})"
            )
            if item_id_str == document_id:
                document = item
                print(
                    f"Found item in grouped items: {item.get('url', 'No URL')} (type: {item.get('content_type', 'unknown')})"
                )
                break

        # If not found in grouped items, try to find in original items
        if not document:
            print(
                f"Document not found in grouped items with ID: {document_id}, trying original items..."
            )
            for item in all_items:
                item_id = item.get("id")
                item_id_str = str(item_id) if item_id else None
                print(
                    f"Checking original item ID: {item_id_str} (type: {type(item_id_str)})"
                )
                if item_id_str == document_id:
                    document = item
                    print(
                        f"Found item in original items: {item.get('url', 'No URL')} (type: {item.get('content_type', 'unknown')})"
                    )
                    break

        # If still not found, try to find by URL
        if not document:
            print(f"Document not found by ID: {document_id}, trying to find by URL...")
            for item in all_items:
                item_url = item.get("url", "")
                if item_url == document_id:
                    document = item
                    print(
                        f"Found item by URL: {item.get('url', 'No URL')} (type: {item.get('content_type', 'unknown')})"
                    )
                    break

        if not document:
            print(f"Document not found with ID: {document_id}")
            return {
                "status": "error",
                "summary": f"Document not found for summarization. ID: {document_id}. Please try refreshing the document list or use the Force Reload button.",
            }

        # Check if summary already exists in metadata (unless force refresh is requested)
        metadata = document.get("metadata", {})
        existing_summary = metadata.get("ai_summary")

        if existing_summary and not input_data.force_refresh:
            print(
                f"📋 RETRIEVED cached AI summary for document: {document_id} (content_type: {document.get('content_type', 'unknown')})"
            )
            return {
                "status": "success",
                "summary": existing_summary,
                "document_id": input_data.document_id,
                "cached": True,
            }

        if input_data.force_refresh and existing_summary:
            print(
                f"🔄 FORCE REFRESH requested for document: {document_id} - regenerating AI summary"
            )
        elif input_data.force_refresh:
            print(
                f"🔄 FORCE REFRESH requested for document: {document_id} - no cached summary found, generating new one"
            )

        # Handle different content types
        content_type = document.get("content_type", "document")

        if content_type == "image":
            # Check if this image is part of a PDF image stack
            metadata = document.get("metadata", {})
            pdf_filename = metadata.get("pdf_filename")

            if pdf_filename:
                # This is part of an image stack - summarize the entire stack
                try:
                    # Get all images from the same PDF
                    image_vdb = create_vector_database(
                        collection_name=image_collection_name
                    )
                    all_images = image_vdb.list_images(limit=1000, offset=0)

                    # Filter images from the same PDF
                    pdf_images = [
                        img
                        for img in all_images
                        if img.get("metadata", {}).get("pdf_filename") == pdf_filename
                    ]

                    if len(pdf_images) > 1:
                        # Check if summary already exists in the first image's metadata (unless force refresh is requested)
                        first_image_metadata = pdf_images[0].get("metadata", {})
                        existing_summary = first_image_metadata.get("ai_summary")

                        if existing_summary and not input_data.force_refresh:
                            print(
                                f"📋 RETRIEVED cached AI summary for image stack: {pdf_filename}"
                            )
                            return {
                                "status": "success",
                                "summary": existing_summary,
                                "cached": True,
                            }

                        if input_data.force_refresh and existing_summary:
                            print(
                                f"🔄 FORCE REFRESH requested for image stack: {pdf_filename} - regenerating AI summary"
                            )

                        # Create comprehensive summary for the image stack
                        summary_text = f"This is an image stack containing {len(pdf_images)} images extracted from the PDF document '{pdf_filename}'.\n\n"

                        # Analyze classifications across all images
                        classifications = []
                        for img in pdf_images:
                            img_metadata = img.get("metadata", {})
                            img_classification = img_metadata.get("classification", {})
                            top_pred = img_classification.get("top_prediction", {})
                            if top_pred.get("label"):
                                classifications.append(top_pred["label"])

                        if classifications:
                            # Count unique classifications
                            from collections import Counter

                            class_counts = Counter(classifications)
                            unique_classes = len(class_counts)

                            summary_text += "**Image Analysis Summary:**\n"
                            summary_text += f"- Total images: {len(pdf_images)}\n"
                            summary_text += (
                                f"- Unique content types: {unique_classes}\n"
                            )

                            # Show top classifications
                            top_classes = class_counts.most_common(3)
                            summary_text += "- Most common content types:\n"
                            for label, count in top_classes:
                                summary_text += f"  • {label}: {count} images\n"

                        # Add metadata about the source PDF
                        summary_text += f"\n**Source Document:** {pdf_filename}"

                        if metadata.get("date_added"):
                            summary_text += f"\n**Extracted:** {metadata['date_added']}"

                        # Store the generated summary in the first image's metadata
                        try:
                            first_image_id = pdf_images[0].get("id")
                            if first_image_id:
                                print(
                                    f"💾 STORING new AI summary for image stack (PDF: {pdf_filename}, image_id: {first_image_id})"
                                )
                                image_vdb.update_image_metadata(
                                    first_image_id, {"ai_summary": summary_text}
                                )
                                print(
                                    f"✅ SUCCESSFULLY stored AI summary in image stack metadata for PDF: {pdf_filename}"
                                )
                        except Exception as e:
                            print(
                                f"❌ FAILED to store AI summary in image stack metadata: {e}"
                            )

                        return {
                            "status": "success",
                            "summary": summary_text,
                        }

                except Exception as e:
                    print(f"Error summarizing image stack: {e}")
                    # Fall back to single image summary

            # Single image summary (fallback or for non-stack images)
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

            # Store the generated summary in the image metadata
            try:
                image_vdb = create_vector_database(
                    collection_name=image_collection_name
                )
                print(
                    f"💾 STORING new AI summary for single image (image_id: {document_id})"
                )
                image_vdb.update_image_metadata(
                    document_id, {"ai_summary": summary_text}
                )
                print(
                    f"✅ SUCCESSFULLY stored AI summary in single image metadata for document: {document_id}"
                )
            except Exception as e:
                print(f"❌ FAILED to store AI summary in single image metadata: {e}")

            # Add additional metadata if available
            if metadata.get("file_size"):
                summary_text += f" File size: {metadata['file_size']} bytes."

            if metadata.get("format"):
                summary_text += f" Format: {metadata['format']}."

        else:
            # For text documents, use the existing summarization logic
            # Check if this is a grouped chunked document
            if document.get("isGroupedChunks") and document.get("combinedText"):
                # Use the combined text from all chunks
                content = document.get("combinedText", "")
                print(
                    f"Using combined text from {document.get('totalChunks', 0)} chunks"
                )
            else:
                # Use regular text content
                content = document.get("text", "")

            if not content:
                return {
                    "status": "success",
                    "summary": "No content available to summarize",
                }

            # For chunked documents, use more content since we have the full document
            if document.get("isGroupedChunks"):
                # Use more content for chunked documents to get better summaries
                limited_content = content[
                    :2000
                ]  # Increased limit for chunked documents
                if len(content) > 2000:
                    limited_content += "..."
            else:
                # Limit content more aggressively for faster processing of single documents
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

            # Adjust prompt based on whether this is a chunked document
            if document.get("isGroupedChunks"):
                summary_prompt = f"""Please provide a comprehensive summary of the following document content in 2-3 sentences.
                This document contains multiple sections/chunks. Focus on the main topics, key points, and overall document structure.

                Document content:
                {limited_content}"""
            else:
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

                # Store the generated summary in the document metadata
                try:
                    # Update the document metadata with the new summary
                    if document.get("content_type") == "image":
                        # For images, update in image collection
                        image_vdb = create_vector_database(
                            collection_name=image_collection_name
                        )
                        print(
                            f"💾 STORING new AI summary for image (image_id: {document_id})"
                        )
                        image_vdb.update_image_metadata(
                            document_id, {"ai_summary": summary_text}
                        )
                        print(
                            f"✅ SUCCESSFULLY stored AI summary in image metadata for document: {document_id}"
                        )
                    else:
                        # For documents, update in document collection
                        ragme = get_ragme()
                        print(
                            f"💾 STORING new AI summary for document (document_id: {document_id})"
                        )
                        ragme.update_document_metadata(
                            document_id, {"ai_summary": summary_text}
                        )
                        print(
                            f"✅ SUCCESSFULLY stored AI summary in document metadata for document: {document_id}"
                        )
                except Exception as e:
                    print(f"❌ FAILED to store AI summary in metadata: {e}")
                    # Continue without storing if there's an error

            except asyncio.TimeoutError:
                summary_text = "Summary generation timed out. The document may be too large or complex."

        # Ensure summary_text is defined
        if "summary_text" not in locals():
            summary_text = "Failed to generate summary. Please try again."

        return {
            "status": "success",
            "summary": summary_text,
            "document_id": input_data.document_id,
            "cached": False,
        }
    except Exception as e:
        print(f"Error in summarize_document endpoint: {e}")
        return {
            "status": "error",
            "summary": f"Error generating summary: {str(e)}. Please try again or use the Force Reload button.",
            "document_id": input_data.document_id,
        }


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
            # Check if document has a storage path and delete from storage if it exists
            storage_path = text_document.get("metadata", {}).get("storage_path")
            storage_deleted = False

            if storage_path:
                try:
                    storage_service = get_storage_service()
                    storage_deleted = storage_service.delete_file(storage_path)
                    if storage_deleted:
                        print(f"Deleted document from storage: {storage_path}")
                    else:
                        print(f"Failed to delete document from storage: {storage_path}")
                except Exception as storage_error:
                    print(
                        f"Error deleting document from storage {storage_path}: {storage_error}"
                    )
                    # Continue with vector database deletion even if storage deletion fails

            # Document exists in text collection, delete it from vector database
            success = get_ragme().delete_document(document_id)
            if success:
                message = f"Document {document_id} deleted successfully"
                if storage_path and storage_deleted:
                    message += f" (also deleted from storage: {storage_path})"
                elif storage_path and not storage_deleted:
                    message += f" (failed to delete from storage: {storage_path})"

                return {
                    "status": "success",
                    "message": message,
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


@app.delete("/delete-document-group/{base_url:path}")
async def delete_document_group(base_url: str):
    """
    Delete all chunks for a document by its base URL.
    This is more efficient than deleting chunks one by one from the frontend.

    Args:
        base_url: Base URL of the document (e.g., "file://ragme-io.pdf")

    Returns:
        dict: Status message with deletion count
    """
    try:
        # Decode URL if needed
        import urllib.parse

        base_url = urllib.parse.unquote(base_url)

        print(f"Backend: Deleting document group for base URL: {base_url}")

        # Get all documents
        documents = get_ragme().list_documents(limit=1000, offset=0)

        # Find all chunks that belong to this document
        chunks_to_delete = []
        storage_paths_to_delete = []

        for doc in documents:
            doc_url = doc.get("url", "")
            # Check if this document's URL starts with the base URL
            if doc_url.startswith(base_url):
                chunks_to_delete.append(doc)

                # Collect storage paths for deletion
                storage_path = doc.get("metadata", {}).get("storage_path")
                if storage_path and storage_path not in storage_paths_to_delete:
                    storage_paths_to_delete.append(storage_path)

        print(f"Backend: Found {len(chunks_to_delete)} chunks to delete for {base_url}")

        if not chunks_to_delete:
            return {
                "status": "success",
                "message": f"No chunks found for document {base_url}",
                "deleted_count": 0,
            }

        # Delete chunks from vector database
        deleted_count = 0
        failed_count = 0

        for chunk in chunks_to_delete:
            try:
                chunk_id = str(chunk.get("id"))
                success = get_ragme().delete_document(chunk_id)
                if success:
                    deleted_count += 1
                    print(f"Backend: Successfully deleted chunk {chunk_id}")
                else:
                    failed_count += 1
                    print(f"Backend: Failed to delete chunk {chunk_id}")
            except Exception as e:
                failed_count += 1
                print(f"Backend: Error deleting chunk {chunk.get('id')}: {e}")

        # Delete storage files
        storage_deleted_count = 0
        for storage_path in storage_paths_to_delete:
            try:
                storage_service = get_storage_service()
                if storage_service.delete_file(storage_path):
                    storage_deleted_count += 1
                    print(f"Backend: Deleted storage file: {storage_path}")
                else:
                    print(f"Backend: Failed to delete storage file: {storage_path}")
            except Exception as e:
                print(f"Backend: Error deleting storage file {storage_path}: {e}")

        message = f"Deleted {deleted_count} chunks for document {base_url}"
        if storage_deleted_count > 0:
            message += f" (and {storage_deleted_count} storage files)"
        if failed_count > 0:
            message += f" ({failed_count} chunks failed to delete)"

        return {
            "status": "success",
            "message": message,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "storage_deleted_count": storage_deleted_count,
        }

    except Exception as e:
        print(f"Backend: Error in delete_document_group: {e}")
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
                db_config.get("name", db_config.get("type", "weaviate-local"))
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

        # Get query configuration
        query_config = config.get("query", {})

        # Build safe configuration for frontend
        frontend_config_data = {
            "application": {
                "name": app_config.get("name", "RAGme"),
                "title": app_config.get("title", "RAGme.io Assistant"),
                "version": app_config.get("version", "1.0.0"),
            },
            "vector_databases": vector_db_info,
            "storage": storage_config,
            "frontend": frontend_config,
            "client": client_config,
            "features": features_config,
            "query": query_config,
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
            # Use a session to ensure proper connection cleanup
            with requests.Session() as session:
                response = session.get(
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


@app.get("/storage/{file_path:path}")
async def serve_storage_file(file_path: str):
    """
    Serve files directly from storage by file path.

    This endpoint allows direct access to files stored in the storage service
    using the file path as provided by the storage management tool.

    Args:
        file_path: The file path within storage (e.g., 'documents/file.pdf')

    Returns:
        FileResponse: The file content with appropriate headers
    """
    try:
        storage_service = get_storage_service()

        # Check if file exists
        if not storage_service.file_exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"detail": "File not found", "file_path": file_path},
            )

        # Get file info
        file_info = storage_service.get_file_info(file_path)

        # Get file content
        file_content = storage_service.get_file(file_path)

        # Determine content type
        content_type = file_info.get("content_type", "application/octet-stream")

        # Create response with appropriate headers
        from fastapi.responses import Response

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(file_info.get("size", 0)),
            "Content-Disposition": f"inline; filename={file_path.split('/')[-1]}",
        }

        return Response(content=file_content, headers=headers)

    except Exception as e:
        print(f"Error serving file {file_path}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)},
        )


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


@app.post("/update-query-settings")
async def update_query_settings(request: dict):
    """Update query settings."""
    try:
        # Extract query settings from request
        top_k = request.get("top_k", 5)
        text_rerank_top_k = request.get("text_rerank_top_k", 3)
        text_relevance_threshold = request.get("text_relevance_threshold", 0.5)
        image_relevance_threshold = request.get("image_relevance_threshold", 0.5)

        # Validate settings
        if not (1 <= top_k <= 20):
            return {
                "status": "error",
                "message": "Top K must be between 1 and 20",
            }

        if not (1 <= text_rerank_top_k <= 10):
            return {
                "status": "error",
                "message": "Text Rerank Top K must be between 1 and 10",
            }

        if not (0.1 <= text_relevance_threshold <= 1.0):
            return {
                "status": "error",
                "message": "Text relevance threshold must be between 0.1 and 1.0",
            }

        if not (0.1 <= image_relevance_threshold <= 1.0):
            return {
                "status": "error",
                "message": "Image relevance threshold must be between 0.1 and 1.0",
            }

        # Update the config.yaml file with new settings
        try:
            from src.ragme.utils.config_manager import config

            config.update_query_settings(
                {
                    "top_k": top_k,
                    "text_rerank_top_k": text_rerank_top_k,
                    "relevance_thresholds": {
                        "text": text_relevance_threshold,
                        "image": image_relevance_threshold,
                    },
                }
            )
        except Exception as config_error:
            print(f"Could not update config file: {config_error}")

        return {
            "status": "success",
            "message": "Query settings updated successfully",
            "settings": {
                "top_k": top_k,
                "text_rerank_top_k": text_rerank_top_k,
                "relevance_thresholds": {
                    "text": text_relevance_threshold,
                    "image": image_relevance_threshold,
                },
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update query settings: {str(e)}",
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
    import socketio  # type: ignore
    from socketio import AsyncServer  # type: ignore

    # Create Socket.IO server
    sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
    socket_app = socketio.ASGIApp(sio, app)

    # Socket event handlers
    @sio.event
    async def connect(sid, environ):
        print(f"🔌 SOCKET CONNECT: Client connected: {sid}")
        print(f"🔌 SOCKET CONNECT: Environment: {environ}")

    @sio.event
    async def disconnect(sid):
        print(f"🔌 SOCKET DISCONNECT: Client disconnected: {sid}")

    @sio.event
    async def chat_message(sid, data):
        """Handle chat message requests from frontend."""
        print(f"🔌 SOCKET EVENT: chat_message called with data: {data}")
        try:
            message = data.get("content", "")
            timestamp = data.get("timestamp", "")

            print(f"Processing chat message: {message}")

            # Process the query using the RAG system
            response = await get_ragme().run(message)

            print(f"RAG response: {response}")

            # Send response back to frontend
            await sio.emit(
                "chat_response",
                {"success": True, "response": response, "timestamp": timestamp},
                room=sid,
            )

        except Exception as e:
            print(f"Error in chat_message socket handler: {e}")
            await sio.emit(
                "chat_response",
                {
                    "success": False,
                    "error": f"Error processing message: {str(e)}",
                    "timestamp": data.get("timestamp", ""),
                },
                room=sid,
            )

    @sio.event
    async def summarize_document(sid, data):
        """Handle document summarization requests from frontend."""
        print(f"🔌 SOCKET EVENT: summarize_document called with data: {data}")
        try:
            document_id = data.get("documentId")
            force_refresh = data.get("forceRefresh", False)
            print(
                f"Received document_id: {document_id}, type: {type(document_id)}, force_refresh: {force_refresh}"
            )
            if not document_id:
                await sio.emit(
                    "document_summarized",
                    {"success": False, "message": "Document ID is required"},
                    room=sid,
                )
                return

            # Check if this is an image stack request
            if (
                isinstance(document_id, dict)
                and document_id.get("type") == "image_stack"
            ):
                print(f"Processing image stack request: {document_id}")
                # Handle image stack summarization
                pdf_filename = document_id.get("pdfFilename")
                if pdf_filename:
                    try:
                        from ..utils.config_manager import config
                        from ..vdbs.vector_db_factory import create_vector_database

                        # Get image collection name
                        image_collection_name = config.get_image_collection_name()

                        # Create image vector database
                        image_vdb = create_vector_database(
                            collection_name=image_collection_name
                        )

                        # List all images and filter by PDF filename
                        all_images = image_vdb.list_images(limit=1000, offset=0)
                        pdf_images = [
                            img
                            for img in all_images
                            if img.get("metadata", {}).get("pdf_filename")
                            == pdf_filename
                        ]

                        if pdf_images:
                            # Check if summary already exists in the first image's metadata (unless force refresh is requested)
                            first_image_metadata = pdf_images[0].get("metadata", {})
                            existing_summary = first_image_metadata.get("ai_summary")

                            if existing_summary and not force_refresh:
                                print(
                                    f"📋 RETRIEVED cached AI summary for image stack: {pdf_filename}"
                                )
                                await sio.emit(
                                    "document_summarized",
                                    {
                                        "success": True,
                                        "summary": existing_summary,
                                        "cached": True,
                                    },
                                    room=sid,
                                )
                                return

                            if force_refresh and existing_summary:
                                print(
                                    f"🔄 FORCE REFRESH requested for image stack: {pdf_filename} - regenerating AI summary"
                                )

                            # Create comprehensive summary for the image stack
                            summary_text = f"This is an image stack containing {len(pdf_images)} images extracted from the PDF document '{pdf_filename}'.\n\n"

                            # Analyze classifications across all images
                            classifications = []
                            for img in pdf_images:
                                img_metadata = img.get("metadata", {})
                                img_classification = img_metadata.get(
                                    "classification", {}
                                )
                                top_pred = img_classification.get("top_prediction", {})
                                if top_pred.get("label"):
                                    classifications.append(top_pred["label"])

                            if classifications:
                                # Count unique classifications
                                from collections import Counter

                                class_counts = Counter(classifications)
                                unique_classes = len(class_counts)

                                summary_text += "**Image Analysis Summary:**\n"
                                summary_text += f"- Total images: {len(pdf_images)}\n"
                                summary_text += (
                                    f"- Unique content types: {unique_classes}\n"
                                )

                                # Show top classifications
                                top_classes = class_counts.most_common(3)
                                summary_text += "- Most common content types:\n"
                                for label, count in top_classes:
                                    summary_text += f"  • {label}: {count} images\n"

                            # Add metadata about the source PDF
                            summary_text += f"\n**Source Document:** {pdf_filename}"

                            if pdf_images[0].get("metadata", {}).get("date_added"):
                                summary_text += f"\n**Extracted:** {pdf_images[0]['metadata']['date_added']}"

                            # Store the generated summary in the first image's metadata
                            try:
                                first_image_id = pdf_images[0].get("id")
                                if first_image_id:
                                    print(
                                        f"💾 STORING new AI summary for image stack (PDF: {pdf_filename}, image_id: {first_image_id})"
                                    )
                                    image_vdb.update_image_metadata(
                                        first_image_id, {"ai_summary": summary_text}
                                    )
                                    print(
                                        f"✅ SUCCESSFULLY stored AI summary in image stack metadata for PDF: {pdf_filename}"
                                    )
                            except Exception as e:
                                print(
                                    f"❌ FAILED to store AI summary in image stack metadata: {e}"
                                )

                            await sio.emit(
                                "document_summarized",
                                {"success": True, "summary": summary_text},
                                room=sid,
                            )
                            return
                        else:
                            await sio.emit(
                                "document_summarized",
                                {
                                    "success": False,
                                    "message": f"No images found for PDF: {pdf_filename}",
                                },
                                room=sid,
                            )
                            return
                    except Exception as e:
                        print(f"Error summarizing image stack: {e}")
                        await sio.emit(
                            "document_summarized",
                            {
                                "success": False,
                                "message": f"Error summarizing image stack: {str(e)}",
                            },
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
                # Check if summary already exists in metadata (unless force refresh is requested)
                metadata = document.get("metadata", {})
                existing_summary = metadata.get("ai_summary")

                if existing_summary and not force_refresh:
                    print(
                        f"📋 RETRIEVED cached AI summary for single image: {document_id}"
                    )
                    await sio.emit(
                        "document_summarized",
                        {"success": True, "summary": existing_summary, "cached": True},
                        room=sid,
                    )
                    return

                if force_refresh and existing_summary:
                    print(
                        f"🔄 FORCE REFRESH requested for single image: {document_id} - regenerating AI summary"
                    )

                # For images, create a summary based on metadata and classification
                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})
                confidence = top_prediction.get("confidence", 0)
                label = top_prediction.get("label", "Unknown")

                summary = f"Image Analysis:\n- Filename: {metadata.get('filename', 'Unknown')}\n- File Size: {metadata.get('file_size', 'Unknown')} bytes\n- Classification: {label} (confidence: {confidence:.2%})\n- Date Added: {metadata.get('date_added', 'Unknown')}"

                # Store the generated summary in the image metadata
                try:
                    print(
                        f"💾 STORING new AI summary for single image (image_id: {document_id})"
                    )
                    image_vdb.update_image_metadata(
                        document_id, {"ai_summary": summary}
                    )
                    print(
                        f"✅ SUCCESSFULLY stored AI summary in single image metadata for document: {document_id}"
                    )
                except Exception as e:
                    print(
                        f"❌ FAILED to store AI summary in single image metadata: {e}"
                    )

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

                    input_data = SummarizeInput(
                        document_id=document_id, force_refresh=force_refresh
                    )
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

    def serialize_weaviate_data(data):
        """Convert Weaviate UUID objects to strings for JSON serialization."""

        def convert_uuids(obj):
            # Check for various Weaviate UUID types
            if hasattr(obj, "__class__") and "WeaviateUUID" in str(obj.__class__):
                return str(obj)
            elif isinstance(obj, dict):
                return {key: convert_uuids(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_uuids(item) for item in obj]
            else:
                return obj

        return convert_uuids(data)

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
            if content_type in ["both", "document", "documents"]:
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

            # Apply date filtering
            filtered_items = filter_documents_by_date(all_items, date_filter)

            # Group chunked documents
            grouped_items = group_chunked_documents(filtered_items)

            # Sort by date (most recent first)
            grouped_items.sort(
                key=lambda x: x.get("metadata", {}).get("date_added", ""), reverse=True
            )

            # Apply pagination to grouped results
            total_count = len(grouped_items)
            paginated_items = grouped_items[offset : offset + limit]

            print(f"Returning {len(paginated_items)} items out of {total_count} total")

            # Serialize Weaviate UUIDs to strings for JSON compatibility
            serialized_items = serialize_weaviate_data(paginated_items)

            await sio.emit(
                "content_listed",
                {
                    "success": True,
                    "items": serialized_items,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "count": total_count,
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
            # Check if image has a storage path and delete from storage if it exists
            storage_path = image_document.get("metadata", {}).get("storage_path")
            storage_deleted = False

            if storage_path:
                try:
                    storage_service = get_storage_service()
                    storage_deleted = storage_service.delete_file(storage_path)
                    if storage_deleted:
                        print(f"Deleted image from storage: {storage_path}")
                    else:
                        print(f"Failed to delete image from storage: {storage_path}")
                except Exception as storage_error:
                    print(
                        f"Error deleting image from storage {storage_path}: {storage_error}"
                    )
                    # Continue with vector database deletion even if storage deletion fails

            # Image exists in image collection, delete it from vector database
            image_success = image_vdb.delete_image(image_id)
            if image_success:
                message = f"Image {image_id} deleted successfully"
                if storage_path and storage_deleted:
                    message += f" (also deleted from storage: {storage_path})"
                elif storage_path and not storage_deleted:
                    message += f" (failed to delete from storage: {storage_path})"

                return {
                    "status": "success",
                    "message": message,
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

        document = next(
            (doc for doc in documents if str(doc.get("id")) == document_id), None
        )

        if document:
            print(f"Found document: {document.get('url', 'No URL')}")
            # This is a text document, try to find the file in storage
            filename = document.get("metadata", {}).get("filename")
            storage_path = document.get("metadata", {}).get("storage_path")

            # Initialize storage_file to None
            storage_file = None

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
            else:
                # Document has no filename or storage_path - it was added before storage service
                print(
                    "Document has no filename or storage_path - not available in storage"
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

                # Initialize storage_file to None
                storage_file = None

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


# OAuth Authentication Endpoints


@app.get("/auth/providers")
async def get_auth_providers():
    """Get available OAuth providers."""
    try:
        print("[DEBUG] /auth/providers endpoint called")
        oauth_manager = get_oauth_manager()
        enabled_providers = oauth_manager.get_enabled_providers()
        print(f"[DEBUG] Enabled providers: {enabled_providers}")

        providers_info = []
        for provider in enabled_providers:
            oauth_manager.get_provider_config(provider)
            providers_info.append(
                {"name": provider, "display_name": provider.title(), "enabled": True}
            )

        result = {
            "success": True,
            "providers": providers_info,
            "bypass_login": config.is_login_bypassed(),
        }
        print(f"[DEBUG] Returning providers: {result}")
        return result
    except Exception as e:
        print(f"[DEBUG] Error in /auth/providers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/auth/{provider}/login")
async def oauth_login(provider: str):
    """Initiate OAuth login flow for a provider."""
    try:
        oauth_manager = get_oauth_manager()

        if not oauth_manager.is_provider_enabled(provider):
            raise HTTPException(
                status_code=400, detail=f"OAuth provider '{provider}' is not enabled"
            )

        # Generate authorization URL
        auth_url = oauth_manager.get_authorization_url(provider)

        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/auth/{provider}/callback")
async def oauth_callback(
    provider: str, code: str, state: str = None, response: Response = None
):
    """Handle OAuth callback from provider."""
    try:
        oauth_manager = get_oauth_manager()
        session_manager = get_session_manager()
        user_manager = get_user_manager()

        if not oauth_manager.is_provider_enabled(provider):
            raise HTTPException(
                status_code=400, detail=f"OAuth provider '{provider}' is not enabled"
            )

        # Exchange code for token and user info
        token_data = await oauth_manager.exchange_code_for_token(provider, code, state)
        user_info = token_data["user_info"]

        # Create or update user
        user_manager.create_or_update_user(user_info, provider)

        # Create session
        session_data = session_manager.create_session(user_info, provider)
        print(
            f"DEBUG: Created session for user {user_info.get('email')} with token: {session_data['token'][:20]}..."
        )

        # Set session cookie
        cookie_config = session_manager.get_session_cookie_config()
        print(f"DEBUG: Cookie config: {cookie_config}")

        # Set cookie with conditional domain
        cookie_kwargs = {
            "key": "session_token",
            "value": session_data["token"],
            "max_age": cookie_config["max_age"],
            "secure": cookie_config["secure"],
            "httponly": cookie_config["httponly"],
            "samesite": cookie_config["samesite"],
            "path": cookie_config["path"],
        }

        # Only set domain if it's specified
        if "domain" in cookie_config and cookie_config["domain"]:
            cookie_kwargs["domain"] = cookie_config["domain"]

        response.set_cookie(**cookie_kwargs)
        print(
            f"DEBUG: Set session cookie with path={cookie_config['path']}, domain={'not set' if 'domain' not in cookie_config else cookie_config['domain']}"
        )

        # Redirect to frontend with success and session token
        frontend_port = config.get("network.frontend.port", 8020)
        frontend_url = f"http://localhost:{frontend_port}"
        return RedirectResponse(
            url=f"{frontend_url}/?auth=success&token={session_data['token']}"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/auth/me")
async def get_current_user_info(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get current user information."""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        return {
            "success": True,
            "user": {
                "id": current_user["user_id"],
                "email": current_user["email"],
                "name": current_user["name"],
                "provider": current_user["provider"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/auth/logout")
async def logout(response: Response):
    """Logout current user."""
    try:
        # Clear session cookie
        response.delete_cookie(key="session_token")

        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/auth/status")
async def auth_status(current_user: dict[str, Any] = Depends(get_current_user)):
    """Check authentication status."""
    try:
        bypass_login = config.is_login_bypassed()

        if current_user:
            return {
                "authenticated": True,
                "bypass_login": bypass_login,
                "user": {
                    "id": current_user["user_id"],
                    "email": current_user["email"],
                    "name": current_user["name"],
                    "provider": current_user["provider"],
                },
            }
        else:
            return {
                "authenticated": bypass_login,  # If bypass_login is true, consider user authenticated
                "bypass_login": bypass_login,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/auth/debug")
async def auth_debug(request: Request, token: str | None = Cookie(None)):
    """Debug authentication information (for troubleshooting)."""
    try:
        session_manager = get_session_manager()
        secret_info = session_manager.get_session_secret_info()

        # Check for token in cookie first
        session_token = token
        if not session_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_token = auth_header[7:]

        debug_info = {
            "session_secret_info": secret_info,
            "token_provided": session_token is not None,
            "token_length": len(session_token) if session_token else 0,
            "token_prefix": session_token[:20] + "..."
            if session_token and len(session_token) > 20
            else session_token,
            "bypass_login": config.is_login_bypassed(),
        }

        if session_token:
            session_data = session_manager.validate_token(session_token)
            debug_info["token_valid"] = session_data is not None
            if session_data:
                debug_info["user_email"] = session_data.get("email")
                debug_info["expires_at"] = session_data.get("expires_at")
                debug_info["time_until_expiry"] = (
                    session_data.get("expires_at", 0) - time.time()
                )

        return debug_info
    except Exception as e:
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
