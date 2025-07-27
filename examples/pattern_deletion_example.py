#!/usr/bin/env python3
"""
Example demonstrating pattern-based document deletion in RagMe.

This example shows how to use the new pattern-based deletion feature
to clean up test documents and manage the document collection.
"""

import asyncio

from src.ragme.ragme import RagMe


async def main():
    """Demonstrate pattern-based document deletion."""

    # Initialize RagMe
    ragme = RagMe()

    print("🤖 RagMe Pattern-Based Document Deletion Example")
    print("=" * 50)

    # Example 1: Delete documents with a specific pattern
    print("\n📝 Example 1: Delete documents matching 'test_integration.pdf'")
    query1 = "del all docs with name pattern test_integration.pdf"
    print(f"Query: {query1}")

    try:
        response1 = await ragme.run(query1)
        print(f"Response: {response1}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Delete documents with wildcard pattern
    print("\n📝 Example 2: Delete documents matching 'test_*' pattern")
    query2 = "delete documents matching pattern test_*"
    print(f"Query: {query2}")

    try:
        response2 = await ragme.run(query2)
        print(f"Response: {response2}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 3: Delete documents with regex pattern
    print("\n📝 Example 3: Delete documents with regex pattern")
    query3 = "delete documents matching pattern test.*\\.pdf"
    print(f"Query: {query3}")

    try:
        response3 = await ragme.run(query3)
        print(f"Response: {response3}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 4: List remaining documents
    print("\n📝 Example 4: List remaining documents")
    query4 = "list all documents in the collection"
    print(f"Query: {query4}")

    try:
        response4 = await ragme.run(query4)
        print(f"Response: {response4}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n✅ Pattern-based deletion example completed!")
    print("\n💡 Usage Tips:")
    print("- Use simple patterns like 'test_integration.pdf' for exact matches")
    print("- Use wildcards like 'test_*' for pattern matching")
    print("- Use regex patterns like 'test.*\\.pdf' for complex matching")
    print("- The system automatically handles case-insensitive matching")
    print(
        "- Patterns are matched against document URLs, filenames, and original filenames"
    )


if __name__ == "__main__":
    asyncio.run(main())
