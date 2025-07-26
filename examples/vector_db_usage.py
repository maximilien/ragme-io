# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Example demonstrating the vector database agnostic RagMe class.

This example shows how to:
1. Use RagMe with the default Weaviate vector database
2. Use RagMe with a custom vector database instance
3. Switch between different vector database types (when implemented)
"""

import asyncio

from src.ragme.ragme import RagMe
from src.ragme.vector_db import WeaviateVectorDatabase, create_vector_database


def example_default_weaviate():
    """Example using RagMe with default Weaviate vector database."""
    print("=== Example 1: Using RagMe with default Weaviate ===")

    # This will use Weaviate by default
    ragme = RagMe()

    # Add some URLs
    urls = ["https://example.com", "https://example.org"]
    ragme.write_webpages_to_weaviate(urls)
    print(f"Added {len(urls)} URLs to vector database")

    # List documents
    documents = ragme.list_documents(limit=5)
    print(f"Found {len(documents)} documents in database")

    # Clean up
    ragme.cleanup()
    print("Cleaned up resources\n")


def example_custom_vector_db():
    """Example using RagMe with a custom vector database instance."""
    print("=== Example 2: Using RagMe with custom vector database ===")

    # Create a custom Weaviate vector database instance
    custom_db = WeaviateVectorDatabase("CustomCollection")

    # Pass it to RagMe
    ragme = RagMe(vector_db=custom_db)

    # Add some JSON data
    json_data = {
        "title": "Sample Document",
        "content": "This is a sample document for testing.",
        "filename": "sample.json",
    }
    metadata = {"source": "example", "type": "json"}

    ragme.write_json_to_weaviate(json_data, metadata)
    print("Added JSON data to custom collection")

    # List documents
    documents = ragme.list_documents(limit=5)
    print(f"Found {len(documents)} documents in custom collection")

    # Clean up
    ragme.cleanup()
    print("Cleaned up resources\n")


def example_factory_pattern():
    """Example using the factory pattern to create vector databases."""
    print("=== Example 3: Using factory pattern ===")

    # Create Weaviate database using factory
    weaviate_db = create_vector_database("weaviate", "FactoryCollection")

    # Use it with RagMe
    ragme = RagMe(vector_db=weaviate_db)

    # Add some content
    ragme.write_json_to_weaviate(
        {
            "title": "Factory Example",
            "content": "Created using factory pattern",
            "filename": "factory.json",
        }
    )

    print("Added content using factory-created database")

    # Clean up
    ragme.cleanup()
    print("Cleaned up resources\n")


async def example_query():
    """Example of querying the RAG system."""
    print("=== Example 4: Querying the RAG system ===")

    ragme = RagMe()

    # Add some content first
    ragme.write_json_to_weaviate(
        {
            "title": "AI and Machine Learning",
            "content": "Artificial Intelligence and Machine Learning are transforming industries worldwide.",
            "filename": "ai_ml.json",
        }
    )

    # Query the system
    query = "What is artificial intelligence?"
    try:
        response = await ragme.run(query)
        print(f"Query: {query}")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error querying: {e}")

    # Clean up
    ragme.cleanup()
    print("Cleaned up resources\n")


def example_unsupported_database():
    """Example showing error handling for unsupported database types."""
    print("=== Example 5: Error handling for unsupported databases ===")

    try:
        # This will raise a ValueError
        create_vector_database("unsupported_db")
    except ValueError as e:
        print(f"Expected error: {e}")

    print("Error handled gracefully\n")


if __name__ == "__main__":
    print("Vector Database Agnostic RagMe Examples")
    print("=" * 50)

    # Run examples
    example_default_weaviate()
    example_custom_vector_db()
    example_factory_pattern()
    example_unsupported_database()

    # Run async example
    asyncio.run(example_query())

    print("All examples completed!")
