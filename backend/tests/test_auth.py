import os
import sys
import unittest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError, AuthError

from app.main import app
from app.api.deps import get_current_user, get_supabase
from app.schemas.auth import RegisterRequest, LoginRequest, UserResponse


class DummyUser:
    def __init__(self, user_id="11111111-2222-3333-4444-555555555555", email="test@example.com"):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"full_name": "Test User"}


class DummySession:
    def __init__(self):
        self.access_token = "mock-access-token-xyz"
        self.refresh_token = "mock-refresh-token-xyz"
        self.token_type = "bearer"
        self.expires_in = 3600
        self.expires_at = 1756396800


class DummyAuthResponse:
    def __init__(self, user=None, session=None):
        self.user = user or DummyUser()
        self.session = session or DummySession()


class DummyUserResponse:
    def __init__(self, user=Ellipsis):
        if user is Ellipsis:
            self.user = DummyUser()
        else:
            self.user = user


class TestAuthEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()
        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    # --- Health Endpoints Regression Tests ---
    def test_health_endpoints(self):
        response_root = self.client.get("/health")
        self.assertEqual(response_root.status_code, 200)
        self.assertEqual(response_root.json(), {"status": "ok"})

        response_v1 = self.client.get("/api/v1/health")
        self.assertEqual(response_v1.status_code, 200)
        self.assertEqual(response_v1.json(), {"status": "ok"})

    # --- Registration Tests ---
    def test_register_success_with_session(self):
        self.mock_supabase.auth.sign_up.return_value = DummyAuthResponse()
        payload = {"email": "test@example.com", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["user"]["email"], "test@example.com")
        self.assertEqual(data["user"]["id"], "11111111-2222-3333-4444-555555555555")
        self.assertIsNotNone(data["session"])
        self.assertEqual(data["session"]["access_token"], "mock-access-token-xyz")
        self.assertEqual(data["message"], "Registration successful.")

    def test_register_success_without_session(self):
        auth_resp = DummyAuthResponse(session=None)
        auth_resp.session = None
        self.mock_supabase.auth.sign_up.return_value = auth_resp
        payload = {"email": "newuser@example.com", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["session"])
        self.assertIn("verify your account", data["message"])

    def test_register_invalid_email_format(self):
        payload = {"email": "invalid-email-address", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_register_short_password(self):
        payload = {"email": "test@example.com", "password": "123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_register_supabase_auth_api_error(self):
        self.mock_supabase.auth.sign_up.side_effect = AuthApiError(
            "User already registered",
            400,
            "user_already_exists"
        )
        payload = {"email": "existing@example.com", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("User already registered", response.json()["detail"])

    def test_register_unconfigured_supabase(self):
        def raise_val_err():
            raise HTTPException(
                status_code=503,
                detail="SUPABASE_URL and SUPABASE_ANON_KEY must be configured."
            )
        app.dependency_overrides[get_supabase] = raise_val_err
        payload = {"email": "user@example.com", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 503)

    # --- Login Tests ---
    def test_login_success(self):
        self.mock_supabase.auth.sign_in_with_password.return_value = DummyAuthResponse()
        payload = {"email": "test@example.com", "password": "securepassword123"}
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["email"], "test@example.com")
        self.assertEqual(data["session"]["access_token"], "mock-access-token-xyz")
        self.assertEqual(data["message"], "Authentication successful.")

    def test_login_invalid_credentials(self):
        self.mock_supabase.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials",
            400,
            "invalid_credentials"
        )
        payload = {"email": "wrong@example.com", "password": "wrongpassword"}
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid login credentials", response.json()["detail"])

    def test_login_invalid_email_format(self):
        payload = {"email": "not-an-email", "password": "password123"}
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_login_unconfigured_supabase(self):
        def raise_val_err():
            raise HTTPException(
                status_code=503,
                detail="SUPABASE_URL and SUPABASE_ANON_KEY must be configured."
            )
        app.dependency_overrides[get_supabase] = raise_val_err
        payload = {"email": "user@example.com", "password": "password123"}
        response = self.client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 503)

    # --- Current User (/me) Tests ---
    def test_get_me_success(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["user_metadata"]["full_name"], "Test User")

    def test_get_me_missing_token(self):
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("token is missing", response.json()["detail"])

    def test_get_me_invalid_token(self):
        self.mock_supabase.auth.get_user.side_effect = AuthApiError(
            "Invalid JWT token signature",
            401,
            "invalid_jwt"
        )
        headers = {"Authorization": "Bearer invalid-jwt-token"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication failed", response.json()["detail"])

    # --- Logout Tests ---
    def test_logout_success(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Successfully signed out."})
        self.mock_supabase.auth._request.assert_called_once_with("POST", "logout", jwt="valid-jwt-token")
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()

    def test_logout_unauthenticated(self):
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, 401)
        self.mock_supabase.auth._request.assert_not_called()
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()

    def test_logout_token_revocation_failure_regression(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        self.mock_supabase.auth._request.side_effect = AuthApiError(
            "Session revocation failed",
            400,
            "session_revocation_failed"
        )
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Logout failed: Session revocation failed", response.json()["detail"])
        self.mock_supabase.auth._request.assert_called_once_with("POST", "logout", jwt="valid-jwt-token")
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()

    def test_logout_unexpected_error_regression(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        self.mock_supabase.auth._request.side_effect = RuntimeError("Network connection broken")
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 500)
        self.assertIn("An unexpected error occurred during logout", response.json()["detail"])
        self.mock_supabase.auth._request.assert_called_once_with("POST", "logout", jwt="valid-jwt-token")
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()


class TestAuthDependency(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()

    def test_get_current_user_success(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-123")
        user = get_current_user(creds, self.mock_supabase)
        self.assertEqual(user.id, "11111111-2222-3333-4444-555555555555")
        self.assertEqual(user.email, "test@example.com")

    def test_get_current_user_no_credentials(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_empty_token(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_null_user_returned(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse(user=None)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_auth_api_error(self):
        self.mock_supabase.auth.get_user.side_effect = AuthApiError("token expired", 401, "token_expired")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_auth_error_base(self):
        self.mock_supabase.auth.get_user.side_effect = AuthError("auth error occurred", "auth_error")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_value_error(self):
        self.mock_supabase.auth.get_user.side_effect = ValueError("Supabase not configured")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds, self.mock_supabase)
        self.assertEqual(ctx.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
