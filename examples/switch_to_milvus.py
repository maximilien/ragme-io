#!/usr/bin/env python3
"""
Example: Switching from Weaviate to Milvus in RagMe.

This script demonstrates how to:
1. Switch from Weaviate to Milvus
2. Add documents to Milvus
3. Query documents from Milvus
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def switch_to_milvus():
    """Demonstrate switching to Milvus."""
    
    print("=== Switching to Milvus ===\n")
    
    # Method 1: Set environment variables programmatically
    os.environ["VECTOR_DB_TYPE"] = "milvus"
    os.environ["MILVUS_URI"] = "milvus_demo.db"
    
    print("✅ Environment variables set:")
    print(f"   VECTOR_DB_TYPE: {os.getenv('VECTOR_DB_TYPE')}")
    print(f"   MILVUS_URI: {os.getenv('MILVUS_URI')}")
    
    try:
        # Import RagMe - fix path for examples directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        sys.path.insert(0, project_root)
        
        from src.ragme import RagMe
        
        # Initialize RagMe with Milvus
        print("\n🔄 Initializing RagMe with Milvus...")
        ragme = RagMe(db_type="milvus")
        print("✅ RagMe initialized successfully")
        
        # Check which vector database is being used
        db_type = type(ragme.vector_db).__name__
        print(f"✅ Using vector database: {db_type}")
        
        # Test adding some documents
        print("\n📝 Adding test documents...")
        test_urls = [
            "https://example.com/test1",
            "https://example.com/test2"
        ]
        
        # Note: This would normally fetch real web pages
        # For demo purposes, we'll just show the setup
        print("✅ Document processing setup complete")
        print("   (In a real scenario, this would fetch and process web pages)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error switching to Milvus: {e}")
        return False

def show_configuration_options():
    """Show different configuration options."""
    
    print("\n=== Configuration Options ===\n")
    
    print("1. Environment Variables (.env file):")
    print("   VECTOR_DB_TYPE=milvus")
    print("   MILVUS_URI=milvus_demo.db")
    print("   MILVUS_TOKEN=root:Milvus  # Only for remote Milvus")
    
    print("\n2. Programmatic Configuration:")
    print("   os.environ['VECTOR_DB_TYPE'] = 'milvus'")
    print("   os.environ['MILVUS_URI'] = 'milvus_demo.db'")
    
    print("\n3. RagMe Initialization:")
    print("   ragme = RagMe(db_type='milvus')")
    
    print("\n=== Milvus URI Options ===")
    print("• Local Milvus Lite: milvus_demo.db")
    print("• Remote Milvus: http://localhost:19530")
    print("• Cloud Milvus: https://your-instance.zilliz.com")

if __name__ == "__main__":
    print("🎯 RagMe Milvus Integration Demo\n")
    
    # Show configuration options
    show_configuration_options()
    
    # Demonstrate switching to Milvus
    success = switch_to_milvus()
    
    if success:
        print("\n🎉 Successfully switched to Milvus!")
        print("\nNext steps:")
        print("1. Add your .env file with VECTOR_DB_TYPE=milvus")
        print("2. Run RagMe normally - it will use Milvus")
        print("3. Your documents will be stored in the local Milvus database")
    else:
        print("\n⚠️ Failed to switch to Milvus. Check the error above.") 