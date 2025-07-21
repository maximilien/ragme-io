# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

# Import from the new modular structure
from .vector_db_base import VectorDatabase
from .vector_db_weaviate import WeaviateVectorDatabase
from .vector_db_milvus import MilvusVectorDatabase
from .vector_db_factory import create_vector_database

# Re-export for backward compatibility
__all__ = [
    'VectorDatabase',
    'WeaviateVectorDatabase', 
    'MilvusVectorDatabase',
    'create_vector_database'
] 