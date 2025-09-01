#!/usr/bin/env python3
"""
Fast integration test for image query functionality.
Tests the intelligent routing of "show me a dog" queries to image search.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import requests

from src.ragme.agents.ragme_agent import RagMeAgent
from src.ragme.ragme import RagMe
from src.ragme.utils.config_manager import config


async def test_image_query_intelligence():
    """Test intelligent image query routing with Yorkshire terrier fixture."""
    print("🧪 Testing intelligent image query routing...")

    # Initialize RagMe and agent
    ragme = RagMe()
    agent = RagMeAgent(ragme)

    # Test image path
    image_path = "tests/fixtures/images/yorkshire-terrier.jpg"
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False

    # Get test collection name
    collection_name = f"test_image_query_{int(time.time())}"

    try:
        # Add Yorkshire terrier image to collection
        print(f"📸 Adding Yorkshire terrier image to collection '{collection_name}'...")
        with open(image_path, "rb") as f:
            files = {"file": ("yorkshire-terrier.jpg", f, "image/jpeg")}
            response = requests.post(
                "http://localhost:8000/images/add",
                files=files,
                data={"collection_name": collection_name},
            )

        if response.status_code != 200:
            print(f"❌ Failed to add image: {response.status_code} - {response.text}")
            return False

        add_result = response.json()
        if add_result.get("status") != "success":
            print(f"❌ Image addition failed: {add_result}")
            return False

        print("✅ Image added successfully")

        # Wait for processing
        print("⏳ Waiting for image processing...")
        time.sleep(3)

        # Test intelligent routing for image queries
        print("🔍 Testing 'show me a dog' query...")
        image_query = "show me a dog"
        response = await agent.run(image_query)

        print(f"📝 Agent response: {response}")

        # Verify the response contains image-specific content
        if "[IMAGE:" not in response:
            print("❌ Response should contain image tags")
            return False

        if "yorkshire" not in response.lower() and "terrier" not in response.lower():
            print("❌ Response should mention Yorkshire terrier")
            return False

        # Verify it's not a generic text response
        generic_responses = [
            "a dog is a domesticated mammal",
            "dogs come in various breeds",
            "you can find images of dogs on websites",
        ]
        for generic in generic_responses:
            if generic.lower() in response.lower():
                print(f"❌ Response should not be generic text: {generic}")
                return False

        print("✅ Intelligent image query routing working correctly!")

        # Clean up test image
        print("🧹 Cleaning up test image...")
        list_response = requests.get(
            "http://localhost:8000/images/list",
            params={"collection_name": collection_name},
        )

        if list_response.status_code == 200:
            images = list_response.json().get("images", [])
            for img in images:
                if "yorkshire" in img.get("filename", "").lower():
                    delete_response = requests.delete(
                        "http://localhost:8000/images/delete",
                        params={
                            "collection_name": collection_name,
                            "image_id": img["id"],
                        },
                    )
                    if delete_response.status_code == 200:
                        print(f"✅ Cleaned up test image: {img['filename']}")
                    else:
                        print(f"⚠️ Failed to clean up test image: {img['filename']}")

        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting fast image query integration test...")

    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not responding at http://localhost:8000")
            return 1
        print("✅ API is running")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API at http://localhost:8000")
        print("   Make sure the API is running with: ./start.sh")
        return 1

    # Run the test
    success = await test_image_query_intelligence()

    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
