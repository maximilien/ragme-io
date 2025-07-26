# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from .vector_db_base import VectorDatabase
from .vector_db_milvus import MilvusVectorDatabase
from .vector_db_weaviate import WeaviateVectorDatabase


def create_vector_database(
    db_type: str = None, collection_name: str = "RagMeDocs"
) -> VectorDatabase:
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
        db_type = os.getenv("VECTOR_DB_TYPE", "milvus")  # Changed default to milvus

    if db_type.lower() == "weaviate":
        # Check if Weaviate credentials are properly configured
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        weaviate_url = os.getenv("WEAVIATE_URL")

        if not weaviate_api_key or not weaviate_url:
            print(
                "⚠️  Weaviate credentials not found. Falling back to Milvus for local development."
            )
            print(
                "   To use Weaviate, set WEAVIATE_API_KEY and WEAVIATE_URL environment variables."
            )
            return MilvusVectorDatabase(collection_name)

        try:
            return WeaviateVectorDatabase(collection_name)
        except Exception as e:
            print(f"⚠️  Failed to connect to Weaviate: {e}")
            print("   Falling back to Milvus for local development.")
            return MilvusVectorDatabase(collection_name)

    elif db_type.lower() == "milvus":
        return MilvusVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
