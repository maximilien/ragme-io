# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Authentication module for RAGme.

This module provides OAuth authentication functionality for Google, GitHub, and Apple providers.
"""

from .oauth_manager import OAuthManager
from .session_manager import SessionManager
from .user_manager import UserManager

__all__ = ["OAuthManager", "SessionManager", "UserManager"]
