#!/usr/bin/env python3
"""
Example script demonstrating RagMe with local Weaviate vector database.

This script shows how to:
1. Start local Weaviate using Podman
2. Configure RagMe to use local Weaviate
3. Add web pages to the vector database
4. Query the stored content

Prerequisites:
- Podman and Podman Compose installed
- Set VECTOR_DB_TYPE=weaviate-local in your environment
- Start local Weaviate: ./tools/weaviate-local.sh start
"""

import asyncio
import os
import time

from src.ragme import RagMe


def wait_for_weaviate():
    """Wait for local Weaviate to be ready."""
    import requests

    print("⏳ Waiting for local Weaviate to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                "http://localhost:8080/v1/.well-known/ready", timeout=5
            )
            if response.status_code == 200:
                print("✅ Local Weaviate is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"   Attempt {attempt + 1}/{max_attempts}...")
        time.sleep(2)

    print("❌ Local Weaviate failed to start within expected time")
    return False


def main():
    # Set environment variables for local Weaviate
    os.environ["VECTOR_DB_TYPE"] = "weaviate-local"
    os.environ["WEAVIATE_LOCAL_URL"] = "http://localhost:8080"

    # Wait for Weaviate to be ready
    if not wait_for_weaviate():
        print("❌ Please start local Weaviate first:")
        print("   ./tools/weaviate-local.sh start")
        return

    # Initialize RagMe with local Weaviate
    print("🚀 Initializing RagMe with local Weaviate...")
    ragme = RagMe(db_type="weaviate-local")

    try:
        # Example URLs to process
        urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://en.wikipedia.org/wiki/Machine_learning",
        ]

        print(f"📄 Adding {len(urls)} URLs to local Weaviate...")
        ragme.write_webpages_to_weaviate(urls)
        print("✅ URLs added successfully!")

        # List documents to verify
        print("\n📋 Documents in database:")
        docs = ragme.list_documents(limit=5)
        for i, doc in enumerate(docs, 1):
            print(f"{i}. {doc['url']} - {len(doc['text'])} chars")

        # Example queries
        queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What are the main differences between AI and ML?",
        ]

        print("\n🤖 Querying the database:")
        for query in queries:
            print(f"\nQ: {query}")
            response = asyncio.run(ragme.run(query))
            print(f"A: {response[:200]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print(
            "   1. Make sure local Weaviate is running: ./tools/weaviate-local.sh status"
        )
        print("   2. Check Weaviate logs: ./tools/weaviate-local.sh logs")
        print("   3. Restart Weaviate: ./tools/weaviate-local.sh restart")
    finally:
        ragme.cleanup()
        print("\n🧹 Cleanup completed")


if __name__ == "__main__":
    main()
