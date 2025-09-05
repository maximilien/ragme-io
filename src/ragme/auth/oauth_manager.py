# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
OAuth authentication manager for RAGme.

Handles OAuth flows for Google, GitHub, and Apple providers.
"""

import secrets
import urllib.parse
from typing import Any

import httpx

from ..utils.config_manager import config


class OAuthManager:
    """Manages OAuth authentication flows for different providers."""

    def __init__(self):
        """Initialize the OAuth manager."""
        self.oauth_config = config.get_oauth_config()
        self.providers_config = config.get_oauth_providers()
        
        # Debug logging
        print(f"[DEBUG] OAuthManager initialized")
        print(f"[DEBUG] OAuth config: {self.oauth_config}")
        print(f"[DEBUG] Providers config: {self.providers_config}")

    def get_authorization_url(self, provider: str, state: str | None = None) -> str:
        """
        Get the authorization URL for a specific OAuth provider.

        Args:
            provider: OAuth provider name (google, github, apple)
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for the OAuth provider

        Raises:
            ValueError: If provider is not configured or enabled
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValueError(f"OAuth provider '{provider}' is not configured")

        if not provider_config.get("enabled", False):
            raise ValueError(f"OAuth provider '{provider}' is not enabled")

        client_id = provider_config.get("client_id")
        redirect_uri = provider_config.get("redirect_uri")
        scope = provider_config.get("scope", "")

        if not client_id or not redirect_uri:
            raise ValueError(
                f"OAuth provider '{provider}' is missing required configuration"
            )

        # Generate state if not provided
        if not state:
            state = secrets.token_urlsafe(32)

        # Build authorization URL based on provider
        if provider == "google":
            return self._build_google_auth_url(client_id, redirect_uri, scope, state)
        elif provider == "github":
            return self._build_github_auth_url(client_id, redirect_uri, scope, state)
        elif provider == "apple":
            return self._build_apple_auth_url(client_id, redirect_uri, scope, state)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

    def exchange_code_for_token(
        self, provider: str, code: str, state: str | None = None
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            provider: OAuth provider name
            code: Authorization code from OAuth callback
            state: State parameter for CSRF protection

        Returns:
            Dictionary containing access token and user info

        Raises:
            ValueError: If provider is not configured or token exchange fails
        """
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValueError(f"OAuth provider '{provider}' is not configured")

        client_id = provider_config.get("client_id")
        client_secret = provider_config.get("client_secret")
        redirect_uri = provider_config.get("redirect_uri")

        if not all([client_id, client_secret, redirect_uri]):
            raise ValueError(
                f"OAuth provider '{provider}' is missing required configuration"
            )

        # Exchange code for token based on provider
        if provider == "google":
            return self._exchange_google_token(
                client_id, client_secret, redirect_uri, code
            )
        elif provider == "github":
            return self._exchange_github_token(
                client_id, client_secret, redirect_uri, code
            )
        elif provider == "apple":
            return self._exchange_apple_token(
                client_id, client_secret, redirect_uri, code
            )
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

    def get_user_info(self, provider: str, access_token: str) -> dict[str, Any]:
        """
        Get user information from OAuth provider.

        Args:
            provider: OAuth provider name
            access_token: Access token from OAuth flow

        Returns:
            Dictionary containing user information

        Raises:
            ValueError: If provider is not supported or API call fails
        """
        if provider == "google":
            return self._get_google_user_info(access_token)
        elif provider == "github":
            return self._get_github_user_info(access_token)
        elif provider == "apple":
            return self._get_apple_user_info(access_token)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

    def get_provider_config(self, provider: str) -> dict[str, Any] | None:
        """Get configuration for a specific OAuth provider."""
        return self.providers_config.get(provider)

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if an OAuth provider is enabled."""
        provider_config = self.get_provider_config(provider)
        return provider_config.get("enabled", False) if provider_config else False

    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled OAuth providers."""
        enabled_providers = []
        for provider, config_data in self.providers_config.items():
            if config_data.get("enabled", False):
                enabled_providers.append(provider)
        return enabled_providers

    def _build_google_auth_url(
        self, client_id: str, redirect_uri: str, scope: str, state: str
    ) -> str:
        """Build Google OAuth authorization URL."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    def _build_github_auth_url(
        self, client_id: str, redirect_uri: str, scope: str, state: str
    ) -> str:
        """Build GitHub OAuth authorization URL."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        return (
            f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        )

    def _build_apple_auth_url(
        self, client_id: str, redirect_uri: str, scope: str, state: str
    ) -> str:
        """Build Apple OAuth authorization URL."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "response_type": "code",
            "response_mode": "form_post",
        }
        return (
            f"https://appleid.apple.com/auth/authorize?{urllib.parse.urlencode(params)}"
        )

    async def _exchange_google_token(
        self, client_id: str, client_secret: str, redirect_uri: str, code: str
    ) -> dict[str, Any]:
        """Exchange authorization code for Google access token."""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        # Get user info
        user_info = await self._get_google_user_info(token_data["access_token"])

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "user_info": user_info,
        }

    async def _exchange_github_token(
        self, client_id: str, client_secret: str, redirect_uri: str, code: str
    ) -> dict[str, Any]:
        """Exchange authorization code for GitHub access token."""
        token_url = "https://github.com/login/oauth/access_token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()

        # Get user info
        user_info = await self._get_github_user_info(token_data["access_token"])

        return {"access_token": token_data["access_token"], "user_info": user_info}

    async def _exchange_apple_token(
        self, client_id: str, client_secret: str, redirect_uri: str, code: str
    ) -> dict[str, Any]:
        """Exchange authorization code for Apple access token."""
        token_url = "https://appleid.apple.com/auth/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        # Get user info
        user_info = await self._get_apple_user_info(token_data["access_token"])

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "user_info": user_info,
        }

    async def _get_google_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Google."""
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _get_github_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from GitHub."""
        user_info_url = "https://api.github.com/user"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _get_apple_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Apple."""
        # Apple doesn't provide a direct user info endpoint
        # The user info is typically provided in the ID token during the initial flow
        # For now, we'll return a basic structure
        return {
            "id": "apple_user",
            "email": "user@privaterelay.appleid.com",  # Apple uses private relay
            "name": "Apple User",
        }
