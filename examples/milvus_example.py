#!/usr/bin/env python3
"""
Example script demonstrating RagMe with Milvus vector database.

This script shows how to:
1. Configure RagMe to use Milvus
2. Add web pages to the vector database
3. Query the stored content

Prerequisites:
- Set VECTOR_DB_TYPE=milvus in your environment
- Install pymilvus: pip install "pymilvus[model]"
"""

import os
import asyncio
from src.ragme import RagMe

def main():
    # Set environment variables for Milvus
    os.environ["VECTOR_DB_TYPE"] = "milvus"
    os.environ["MILVUS_URI"] = "milvus_demo.db"  # Local Milvus Lite
    
    # Initialize RagMe with Milvus
    print("Initializing RagMe with Milvus...")
    ragme = RagMe(db_type="milvus")
    
    try:
        # Example URLs to process
        urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://en.wikipedia.org/wiki/Machine_learning"
        ]
        
        print(f"Adding {len(urls)} URLs to Milvus...")
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
            "What are the main differences between AI and ML?"
        ]
        
        print("\n🤖 Querying the database:")
        for query in queries:
            print(f"\nQ: {query}")
            response = asyncio.run(ragme.run(query))
            print(f"A: {response[:200]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        ragme.cleanup()
        print("\n🧹 Cleanup completed")

if __name__ == "__main__":
    main() 