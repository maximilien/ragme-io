# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import traceback
import warnings
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .ragme import RagMe

# Suppress Pydantic deprecation and schema warnings from dependencies
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince211.*"
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


@app.post("/add-json")
async def add_json(json_input: JSONInput):
    """
    Add JSON content to the RAG system.

    Args:
        json_input: JSON data and optional metadata to add

    Returns:
        dict: Status message
    """
    try:
        ragme.write_json_to_weaviate(json_input.data, json_input.metadata)
        return {"status": "success", "message": "Successfully processed JSON content"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


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


@app.get("/list-documents")
async def list_documents(
    limit: int = Query(
        default=10, ge=1, le=100, description="Maximum number of documents to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of documents to skip"),
):
    """
    List documents in the RAG system.

    Args:
        limit: Maximum number of documents to return (1-100)
        offset: Number of documents to skip

    Returns:
        dict: List of documents and pagination info
    """
    try:
        documents = ragme.list_documents(limit=limit, offset=offset)
        return {
            "status": "success",
            "documents": documents,
            "pagination": {"limit": limit, "offset": offset, "count": len(documents)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8021)
