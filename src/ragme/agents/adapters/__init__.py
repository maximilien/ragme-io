# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Agent adapters for different frameworks.

This module provides adapter classes that wrap different agent frameworks
to provide a unified AbstractAgent interface.
"""

from .custom_adapter import CustomAdapter
from .llamaindex_adapter import LlamaIndexAdapter
from .openai_adapter import OpenAIAdapter

__all__ = [
    "OpenAIAdapter",
    "LlamaIndexAdapter",
    "CustomAdapter",
]
