"""
Vector Database implementations and factory functions.

This module provides the vector database abstraction layer with support for
multiple vector database backends including Weaviate, Milvus, and others.
"""

from .vector_db_base import VectorDatabase
from .vector_db_factory import create_vector_database
from .vector_db_milvus import MilvusVectorDatabase
from .vector_db_weaviate import WeaviateVectorDatabase
from .vector_db_weaviate_local import WeaviateLocalVectorDatabase

__all__ = [
    "VectorDatabase",
    "create_vector_database",
    "WeaviateVectorDatabase",
    "WeaviateLocalVectorDatabase",
    "MilvusVectorDatabase",
]
