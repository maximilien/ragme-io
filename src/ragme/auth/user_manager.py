# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
User management for RAGme authentication.

Handles user data storage and retrieval.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class UserManager:
    """Manages user data and storage."""

    def __init__(self):
        """Initialize the user manager."""
        self.users_file = Path("data/users.json")
        self.users_file.parent.mkdir(exist_ok=True)
        self._load_users()

    def _load_users(self) -> None:
        """Load users from storage file."""
        if self.users_file.exists():
            try:
                with open(self.users_file, encoding="utf-8") as f:
                    self.users = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.users = {}
        else:
            self.users = {}

    def _save_users(self) -> None:
        """Save users to storage file."""
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Error saving users: {e}")

    def create_or_update_user(
        self, user_info: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        """
        Create or update a user record.

        Args:
            user_info: User information from OAuth provider
            provider: OAuth provider name

        Returns:
            User record with additional metadata
        """
        user_id = user_info.get("id", user_info.get("sub", ""))
        email = user_info.get("email", "")
        name = user_info.get("name", user_info.get("login", ""))

        # Create or update user record
        if user_id in self.users:
            # Update existing user
            user = self.users[user_id]
            user["email"] = email
            user["name"] = name
            user["last_login"] = datetime.utcnow().isoformat()
            user["login_count"] = user.get("login_count", 0) + 1
        else:
            # Create new user
            user = {
                "id": user_id,
                "email": email,
                "name": name,
                "provider": provider,
                "created_at": datetime.utcnow().isoformat(),
                "last_login": datetime.utcnow().isoformat(),
                "login_count": 1,
                "is_active": True,
            }

        self.users[user_id] = user
        self._save_users()

        return user

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User record if found, None otherwise
        """
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Get user by email address.

        Args:
            email: Email address

        Returns:
            User record if found, None otherwise
        """
        for user in self.users.values():
            if user.get("email") == email:
                return user
        return None

    def list_users(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of user records
        """
        user_list = list(self.users.values())
        return user_list[offset : offset + limit]

    def update_user_activity(self, user_id: str) -> bool:
        """
        Update user's last activity timestamp.

        Args:
            user_id: User ID

        Returns:
            True if user was found and updated, False otherwise
        """
        if user_id in self.users:
            self.users[user_id]["last_activity"] = datetime.utcnow().isoformat()
            self._save_users()
            return True
        return False

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            True if user was found and deactivated, False otherwise
        """
        if user_id in self.users:
            self.users[user_id]["is_active"] = False
            self.users[user_id]["deactivated_at"] = datetime.utcnow().isoformat()
            self._save_users()
            return True
        return False

    def get_user_stats(self) -> dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dictionary containing user statistics
        """
        total_users = len(self.users)
        active_users = sum(
            1 for user in self.users.values() if user.get("is_active", True)
        )

        # Count users by provider
        provider_counts = {}
        for user in self.users.values():
            provider = user.get("provider", "unknown")
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "provider_counts": provider_counts,
        }
