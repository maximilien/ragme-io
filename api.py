from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import asyncio
from ragme import RagMe

app = FastAPI(
    title="RagMe API",
    description="API for RAG operations with web content using Weaviate",
    version="1.0.0"
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
    urls: List[str]

class QueryInput(BaseModel):
    """Input model for querying the RAG system."""
    query: str

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
            "urls_processed": len(url_input.urls)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the application shuts down."""
    ragme.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)