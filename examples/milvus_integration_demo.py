#!/usr/bin/env python3
"""
Milvus Integration Demo for RagMe

This script demonstrates how to use RagMe with Milvus as the vector database backend.

- This is NOT a test file. It is for manual/integration demonstration only.
- Pytest should NOT collect or run this file.

How to run:
    python examples/milvus_integration_demo.py

Requirements:
    - pymilvus must be installed (pip install "pymilvus[model]")
    - Milvus Lite will be used locally by default

"""

import os
import sys

from pymilvus import MilvusClient


def test_milvus_basic():
    """Test basic Milvus functionality."""

    print("=== Testing Basic Milvus Functionality ===\n")

    try:
        # Create client
        client = MilvusClient(uri="milvus_demo.db")
        print("✅ Milvus client created successfully")

        # Test collection creation
        test_collection = "ragme_test"

        if not client.has_collection(test_collection):
            client.create_collection(
                collection_name=test_collection,
                dimension=1536,
                primary_field_name="id",
                vector_field_name="vector",
            )
            print("✅ Test collection created")

        # Insert test data
        data = [
            {"id": 1, "text": "Hello Milvus!", "vector": [0.1] * 1536},
            {"id": 2, "text": "Testing RagMe with Milvus", "vector": [0.2] * 1536},
        ]
        client.insert(test_collection, data)
        print("✅ Test data inserted")

        # Query test data
        results = client.query(test_collection, filter="id == 1")
        print(f"✅ Query successful: {len(results)} results")

        # Cleanup
        client.drop_collection(test_collection)
        print("✅ Test collection dropped")

        client.close()
        print("✅ Client closed successfully")

        return True

    except Exception as e:
        print(f"❌ Basic Milvus test failed: {e}")
        return False


def test_ragme_integration():
    """Test RagMe integration with Milvus."""

    print("\n=== Testing RagMe Integration ===\n")

    try:
        # Set environment variables
        os.environ["VECTOR_DB_TYPE"] = "milvus"
        os.environ["MILVUS_URI"] = "milvus_demo.db"

        print(f"VECTOR_DB_TYPE: {os.getenv('VECTOR_DB_TYPE')}")
        print(f"MILVUS_URI: {os.getenv('MILVUS_URI')}")

        # Import RagMe - fix path for examples directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        sys.path.insert(0, project_root)

        from src.ragme.ragme import RagMe

        # Initialize RagMe with Milvus
        ragme = RagMe(db_type="milvus")
        print("✅ RagMe initialized with Milvus")

        # Test vector database creation
        db = ragme.vector_db
        print(f"✅ Vector database created: {type(db).__name__}")

        # Test setup
        db.setup()
        print("✅ Database setup completed")

        return True

    except Exception as e:
        print(f"❌ RagMe integration failed: {e}")
        return False


if __name__ == "__main__":
    print("=== Final Milvus Configuration Test ===\n")

    # Test basic Milvus functionality
    milvus_success = test_milvus_basic()

    # Test RagMe integration
    ragme_success = test_ragme_integration()

    print("\n=== Test Results ===")
    print(f"Basic Milvus: {'✅ PASS' if milvus_success else '❌ FAIL'}")
    print(f"RagMe Integration: {'✅ PASS' if ragme_success else '❌ FAIL'}")

    if milvus_success and ragme_success:
        print("\n🎉 All tests passed! Milvus is ready to use with RagMe.")
        print("\nTo use Milvus with RagMe:")
        print("1. Set VECTOR_DB_TYPE=milvus in your .env file")
        print("2. Set MILVUS_URI=milvus_demo.db for local storage")
        print("3. Run RagMe normally - it will use Milvus as the vector database")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
