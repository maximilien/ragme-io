#!/bin/bash

# Run all tests with the correct PYTHONPATH and robustly suppress Pydantic deprecation warnings
PYTHONWARNINGS="ignore:PydanticDeprecatedSince20" PYTHONPATH=. pytest -v 