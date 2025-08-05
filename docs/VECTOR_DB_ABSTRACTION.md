# Vector Database Abstraction

The `RagMe` class has been refactored to be vector database agnostic, allowing you to easily switch between different vector database implementations without changing your core application logic.

## Overview

The vector database abstraction consists of:

1. **`VectorDatabase`** - Abstract base class defining the interface
2. **`WeaviateVectorDatabase`** - Implementation for Weaviate Cloud (⭐ Recommended)
3. **`WeaviateLocalVectorDatabase`** - Implementation for local Weaviate (Podman) (⭐ Recommended for local development)
4. **`MilvusVectorDatabase`** - Implementation for Milvus (alternative for local development)
5. **`create_vector_database()`** - Factory function for creating database instances
6. **Updated `RagMe`** - Now accepts any vector database implementation

## File Structure

The vector database implementation is organized into modular files:

```
src/ragme/
├── vector_db.py              # Compatibility layer (imports from modules)
├── vector_db_base.py         # Abstract base class
├── vector_db_weaviate.py     # Weaviate Cloud implementation
├── vector_db_weaviate_local.py # Local Weaviate implementation
├── vector_db_milvus.py       # Milvus implementation (default)
└── vector_db_factory.py      # Factory function
```

### Test Structure

The test suite mirrors the modular code structure:

```
tests/
├── test_vector_db_base.py      # Tests for abstract base class
├── test_vector_db_weaviate.py  # Tests for Weaviate implementation
├── test_vector_db_milvus.py    # Tests for Milvus implementation
├── test_vector_db_factory.py   # Tests for factory function
└── test_vector_db.py           # Compatibility layer (imports from above)
```

## Architecture

```
VectorDatabase (ABC)
    ├── WeaviateVectorDatabase (Cloud)
    ├── WeaviateLocalVectorDatabase (Local)
    ├── MilvusVectorDatabase (Default)
    ├── PineconeVectorDatabase (future)
    ├── ChromaVectorDatabase (future)
    └── ...
```

## Usage Examples

### Default Weaviate Usage ⭐ **RECOMMENDED**

```python
from src.ragme.ragme import RagMe
import os

# Uses Weaviate by default (recommended)
os.environ["VECTOR_DB_TYPE"] = "weaviate-local"
os.environ["WEAVIATE_LOCAL_URL"] = "http://localhost:8080"
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Using Weaviate Cloud

```python
from src.ragme.ragme import RagMe
import os

# Configure for Weaviate Cloud
os.environ["VECTOR_DB_TYPE"] = "weaviate"
os.environ["WEAVIATE_URL"] = "https://your-cluster.weaviate.cloud"
os.environ["WEAVIATE_API_KEY"] = "your-api-key"

# Initialize RagMe with Weaviate Cloud
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Using Milvus (Alternative)

```python
from src.ragme.ragme import RagMe
import os

# Configure for Milvus
os.environ["VECTOR_DB_TYPE"] = "milvus"
os.environ["MILVUS_URI"] = "milvus_demo.db"  # Local Milvus Lite

# Initialize RagMe with Milvus
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Using Local Weaviate

```python
from src.ragme.ragme import RagMe
import os

# Configure for local Weaviate
os.environ["VECTOR_DB_TYPE"] = "weaviate-local"
os.environ["WEAVIATE_LOCAL_URL"] = "http://localhost:8080"

# Initialize RagMe with local Weaviate
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Using Weaviate Cloud

```python
from src.ragme.ragme import RagMe
import os

# Configure for Weaviate Cloud
os.environ["VECTOR_DB_TYPE"] = "weaviate"
os.environ["WEAVIATE_API_KEY"] = "your-api-key"
os.environ["WEAVIATE_URL"] = "https://your-cluster.weaviate.network"

# Initialize RagMe with Weaviate Cloud
ragme = RagMe()
ragme.write_webpages_to_weaviate(["https://example.com"])
documents = ragme.list_documents()
ragme.cleanup()
```

### Custom Vector Database Instance

