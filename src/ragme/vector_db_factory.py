# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from .vector_db_base import VectorDatabase
from .vector_db_weaviate import WeaviateVectorDatabase
from .vector_db_milvus import MilvusVectorDatabase


def create_vector_database(db_type: str = None, collection_name: str = "RagMeDocs") -> VectorDatabase:
    """
    Factory function to create vector database instances.
    Args:
        db_type: Type of vector database ("weaviate", "milvus", etc.)
        collection_name: Name of the collection to use
    Returns:
        VectorDatabase instance
    """
    import os
    if db_type is None:
        db_type = os.getenv("VECTOR_DB_TYPE", "weaviate")
    if db_type.lower() == "weaviate":
        return WeaviateVectorDatabase(collection_name)
    elif db_type.lower() == "milvus":
        return MilvusVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}") 