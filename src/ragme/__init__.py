# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
RAGme - A personalized agent to RAG websites and documents.

This package provides a modular architecture for RAG (Retrieval-Augmented Generation)
with support for multiple vector databases, agents, and APIs.
"""

# Import submodules for easy access
from . import agents, apis, utils, vdbs
from .ragme import RagMe

__all__ = [
    "RagMe",
    "vdbs",
    "agents",
    "apis",
    "utils",
]
