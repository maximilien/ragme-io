# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os

from ..utils.config_manager import config
from .vector_db_base import CollectionConfig, VectorDatabase
from .vector_db_milvus import MilvusVectorDatabase
from .vector_db_weaviate import WeaviateVectorDatabase
from .vector_db_weaviate_local import WeaviateLocalVectorDatabase


def create_vector_database(
    db_type: str | None = None, collection_name: str | None = None
) -> VectorDatabase:
    """
    Factory function to create vector database instances.

    Args:
        db_type: Type of vector database ("weaviate", "milvus", etc.).
                If None, uses the default from config.yaml
        collection_name: Name of the collection to use.
                        If None, uses the collection name from config.yaml

    Returns:
        VectorDatabase instance
    """
    # Get database configuration
    if db_type is None:
        # First try environment variable for backward compatibility
        db_type = os.getenv("VECTOR_DB_TYPE")
        if db_type is None:
            # Use default from config
            db_type = config.get("databases.default", "weaviate-local")
            # If config returns the unsubstituted placeholder, use fallback
            if db_type == "${VECTOR_DB_TYPE}":
                db_type = "weaviate-local"

    # Map environment variable values to config database names
    db_type_mapping = {
        "weaviate": "weaviate-cloud",
        "weaviate-local": "weaviate-local",
        "milvus": "milvus-local",
        "milvus-local": "milvus-local",
        "milvus-cloud": "milvus-cloud",
    }
    db_type = db_type_mapping.get(db_type, db_type)

    # Get database configuration
    db_config = config.get_database_config(db_type)
    if db_config is None:
        # Fallback to environment variables for backward compatibility
        return _create_database_legacy(db_type, collection_name)

    # Get collections configuration
    collections_config = config.get_collections_config(db_type)

    # Convert to CollectionConfig objects
    collections = []
    for collection_config in collections_config:
        if isinstance(collection_config, dict):
            name = collection_config.get("name", "RagMeDocs")
            collection_type = collection_config.get("type", "text")
            collections.append(CollectionConfig(name, collection_type))

    # If no collections configured, create default text collection
    if not collections:
        if collection_name is None:
            collection_name = config.get_text_collection_name(db_type)
        collections = [CollectionConfig(collection_name, "text")]

    db_type_normalized = db_config.get("type", db_type).lower()

    if db_type_normalized in ["weaviate", "weaviate-cloud"]:
        return _create_weaviate_cloud(db_config, collections)
    elif db_type_normalized == "weaviate-local":
        return _create_weaviate_local(db_config, collections)
    elif db_type_normalized in ["milvus", "milvus-local", "milvus-cloud"]:
        return _create_milvus(db_config, collections)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type_normalized}")


def _create_weaviate_cloud(
    db_config: dict, collections: list[CollectionConfig]
) -> VectorDatabase:
    """Create Weaviate Cloud instance."""
    api_key = db_config.get("api_key")
    url = db_config.get("url")

    if not api_key or not url or "${" in str(api_key) or "${" in str(url):
        print("⚠️  Weaviate Cloud credentials not configured in config.yaml.")
        print("   Set WEAVIATE_API_KEY and WEAVIATE_URL environment variables.")
        print("   Falling back to default database.")
        # Fall back to default database
        default_db = config.get("vector_databases.default", "weaviate-local")
        if default_db != "weaviate-cloud":
            fallback_config = config.get_database_config(default_db)
            if fallback_config:
                return create_vector_database(default_db)
        return MilvusVectorDatabase(collections)

    try:
        return WeaviateVectorDatabase(collections)
    except Exception as e:
        print(f"⚠️  Failed to connect to Weaviate Cloud: {e}")
        print("   Falling back to local database.")
        return _create_fallback_database(collections)


def _create_weaviate_local(
    db_config: dict, collections: list[CollectionConfig]
) -> VectorDatabase:
    """Create local Weaviate instance."""
    try:
        return WeaviateLocalVectorDatabase(collections)
    except Exception as e:
        print(f"⚠️  Failed to connect to local Weaviate: {e}")
        print(
            "   Make sure local Weaviate is running (see tools/podman-compose.weaviate.yml)"
        )
        print("   Falling back to Milvus.")
        return _create_fallback_database(collections)


def _create_milvus(
    db_config: dict, collections: list[CollectionConfig]
) -> VectorDatabase:
    """Create Milvus instance."""
    return MilvusVectorDatabase(collections)


def _create_fallback_database(collections: list[CollectionConfig]) -> VectorDatabase:
    """Create fallback database (Milvus)."""
    return MilvusVectorDatabase(collections)


def _create_database_legacy(
    db_type: str, collection_name: str | None
) -> VectorDatabase:
    """Legacy database creation using environment variables."""
    if collection_name is None:
        collection_name = "RagMeDocs"

    # Create default text collection for legacy support
    collections = [CollectionConfig(collection_name, "text")]

    if db_type.lower() == "weaviate":
        # Check if Weaviate credentials are properly configured
        weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        weaviate_url = os.getenv("WEAVIATE_URL")

        if not weaviate_api_key or not weaviate_url:
            print(
                "⚠️  Weaviate Cloud credentials not found. Falling back to Milvus for local development."
            )
            print(
                "   To use Weaviate Cloud, set WEAVIATE_API_KEY and WEAVIATE_URL environment variables."
            )
            print("   To use local Weaviate, set VECTOR_DB_TYPE=weaviate-local")
            return MilvusVectorDatabase(collections)

        try:
            return WeaviateVectorDatabase(collections)
        except Exception as e:
            print(f"⚠️  Failed to connect to Weaviate Cloud: {e}")
            print("   Falling back to Milvus for local development.")
            return MilvusVectorDatabase(collections)

    elif db_type.lower() == "weaviate-local":
        try:
            return WeaviateLocalVectorDatabase(collections)
        except Exception as e:
            print(f"⚠️  Failed to connect to local Weaviate: {e}")
            print(
                "   Make sure local Weaviate is running (see tools/podman-compose.weaviate.yml)"
            )
            print("   Falling back to Milvus for local development.")
            return MilvusVectorDatabase(collections)

    elif db_type.lower() == "milvus":
        return MilvusVectorDatabase(collections)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
