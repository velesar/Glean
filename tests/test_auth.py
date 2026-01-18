"""
Tests for the Glean authentication module.

Covers:
- Password hashing (including long passwords > 72 bytes)
- JWT token creation and decoding
- Auth API endpoints (register, login, me)
"""

import pytest

from web.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    _prepare_password,
)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password_basic(self):
        """Test basic password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_hash_password_long_password(self):
        """Test hashing passwords longer than bcrypt's 72-byte limit."""
        # Create a password longer than 72 bytes
        long_password = "a" * 100

        # Should not raise an error
        hashed = hash_password(long_password)
        assert hashed is not None
        assert hashed.startswith("$2b$")

    def test_verify_long_password(self):
        """Test verifying long passwords works correctly."""
        long_password = "a" * 100
        hashed = hash_password(long_password)

        assert verify_password(long_password, hashed) is True
        assert verify_password("a" * 99, hashed) is False
        assert verify_password("a" * 101, hashed) is False

    def test_prepare_password_short(self):
        """Test _prepare_password returns short passwords unchanged."""
        short_password = "short"
        assert _prepare_password(short_password) == short_password

    def test_prepare_password_exactly_72_bytes(self):
        """Test _prepare_password with exactly 72 bytes."""
        password_72 = "a" * 72
        assert _prepare_password(password_72) == password_72

    def test_prepare_password_over_72_bytes(self):
        """Test _prepare_password hashes passwords over 72 bytes."""
        long_password = "a" * 73
        prepared = _prepare_password(long_password)

        # Should be different from original
        assert prepared != long_password
        # Should be base64 encoded SHA-256 (44 chars)
        assert len(prepared) == 44

    def test_prepare_password_unicode(self):
        """Test _prepare_password handles unicode correctly."""
        # Unicode characters can be multiple bytes
        unicode_password = "пароль" * 20  # Cyrillic, 12 bytes per repeat
        prepared = _prepare_password(unicode_password)

        # Should be hashed since it exceeds 72 bytes
        assert len(prepared) == 44

    def test_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        assert hash1 != hash2

    def test_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "1", "username": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        # JWT format: header.payload.signature
        assert token.count(".") == 2

    def test_decode_access_token(self):
        """Test decoding an access token."""
        data = {"sub": "1", "username": "testuser"}
        token = create_access_token(data)

        result = decode_access_token(token)

        assert result is not None
        assert result.user_id == 1
        assert result.username == "testuser"

    def test_decode_token_sub_must_be_string(self):
        """Test that token sub claim must be a string for proper encoding."""
        # This is the fix we made - sub should be string
        data = {"sub": "42", "username": "testuser"}
        token = create_access_token(data)

        result = decode_access_token(token)

        assert result is not None
        assert result.user_id == 42
        assert isinstance(result.user_id, int)

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        result = decode_access_token("invalid.token.here")

        assert result is None

    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        from datetime import timedelta

        data = {"sub": "1", "username": "testuser"}
        # Create token that expired 1 hour ago
        token = create_access_token(data, expires_delta=timedelta(hours=-1))

        result = decode_access_token(token)

        assert result is None

    def test_decode_token_missing_sub(self):
        """Test decoding a token without sub claim returns None."""
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from web.api.auth import SECRET_KEY, ALGORITHM

        # Create token without sub
        data = {
            "username": "testuser",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        result = decode_access_token(token)

        assert result is None

    def test_token_contains_user_info(self):
        """Test that token payload contains expected user info."""
        from jose import jwt
        from web.api.auth import SECRET_KEY, ALGORITHM

        data = {"sub": "123", "username": "johndoe"}
        token = create_access_token(data)

        # Decode without verification to inspect payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "123"
        assert payload["username"] == "johndoe"
        assert "exp" in payload


class TestAuthAPIEndpoints:
    """Tests for auth API endpoints using FastAPI TestClient."""

    @pytest.fixture
    def client(self, temp_db):
        """Create a FastAPI test client with temp database."""
        from fastapi.testclient import TestClient
        from web.api.main import app
        from web.api import deps

        # Override the database dependency
        def override_get_db():
            return temp_db

        app.dependency_overrides[deps.get_db] = override_get_db

        with TestClient(app) as client:
            yield client

        # Clear overrides
        app.dependency_overrides.clear()

    def test_setup_status_no_users(self, client):
        """Test setup-status returns needs_setup=True when no users."""
        response = client.get("/api/auth/setup-status")

        assert response.status_code == 200
        data = response.json()
        assert data["needs_setup"] is True
        assert data["user_count"] == 0

    def test_register_first_user_is_admin(self, client):
        """Test that first registered user becomes admin."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "email": "admin@test.com",
                "password": "password123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True

    def test_register_second_user_not_admin(self, client):
        """Test that second registered user is not admin."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "email": "admin@test.com",
                "password": "password123"
            }
        )

        # Register second user
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "user2@test.com",
                "password": "password123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "user2"
        assert data["is_admin"] is False

    def test_register_duplicate_username(self, client):
        """Test that duplicate username is rejected."""
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test1@test.com",
                "password": "password123"
            }
        )

        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test2@test.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client):
        """Test that duplicate email is rejected."""
        client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "same@test.com",
                "password": "password123"
            }
        )

        response = client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "same@test.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, client):
        """Test successful login returns token."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@test.com",
                "password": "password123"
            }
        )

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """Test login with wrong password fails."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@test.com",
                "password": "password123"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nobody",
                "password": "password123"
            }
        )

        assert response.status_code == 401

    def test_get_current_user(self, client):
        """Test getting current user with valid token."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@test.com",
                "password": "password123"
            }
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@test.com"

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token fails."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token fails."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_login_with_long_password(self, client):
        """Test login works with passwords > 72 bytes."""
        long_password = "a" * 100

        # Register with long password
        client.post(
            "/api/auth/register",
            json={
                "username": "longpass",
                "email": "long@test.com",
                "password": long_password
            }
        )

        # Login with same long password
        response = client.post(
            "/api/auth/login",
            json={
                "username": "longpass",
                "password": long_password
            }
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_full_auth_flow(self, client):
        """Test complete auth flow: register -> login -> access protected resource."""
        # 1. Check setup status
        setup_response = client.get("/api/auth/setup-status")
        assert setup_response.json()["needs_setup"] is True

        # 2. Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": "admin",
                "email": "admin@test.com",
                "password": "securepassword123"
            }
        )
        assert register_response.status_code == 200
        assert register_response.json()["is_admin"] is True

        # 3. Check setup status again
        setup_response = client.get("/api/auth/setup-status")
        assert setup_response.json()["needs_setup"] is False
        assert setup_response.json()["user_count"] == 1

        # 4. Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "securepassword123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 5. Access protected resource
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "admin"

        # 6. Logout (stateless, just verify endpoint works)
        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200
