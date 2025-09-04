# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Session management for RAGme authentication.

Handles user sessions, JWT tokens, and session storage.
"""

import secrets
import time
from typing import Any

import jwt

from ..utils.config_manager import config


class SessionManager:
    """Manages user sessions and authentication tokens."""

    def __init__(self):
        """Initialize the session manager."""
        self.session_config = config.get_session_config()
        self.secret_key = self.session_config.get(
            "secret_key", "your-secret-key-change-in-production"
        )
        self.max_age_seconds = self.session_config.get(
            "max_age_seconds", 86400
        )  # 24 hours

    def create_session(
        self, user_info: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        """
        Create a new user session.

        Args:
            user_info: User information from OAuth provider
            provider: OAuth provider name

        Returns:
            Dictionary containing session data and JWT token
        """
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()
        expires_at = current_time + self.max_age_seconds

        # Create session data
        session_data = {
            "session_id": session_id,
            "user_id": user_info.get("id", user_info.get("sub", "")),
            "email": user_info.get("email", ""),
            "name": user_info.get("name", user_info.get("login", "")),
            "provider": provider,
            "created_at": current_time,
            "expires_at": expires_at,
            "last_activity": current_time,
        }

        # Create JWT token
        jwt_payload = {
            "session_id": session_id,
            "user_id": session_data["user_id"],
            "email": session_data["email"],
            "name": session_data["name"],
            "provider": provider,
            "exp": expires_at,
            "iat": current_time,
        }

        token = jwt.encode(jwt_payload, self.secret_key, algorithm="HS256")

        return {
            "session_id": session_id,
            "token": token,
            "user": {
                "id": session_data["user_id"],
                "email": session_data["email"],
                "name": session_data["name"],
                "provider": provider,
            },
            "expires_at": expires_at,
        }

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a JWT token and return session data.

        Args:
            token: JWT token to validate

        Returns:
            Session data if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            current_time = time.time()

            # Check if token is expired
            if payload.get("exp", 0) < current_time:
                return None

            return {
                "session_id": payload.get("session_id"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "provider": payload.get("provider"),
                "expires_at": payload.get("exp"),
            }
        except jwt.InvalidTokenError:
            return None

    def refresh_token(self, token: str) -> dict[str, Any] | None:
        """
        Refresh a JWT token if it's still valid.

        Args:
            token: Current JWT token

        Returns:
            New session data with refreshed token, None if current token is invalid
        """
        session_data = self.validate_token(token)
        if not session_data:
            return None

        # Create new token with extended expiration
        current_time = time.time()
        new_expires_at = current_time + self.max_age_seconds

        jwt_payload = {
            "session_id": session_data["session_id"],
            "user_id": session_data["user_id"],
            "email": session_data["email"],
            "name": session_data["name"],
            "provider": session_data["provider"],
            "exp": new_expires_at,
            "iat": current_time,
        }

        new_token = jwt.encode(jwt_payload, self.secret_key, algorithm="HS256")

        return {
            "session_id": session_data["session_id"],
            "token": new_token,
            "user": {
                "id": session_data["user_id"],
                "email": session_data["email"],
                "name": session_data["name"],
                "provider": session_data["provider"],
            },
            "expires_at": new_expires_at,
        }

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if session was invalidated, False otherwise
        """
        # In a production system, you would store session IDs in a database
        # and mark them as invalidated. For now, we'll just return True.
        # The JWT token will naturally expire based on its expiration time.
        return True

    def get_session_cookie_config(self) -> dict[str, Any]:
        """Get session cookie configuration."""
        return {
            "max_age": self.max_age_seconds,
            "secure": False,  # Keep False for localhost development
            "httponly": False,  # Set to False to allow JavaScript access
            "samesite": "lax",  # Use "lax" for localhost
            # Don't set domain to allow cookie to work for the specific host
            "path": "/",  # Make cookie available for all paths
        }