```python
from src.ragme.ragme import RagMe
from src.ragme.vdbs.vector_db_weaviate import WeaviateVectorDatabase
from src.ragme.vdbs.vector_db_milvus import MilvusVectorDatabase
from src.ragme.vdbs.vector_db_weaviate_local import WeaviateLocalVectorDatabase

# Create custom Weaviate Cloud database
weaviate_db = WeaviateVectorDatabase("MyWeaviateCollection")
ragme = RagMe(vector_db=weaviate_db)

# Or create custom local Weaviate database
weaviate_local_db = WeaviateLocalVectorDatabase("MyLocalCollection")
ragme = RagMe(vector_db=weaviate_local_db)

# Or create custom Milvus database
milvus_db = MilvusVectorDatabase("MyMilvusCollection")
ragme = RagMe(vector_db=milvus_db)
```

### Factory Pattern

```python
from src.ragme.ragme import RagMe
from src.ragme.vdbs.vector_db_factory import create_vector_database

# Create Weaviate Cloud database using factory
weaviate_db = create_vector_database("weaviate", "FactoryCollection")
ragme = RagMe(vector_db=weaviate_db)

# Create local Weaviate database using factory
weaviate_local_db = create_vector_database("weaviate-local", "LocalCollection")
ragme = RagMe(vector_db=weaviate_local_db)

# Create Milvus database using factory
milvus_db = create_vector_database("milvus", "MilvusCollection")
ragme = RagMe(vector_db=milvus_db)
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
- `db_type` property - Return the type/name of the vector database

### Document Format

Documents should be dictionaries with these fields:
```python
{
    "url": "source_url_or_identifier",
    "text": "document_content",
    "metadata": {"optional": "metadata"}
}
```

For Milvus, documents must also include a `vector` field:
```python
{
    "url": "source_url_or_identifier",
    "text": "document_content",
    "metadata": {"optional": "metadata"},
    "vector": [0.1, 0.2, ...]  # Required for Milvus
}
```

## Adding New Vector Database Implementations

To add support for a new vector database (e.g., Pinecone):

1. Create a new class implementing `VectorDatabase`:

```python
# src/ragme/vector_db_pinecone.py
from .vector_db_base import VectorDatabase

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
        
    @property
    def db_type(self) -> str:
        return "pinecone"
```

2. Update the factory function in `src/ragme/vector_db_factory.py`:

```python
def create_vector_database(db_type: str = None, collection_name: str = "RagMeDocs") -> VectorDatabase:
    import os
    if db_type is None:
        db_type = os.getenv("VECTOR_DB_TYPE", "milvus")  # Milvus is now default
    if db_type.lower() == "weaviate":
        return WeaviateVectorDatabase(collection_name)
    elif db_type.lower() == "weaviate-local":
        return WeaviateLocalVectorDatabase(collection_name)
    elif db_type.lower() == "milvus":
        return MilvusVectorDatabase(collection_name)
    elif db_type.lower() == "pinecone":
        return PineconeVectorDatabase(collection_name)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
```

3. Create corresponding test file `tests/test_vector_db_pinecone.py`

4. Update the compatibility layer in `src/ragme/vector_db.py`:

```python
from .vector_db_pinecone import PineconeVectorDatabase

__all__ = [
    'VectorDatabase',
    'WeaviateVectorDatabase',
    'WeaviateLocalVectorDatabase',
    'MilvusVectorDatabase',
    'PineconeVectorDatabase',
    'create_vector_database'
]
```

## Benefits

1. **Flexibility** - Easy to switch between vector databases
2. **Testability** - Can mock vector database for testing
3. **Extensibility** - Simple to add new database implementations
4. **Separation of Concerns** - Database logic separated from RAG logic
5. **Future-Proof** - Can adapt to new vector database technologies
6. **Modularity** - Each implementation is in its own file
7. **Maintainability** - Easy to maintain and debug specific implementations
8. **Local Development** - Milvus Lite provides easy local development without external dependencies

## Migration from Previous Version

The `RagMe` class maintains backward compatibility. Existing code will continue to work:

```python
# Old way (still works, now defaults to Milvus)
ragme = RagMe()

