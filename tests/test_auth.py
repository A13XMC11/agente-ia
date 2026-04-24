"""
Tests for authentication module.

Tests JWT token creation, validation, password hashing, etc.
"""

import pytest
from datetime import timedelta
from jose import JWTError

from seguridad.auth import AuthManager


class TestAuthManager:
    """Tests for AuthManager."""

    @pytest.fixture
    def auth_manager(self):
        """Create auth manager instance."""
        return AuthManager(
            jwt_secret="test-secret-key-very-long",
            jwt_algorithm="HS256",
            jwt_expiration_hours=24,
        )

    def test_hash_password(self, auth_manager):
        """Test password hashing."""
        password = "mySecurePassword123!"
        hashed = auth_manager.hash_password(password)

        assert hashed != password
        assert auth_manager.verify_password(password, hashed)

    def test_hash_password_different_hashes(self, auth_manager):
        """Test that same password produces different hashes."""
        password = "mySecurePassword123!"
        hash1 = auth_manager.hash_password(password)
        hash2 = auth_manager.hash_password(password)

        assert hash1 != hash2
        assert auth_manager.verify_password(password, hash1)
        assert auth_manager.verify_password(password, hash2)

    def test_verify_password_wrong_password(self, auth_manager):
        """Test password verification with wrong password."""
        password = "mySecurePassword123!"
        wrong_password = "wrongPassword123!"
        hashed = auth_manager.hash_password(password)

        assert not auth_manager.verify_password(wrong_password, hashed)

    def test_create_access_token(self, auth_manager):
        """Test JWT token creation."""
        token = auth_manager.create_access_token(
            user_id="user-123",
            client_id="client-456",
            role="admin",
            email="user@example.com",
        )

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_token(self, auth_manager):
        """Test JWT token verification."""
        user_id = "user-123"
        client_id = "client-456"
        role = "admin"
        email = "user@example.com"

        token = auth_manager.create_access_token(
            user_id=user_id,
            client_id=client_id,
            role=role,
            email=email,
        )

        claims = await auth_manager.verify_token(token)

        assert claims["user_id"] == user_id
        assert claims["client_id"] == client_id
        assert claims["role"] == role
        assert claims["email"] == email

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_manager):
        """Test token verification with invalid token."""
        with pytest.raises(JWTError):
            await auth_manager.verify_token("invalid-token")

    @pytest.mark.asyncio
    async def test_verify_token_with_wrong_secret(self, auth_manager):
        """Test token verification with different secret."""
        token = auth_manager.create_access_token(
            user_id="user-123",
            client_id="client-456",
            role="admin",
            email="user@example.com",
        )

        # Create new manager with different secret
        wrong_auth = AuthManager(
            jwt_secret="different-secret-key-very-long",
            jwt_algorithm="HS256",
        )

        with pytest.raises(JWTError):
            await wrong_auth.verify_token(token)

    def test_create_token_with_custom_expiration(self, auth_manager):
        """Test token creation with custom expiration."""
        token = auth_manager.create_access_token(
            user_id="user-123",
            client_id="client-456",
            role="admin",
            email="user@example.com",
            expires_delta=timedelta(hours=1),
        )

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_refresh_token(self, auth_manager):
        """Test token refresh."""
        original_token = auth_manager.create_access_token(
            user_id="user-123",
            client_id="client-456",
            role="admin",
            email="user@example.com",
        )

        # Refresh the token
        response = await auth_manager.refresh_token(original_token)

        assert response.access_token != original_token
        assert response.token_type == "bearer"
        assert response.expires_in > 0

        # Verify new token
        claims = await auth_manager.verify_token(response.access_token)
        assert claims["user_id"] == "user-123"
