#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Integration Test Runner for RAGme AI

This script runs comprehensive integration tests for both APIs and Agents levels.
It ensures proper setup, execution, and cleanup of test environments.

Usage:
    python tests/integration/run_integration_tests.py [--api] [--agents] [--all]
"""

import argparse
import asyncio
import os
import re
import shutil
import sys
import time
import warnings
from pathlib import Path

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress ResourceWarnings from dependencies
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=".*Enable tracemalloc.*"
)
warnings.filterwarnings("ignore", category=ResourceWarning)

# Suppress Pydantic deprecation warnings
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince211.*"
)

# Suppress asyncio ResourceWarnings by setting environment variable
os.environ["PYTHONWARNINGS"] = "ignore::ResourceWarning"

# Import after adding project root to path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import after adding project root to path
from src.ragme.agents.ragme_agent import RagMeAgent
from src.ragme.ragme import RagMe
from tests.integration.config_manager import (
    get_test_collection_name,
    setup_test_config,
    teardown_test_config,
)
from tests.integration.test_agents import TestAgentsIntegration
from tests.integration.test_apis import TestAPIIntegration


def check_api_keys():
    """Check if real API keys are available for integration tests."""
    print("Checking API keys for integration tests...")

    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if (
        not openai_key
        or openai_key.startswith("fake-")
        or openai_key == "your-openai-api-key-here"
    ):
        print("❌ No valid OpenAI API key found")
        print("   Integration tests require a real OpenAI API key")
        print("   Please set OPENAI_API_KEY in your .env file")
        return False

    print("✅ OpenAI API key found")

    # Check for vector database configuration
    vector_db_type = os.getenv("VECTOR_DB_TYPE", "weaviate-local")
    print(f"📊 Vector database type: {vector_db_type}")

    if vector_db_type == "weaviate":
        weaviate_key = os.getenv("WEAVIATE_API_KEY")
        weaviate_url = os.getenv("WEAVIATE_URL")
        if (
            not weaviate_key
            or weaviate_key.startswith("fake-")
            or weaviate_key == "your-weaviate-api-key-here"
        ):
            print("❌ No valid Weaviate API key found")
            print("   Please set WEAVIATE_API_KEY in your .env file")
            return False
        if not weaviate_url or weaviate_url.startswith("fake-"):
            print("❌ No valid Weaviate URL found")
            print("   Please set WEAVIATE_URL in your .env file")
            return False
        print("✅ Weaviate API key and URL found")

    elif vector_db_type == "weaviate-local":
        print("✅ Using local Weaviate (no API key required)")

    elif vector_db_type == "milvus":
        milvus_uri = os.getenv("MILVUS_URI")
        if not milvus_uri:
            print("❌ No Milvus URI found")
            print("   Please set MILVUS_URI in your .env file")
            return False
        print("✅ Milvus URI found")

    return True


def check_services_available():
    """Check if required services are running."""
    import requests

    services = {"API": "http://localhost:8021", "MCP": "http://localhost:8022"}

    print("Checking service availability...")
    available_services = []

    for name, url in services.items():
        try:
            if name == "API":
                # API service has /config endpoint
                response = requests.get(f"{url}/config", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name} service is available at {url}")
                    available_services.append(name)
                else:
                    print(f"❌ {name} service returned status {response.status_code}")
            elif name == "MCP":
                # MCP service has /tool/process_pdf endpoint
                response = requests.get(f"{url}/tool/process_pdf", timeout=5)
                if (
                    response.status_code == 405
                ):  # Method Not Allowed is expected for GET
                    print(f"✅ {name} service is available at {url}")
                    available_services.append(name)
                else:
                    print(f"❌ {name} service returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {name} service is not available at {url}: {e}")

    return available_services


def run_api_tests():
    """Run API integration tests."""
    print("\n" + "=" * 60)
    print("RUNNING API INTEGRATION TESTS")
    print("=" * 60)

    # Setup test configuration
    if not setup_test_config():
        print("❌ Failed to setup test configuration")
        return False

    # Set environment variable for test collection to ensure it overrides config
    original_collection_name = os.environ.get("VECTOR_DB_TEXT_COLLECTION_NAME")
    os.environ["VECTOR_DB_TEXT_COLLECTION_NAME"] = get_test_collection_name()
    print(f"🔧 Set VECTOR_DB_TEXT_COLLECTION_NAME={get_test_collection_name()}")

    # Restart backend services to pick up the new test configuration
    print("🔄 Restarting backend services with test configuration...")
    import subprocess

    try:
        # Ensure environment variables are passed to the subprocess
        env = os.environ.copy()
        result = subprocess.run(
            ["./start.sh", "restart-backend"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
            env=env,
        )
        if result.returncode == 0:
            print("✅ Backend services restarted successfully")
            # Wait for services to be ready
            time.sleep(3)
        else:
            print(f"❌ Failed to restart backend services: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Timeout while restarting backend services")
        return False
    except Exception as e:
        print(f"❌ Error restarting backend services: {e}")
        return False

    try:
        # Create test instance and run tests directly
        test_instance = TestAPIIntegration()

        # Manually setup the test instance
        test_instance.base_url = "http://localhost:8021"
        test_instance.mcp_url = "http://localhost:8022"
        test_instance.collection_name = get_test_collection_name()

        # Configure retry strategy for API calls
        test_instance.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        test_instance.session.mount("http://", adapter)
        test_instance.session.mount("https://", adapter)

        # Test data
        test_instance.test_url = "https://maximilien.org"
        test_instance.test_pdf_path = "tests/fixtures/pdfs/ragme-ai.pdf"
        test_instance.test_queries = {
            "maximilien": "who is Maximilien?",
            "ragme": "what is the RAGme-ai project?",
        }

        try:
            # Run individual test steps
            print("\n1. Testing empty collection...")
            test_instance.test_step_0_empty_collection()

            print("\n2. Testing queries with empty collection...")
            test_instance.test_step_1_queries_with_empty_collection()

            print("\n3. Testing document addition and querying...")
            test_instance.test_step_2_add_documents_and_query()

            print("\n4. Testing document removal and verification...")
            test_instance.test_step_3_remove_documents_and_verify()

            print("\n5. Running complete scenario test...")
            test_instance.test_complete_scenario()

            print("\n✅ All API integration tests passed!")
            return True

        except Exception as e:
            print(f"\n❌ API integration tests failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            test_instance.cleanup_test_collection()
            # Clean up VDB connections to prevent ResourceWarnings
            if hasattr(test_instance, "ragme") and test_instance.ragme:
                test_instance.ragme.cleanup()
    finally:
        # Always restore configuration and environment
        if "original_collection_name" in locals():
            if original_collection_name is not None:
                os.environ["VECTOR_DB_TEXT_COLLECTION_NAME"] = original_collection_name
                print(
                    f"🔧 Restored VECTOR_DB_TEXT_COLLECTION_NAME={original_collection_name}"
                )
            else:
                os.environ.pop("VECTOR_DB_TEXT_COLLECTION_NAME", None)
                print("🔧 Removed VECTOR_DB_TEXT_COLLECTION_NAME from environment")
        teardown_test_config()


async def run_agent_tests():
    """Run Agent integration tests."""
    print("\n" + "=" * 60)
    print("RUNNING AGENT INTEGRATION TESTS")
    print("=" * 60)

    # Setup test configuration
    if not setup_test_config():
        print("❌ Failed to setup test configuration")
        return False

    # Set environment variable for test collection to ensure it overrides config
    original_collection_name = os.environ.get("VECTOR_DB_TEXT_COLLECTION_NAME")
    os.environ["VECTOR_DB_TEXT_COLLECTION_NAME"] = get_test_collection_name()
    print(f"🔧 Set VECTOR_DB_TEXT_COLLECTION_NAME={get_test_collection_name()}")

    # Restart backend services to pick up the new test configuration
    print("🔄 Restarting backend services with test configuration...")
    import subprocess

    try:
        # Ensure environment variables are passed to the subprocess
        env = os.environ.copy()
        result = subprocess.run(
            ["./start.sh", "restart-backend"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
            env=env,
        )
        if result.returncode == 0:
            print("✅ Backend services restarted successfully")
            # Wait for services to be ready
            time.sleep(3)
        else:
            print(f"❌ Failed to restart backend services: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Timeout while restarting backend services")
        return False
    except Exception as e:
        print(f"❌ Error restarting backend services: {e}")
        return False

    try:
        # Create test instance and run tests directly
        test_instance = TestAgentsIntegration()

        # Manually setup the test instance
        test_instance.base_url = "http://localhost:8021"
        test_instance.mcp_url = "http://localhost:8022"
        test_instance.collection_name = get_test_collection_name()

        # Configure retry strategy for MCP calls
        test_instance.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        test_instance.session.mount("http://", adapter)
        test_instance.session.mount("https://", adapter)

        # Test data
        test_instance.test_url = "https://maximilien.org"
        test_instance.test_pdf_path = "tests/fixtures/pdfs/ragme-ai.pdf"
        test_instance.test_queries = {
            "maximilien": "who is Maximilien?",
            "ragme": "what is the RAGme-ai project?",
        }

        # Initialize RagMe and RagMeAgent
        test_instance.ragme = RagMe()
        test_instance.agent = RagMeAgent(test_instance.ragme)

        try:
            # Run individual test steps
            print("\n1. Testing empty collection...")
            await test_instance.test_step_0_empty_collection()

            print("\n2. Testing queries with empty collection...")
            await test_instance.test_step_1_queries_with_empty_collection()

            print("\n3. Testing document addition and querying...")
            await test_instance.test_step_2_add_documents_and_query()

            print("\n4. Testing document removal and verification...")
            await test_instance.test_step_3_remove_documents_and_verify()

            print("\n5. Testing agent functionality...")
            await test_instance.test_agent_functionality()

            print("\n6. Running complete scenario test...")
            await test_instance.test_complete_scenario()

            print("\n✅ All Agent integration tests passed!")
            return True

        except Exception as e:
            print(f"\n❌ Agent integration tests failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            test_instance.cleanup_test_collection()
            # Clean up VDB connections to prevent ResourceWarnings
            if hasattr(test_instance, "ragme") and test_instance.ragme:
                test_instance.ragme.cleanup()
    finally:
        # Always restore configuration and environment
        if "original_collection_name" in locals():
            if original_collection_name is not None:
                os.environ["VECTOR_DB_TEXT_COLLECTION_NAME"] = original_collection_name
                print(
                    f"🔧 Restored VECTOR_DB_TEXT_COLLECTION_NAME={original_collection_name}"
                )
            else:
                os.environ.pop("VECTOR_DB_TEXT_COLLECTION_NAME", None)
                print("🔧 Removed VECTOR_DB_TEXT_COLLECTION_NAME from environment")
        teardown_test_config()


def run_pytest_tests(test_type):
    """Run tests using pytest framework."""
    print(f"\nRunning {test_type} tests with pytest...")

    if test_type == "api":
        test_file = "tests/integration/test_apis.py"
    elif test_type == "agents":
        test_file = "tests/integration/test_agents.py"
    else:
        test_file = "tests/integration/"

    # Run pytest with verbose output
    result = pytest.main([test_file, "-v", "--tb=short", "--capture=no"])

    return result == 0


def main():
    """Main function to run integration tests."""
    parser = argparse.ArgumentParser(description="Run RAGme AI integration tests")
    parser.add_argument("--api", action="store_true", help="Run API integration tests")
    parser.add_argument(
        "--agents", action="store_true", help="Run Agent integration tests"
    )
    parser.add_argument("--all", action="store_true", help="Run all integration tests")
    parser.add_argument("--pytest", action="store_true", help="Use pytest framework")
    parser.add_argument(
        "--skip-api-check", action="store_true", help="Skip API key validation"
    )

    args = parser.parse_args()

    # Default to running all tests if no specific option is provided
    if not any([args.api, args.agents, args.all]):
        args.all = True

    print("RAGme AI Integration Test Runner")
    print("=" * 40)

    # Check if test PDF exists
    test_pdf_path = "tests/fixtures/pdfs/ragme-ai.pdf"
    if not os.path.exists(test_pdf_path):
        print(f"❌ Test PDF not found: {test_pdf_path}")
        print(
            "Please ensure the test PDF file exists before running integration tests."
        )
        return 1

    # Check API keys (unless skipped)
    if not args.skip_api_check:
        if not check_api_keys():
            print("\n❌ API key validation failed.")
            print("Integration tests require valid API keys to make real API calls.")
            print("You can:")
            print("  1. Set valid API keys in your .env file")
            print("  2. Use --skip-api-check to run tests anyway (may fail)")
            return 1

    # Check service availability
    available_services = check_services_available()

    if not available_services:
        print("\n❌ No required services are available.")
        print("Please start the RAGme services before running integration tests:")
        print("  ./start.sh")
        return 1

    # Run tests based on arguments
    success = True

    if args.pytest:
        # Use pytest framework
        if args.api or args.all:
            success &= run_pytest_tests("api")

        if args.agents or args.all:
            success &= run_pytest_tests("agents")
    else:
        # Use custom test runner
        if args.api or args.all:
            success &= run_api_tests()

        if args.agents or args.all:
            success &= asyncio.run(run_agent_tests())

    # Print summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)

    if success:
        print("✅ All integration tests completed successfully!")
        return 0
    else:
        print("❌ Some integration tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
