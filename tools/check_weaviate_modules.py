#!/usr/bin/env python3
"""
Script to check available Weaviate modules
"""

import os
import requests
import dotenv

# Load environment variables
dotenv.load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

if not WEAVIATE_URL or not WEAVIATE_API_KEY:
    print("Error: WEAVIATE_URL and WEAVIATE_API_KEY must be set in .env file")
    exit(1)

# Ensure URL has proper scheme
if not WEAVIATE_URL.startswith(('http://', 'https://')):
    WEAVIATE_URL = f"https://{WEAVIATE_URL}"

# Remove trailing slash if present
WEAVIATE_URL = WEAVIATE_URL.rstrip('/')

try:
    # Query Weaviate metadata
    headers = {
        "Authorization": f"Bearer {WEAVIATE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{WEAVIATE_URL}/v1/meta", headers=headers)
    
    if response.status_code == 200:
        meta = response.json()
        print("Available Weaviate modules:")
        print("=" * 40)
        
        if 'modules' in meta:
            for module_name, module_info in meta['modules'].items():
                print(f"✓ {module_name}")
                if 'version' in module_info:
                    print(f"  Version: {module_info['version']}")
        else:
            print("No modules information found")
            
        print("\nAvailable vectorizers:")
        print("=" * 40)
        if 'vectorizers' in meta:
            for vectorizer in meta['vectorizers']:
                print(f"✓ {vectorizer}")
        else:
            print("No vectorizers information found")
            
    else:
        print(f"Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Error connecting to Weaviate: {e}") 