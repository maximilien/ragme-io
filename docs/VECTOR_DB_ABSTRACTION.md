# Vector Database Abstraction

The `RagMe` class has been refactored to be vector database agnostic, allowing you to easily switch between different vector database implementations without changing your core application logic.

## Overview

The vector database abstraction consists of:

1. **`VectorDatabase`** - Abstract base class defining the interface
2. **`WeaviateVectorDatabase`** - Implementation for Weaviate
3. **`create_vector_database()`** - Factory function for creating database instances
4. **Updated `RagMe`** - Now accepts any vector database implementation

## Architecture

```
VectorDatabase (ABC)
    ├── WeaviateVectorDatabase
    ├── PineconeVectorDatabase (future)
    ├── ChromaVectorDatabase (future)
    └── ...
```

## Usage Examples

### Default Weaviate Usage

```python
from src.ragme.ragme import RagMe

# Uses Weaviate by default
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Custom Vector Database Instance

```python
from src.ragme.ragme import RagMe
from src.ragme.vector_db import WeaviateVectorDatabase

# Create custom vector database
custom_db = WeaviateVectorDatabase("MyCollection")

# Use with RagMe
ragme = RagMe(vector_db=custom_db)
ragme.write_json_to_weaviate({"content": "example"})
ragme.cleanup()
```

### Factory Pattern

```python
from src.ragme.ragme import RagMe
from src.ragme.vector_db import create_vector_database

# Create database using factory
db = create_vector_database("weaviate", "FactoryCollection")
ragme = RagMe(vector_db=db)
```

## VectorDatabase Interface

The `VectorDatabase` abstract base class defines these methods:

### Required Methods

- `__init__(collection_name: str)` - Initialize with collection name
- `setup()` - Set up database and create collections if needed
- `write_documents(documents: List[Dict[str, Any]])` - Write documents to database
- `list_documents(limit: int, offset: int)` - List documents from database
- `create_query_agent()` - Create and return a query agent
- `cleanup()` - Clean up resources and close connections

### Document Format

Documents should be dictionaries with these fields:
```python
{
    "url": "source_url_or_identifier",
    "text": "document_content",
    "metadata": {"optional": "metadata"}
}
```

## Adding New Vector Database Implementations

To add support for a new vector database (e.g., Pinecone):

1. Create a new class implementing `VectorDatabase`:

```python
class PineconeVectorDatabase(VectorDatabase):
    def __init__(self, collection_name: str = "RagMeDocs"):
        super().__init__(collection_name)
        # Initialize Pinecone client
        
    def setup(self):
        # Set up Pinecone index
        
    def write_documents(self, documents: List[Dict[str, Any]]):
        # Write documents to Pinecone
        
    def list_documents(self, limit: int = 10, offset: int = 0):
        # List documents from Pinecone
        
    def create_query_agent(self):
        # Create Pinecone-specific query agent
        
    def cleanup(self):
        # Clean up Pinecone resources
```

2. Update the factory function:

```python
def create_vector_database(db_type: str = "weaviate", collection_name: str = "RagMeDocs"):
    if db_type.lower() == "weaviate":
        return WeaviateVectorDatabase(collection_name)
    elif db_type.lower() == "pinecone":
        return PineconeVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
```

## Benefits

1. **Flexibility** - Easy to switch between vector databases
2. **Testability** - Can mock vector database for testing
3. **Extensibility** - Simple to add new database implementations
4. **Separation of Concerns** - Database logic separated from RAG logic
5. **Future-Proof** - Can adapt to new vector database technologies

## Migration from Previous Version

The `RagMe` class maintains backward compatibility. Existing code will continue to work:

```python
# Old way (still works)
ragme = RagMe()

# New way (more flexible)
ragme = RagMe(vector_db=WeaviateVectorDatabase("CustomCollection"))
```

## Environment Variables

The Weaviate implementation still requires these environment variables:
- `WEAVIATE_API_KEY`
- `WEAVIATE_URL`
- `OPENAI_API_KEY`

Other vector database implementations may require different environment variables.

## Testing

The abstraction includes comprehensive tests in `tests/test_vector_db.py` that cover:
- Abstract base class behavior
- Weaviate implementation
- Factory function
- Error handling

All tests use mocking to avoid requiring actual database connections. 