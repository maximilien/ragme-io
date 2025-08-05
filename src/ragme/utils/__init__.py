"""
Utility functions and classes for RAGme.

This module provides common utility functions and classes used throughout
the RAGme system.
"""

from .common import crawl_webpage
from .socket_manager import emit_document_added, set_socket_manager

__all__ = [
    "crawl_webpage",
    "set_socket_manager",
    "emit_document_added",
]
