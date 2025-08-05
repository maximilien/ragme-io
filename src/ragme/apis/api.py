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
from pydantic import BaseModel

from ..ragme import RagMe

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
    ragme.cleanup()


app = FastAPI(
    title="RagMe API",
    description="API for RAG operations with web content using a Vector Database",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize RagMe instance
ragme = RagMe()


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
        ragme.write_webpages_to_weaviate(url_input.urls)
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
                existing_doc = ragme.vector_db.find_document_by_url(unique_url)
                if existing_doc:
                    # Only replace if it's not a chunked document or if the new one is chunked
                    # This prevents chunked documents from replacing regular documents
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
                        ragme.vector_db.delete_document(existing_doc["id"])
                        replaced_count += 1
                    elif existing_is_chunked and not new_is_chunked:
                        # Skip adding this document to avoid replacing chunked document with regular document
                        continue

                # Add the new document with unique URL
                ragme.vector_db.write_documents(
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
            ragme.write_json_to_weaviate(json_input.data, json_input.metadata)
            return {"status": "success", "message": "JSON data added to RAG system"}

    except Exception as e:
        # Assuming 'logger' is defined elsewhere or needs to be imported
        # For now, using print for simplicity as 'logger' is not defined in the original file
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
        response = await ragme.run(query_input.query)
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
            date_added = datetime.fromisoformat(date_added_str.replace("Z", "+00:00"))
            if date_added >= cutoff_date:
                filtered_documents.append(doc)
        except (ValueError, TypeError):
            # If date parsing fails, include the document
            filtered_documents.append(doc)

    return filtered_documents


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
        all_documents = ragme.list_documents(limit=1000, offset=0)

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


@app.post("/summarize-document")
async def summarize_document(input_data: SummarizeInput):
    """
    Summarize a document using the RagMe agent.

    Args:
        input_data: Contains document_id to summarize

    Returns:
        dict: Summarized content
    """
    try:
        # Get the document content
        documents = ragme.list_documents(
            limit=1000, offset=0
        )  # Get all documents to find the one by ID

        # Find the document by ID (assuming ID is the index in the list)
        try:
            doc_id = int(input_data.document_id)
            if doc_id < 0 or doc_id >= len(documents):
                raise HTTPException(status_code=404, detail="Document not found")
            document = documents[doc_id]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document ID") from None

        # Create a summarization prompt
        content = document.get("text", "")
        if not content:
            return {"status": "success", "summary": "No content available to summarize"}

        # Limit content more aggressively for faster processing
        limited_content = content[
            :500
        ]  # Reduced from 1000 to 500 characters for faster processing
        if len(content) > 500:
            limited_content += "..."

        # Use a direct LLM call for faster summarization
        from llama_index.llms.openai import OpenAI

        llm = OpenAI(
            model="gpt-4o-mini", temperature=0.1
        )  # Lower temperature for more consistent summaries

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
                    # Add to RAG system
                    metadata = {
                        "type": filename.split(".")[-1],
                        "filename": file.filename,
                        "date_added": datetime.now().isoformat(),
                    }

                    # Generate unique URL to prevent overwriting
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    unique_url = f"file://{file.filename}#{timestamp}"

                    ragme.vector_db.write_documents(
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
        success = ragme.delete_document(document_id)

        if success:
            return {
                "status": "success",
                "message": f"Document {document_id} deleted successfully",
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

    except Exception as e:
        print(f"Error deleting document {document_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8021)
