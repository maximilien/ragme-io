#!/bin/bash

# Add some test .env variables
export OPENAI_API_KEY=fake-openai-key
export WEAVIATE_API_KEY=fake-weaviate-key
export WEAVIATE_URL=fake-weaviate-url.com

# Run all tests with the correct PYTHONPATH and robustly suppress Pydantic deprecation warnings
PYTHONWARNINGS="ignore:PydanticDeprecatedSince20" PYTHONPATH=src uv run pytest -v 