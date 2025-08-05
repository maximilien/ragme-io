"""
API and MCP server implementations.

This module provides the FastAPI server implementation and Model Context Protocol
(MCP) server for RAGme.
"""

from .api import app
from .mcp import Base64FileRequest, ToolResponse
from .mcp import app as mcp_app

__all__ = [
    "app",
    "mcp_app",
    "ToolResponse",
    "Base64FileRequest",
]
