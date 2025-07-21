# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
from abc import ABC, abstractmethod
from typing import List, Dict, Any

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    def __init__(self, collection_name: str = "RagMeDocs"):
        """Initialize the vector database with a collection name."""
        self.collection_name = collection_name
    
    @property
    @abstractmethod
    def db_type(self) -> str:
        """Return the type/name of the vector database."""
        pass
    
    @abstractmethod
    def setup(self):
        """Set up the database and create collections if they don't exist."""
        pass
    
    @abstractmethod
    def write_documents(self, documents: List[Dict[str, Any]]):
        """
        Write documents to the vector database.
        
        Args:
            documents: List of documents with 'url', 'text', and 'metadata' fields
        """
        pass
    
    @abstractmethod
    def list_documents(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents from the vector database.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of documents with their properties
        """
        pass
    
    @abstractmethod
    def create_query_agent(self):
        """Create and return a query agent for this vector database."""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources and close connections."""
        pass 