# New way (more flexible)
ragme = RagMe(vector_db=MilvusVectorDatabase("CustomCollection"))

# New modular imports (recommended)
from src.ragme.vdbs.vector_db_weaviate import WeaviateVectorDatabase
from src.ragme.vdbs.vector_db_weaviate_local import WeaviateLocalVectorDatabase
from src.ragme.vdbs.vector_db_milvus import MilvusVectorDatabase
from src.ragme.vdbs.vector_db_factory import create_vector_database
```

## Environment Variables

### Weaviate (Recommended)
- `VECTOR_DB_TYPE=weaviate-local` - Set to use local Weaviate (default: `http://localhost:8080`)
- `WEAVIATE_LOCAL_URL` - Local Weaviate URL (default: `http://localhost:8080`)
- `OPENAI_API_KEY` - OpenAI API key for LLM operations

### Weaviate Cloud
- `VECTOR_DB_TYPE=weaviate` - Set to use Weaviate Cloud
- `WEAVIATE_API_KEY` - Your Weaviate Cloud API key
- `WEAVIATE_URL` - Your Weaviate Cloud cluster URL
- `OPENAI_API_KEY` - OpenAI API key for LLM operations

### Milvus (Alternative)
- `VECTOR_DB_TYPE=milvus` - Set to use Milvus as the vector database (alternative)
- `MILVUS_URI` - URI for Milvus connection (e.g., `milvus_demo.db` for local, `http://localhost:19530` for server)
- `MILVUS_TOKEN` - Authentication token (optional, for Milvus Cloud)
- `OPENAI_API_KEY` - OpenAI API key for LLM operations

### General
- `VECTOR_DB_TYPE` - Set to `weaviate-local` (default), `weaviate`, `milvus`, or `pinecone` to choose the vector database

## Testing

The abstraction includes comprehensive tests organized into separate files:

- `tests/test_vector_db_base.py` - Tests for the abstract base class
- `tests/test_vector_db_weaviate.py` - Tests for Weaviate Cloud implementation
- `tests/test_vector_db_weaviate_local.py` - Tests for local Weaviate implementation
- `tests/test_vector_db_milvus.py` - Tests for Milvus implementation
- `tests/test_vector_db_factory.py` - Tests for the factory function
- `tests/test_vector_db.py` - Compatibility layer (imports from separate test files)

All tests cover:
- Abstract base class behavior
- Vector database implementations
- Factory function
- Error handling
- Lazy initialization (for Milvus)
- Graceful degradation
- Warning suppression for clean test output

All tests use mocking to avoid requiring actual database connections.

## Key Features

### Lazy Initialization (Milvus)
The Milvus implementation uses lazy initialization to avoid import-time connection issues:

```python
def _ensure_client(self):
    """Ensure the client is created, handling import-time issues."""
    if not self._client_created:
        self._create_client()
        self._client_created = True
```

### Graceful Degradation
All implementations include graceful error handling:

```python
def setup(self):
    """Set up Milvus collection if it doesn't exist."""
    self._ensure_client()
    if self.client is None:
        warnings.warn("Milvus client is not available. Setup skipped.")
        return
```

### Warning Suppression
The code includes comprehensive warning filters to maintain clean output:

```python
# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
```

## Local Development Setup

### Weaviate (Recommended)

For local development, Weaviate is now the default and requires no additional setup:

```bash
# Default configuration
VECTOR_DB_TYPE=weaviate-local
WEAVIATE_LOCAL_URL=http://localhost:8080
```

### Local Weaviate (Podman)

For local development with Weaviate:

```bash
# Start local Weaviate
./tools/weaviate-local.sh start

# Configure environment
VECTOR_DB_TYPE=weaviate-local
WEAVIATE_LOCAL_URL=http://localhost:8080
```

### Examples

See the `examples/` directory for complete usage examples:

- `examples/milvus_example.py` - Basic Milvus usage
- `examples/weaviate_local_example.py` - Local Weaviate usage
- `examples/vector_db_usage.py` - General vector database usage
- `examples/milvus_integration_demo.py` - Milvus integration demo
- `examples/switch_to_milvus.py` - Migration guide to Milvus 