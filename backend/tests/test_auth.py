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
        self.mock_supabase.auth._request.assert_called_once_with(
            "POST", "logout", jwt="valid-jwt-token", no_resolve_json=True
        )
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()

    def test_logout_empty_response_body_success(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        # Mock empty response from Supabase logout endpoint
        mock_resp = MagicMock()
        mock_resp.text = ""
        mock_resp.content = b""
        mock_resp.status_code = 200
        self.mock_supabase.auth._request.return_value = mock_resp

        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Successfully signed out."})
        self.mock_supabase.auth._request.assert_called_once_with(
            "POST", "logout", jwt="valid-jwt-token", no_resolve_json=True
        )
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
        self.mock_supabase.auth._request.assert_called_once_with(
            "POST", "logout", jwt="valid-jwt-token", no_resolve_json=True
        )
        self.mock_supabase.auth.sign_out.assert_not_called()
        self.mock_supabase.auth.admin.sign_out.assert_not_called()

    def test_logout_unexpected_error_regression(self):
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        self.mock_supabase.auth._request.side_effect = RuntimeError("Network connection broken")
        headers = {"Authorization": "Bearer valid-jwt-token"}
        response = self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 500)
        self.assertIn("An unexpected error occurred during logout", response.json()["detail"])
        self.mock_supabase.auth._request.assert_called_once_with(
            "POST", "logout", jwt="valid-jwt-token", no_resolve_json=True
        )
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


class TestSupabaseUrlValidation(unittest.TestCase):
    def setUp(self):
        import app.core.supabase as supabase_module

        self.supabase_module = supabase_module
        self.orig_client = supabase_module._supabase_client
        self.orig_sr_client = supabase_module._service_role_supabase_client
        supabase_module._supabase_client = None
        supabase_module._service_role_supabase_client = None

    def tearDown(self):
        self.supabase_module._supabase_client = self.orig_client
        self.supabase_module._service_role_supabase_client = self.orig_sr_client

    def test_local_loopback_http_accepted_in_development(self):
        from unittest.mock import patch

        loopback_urls = [
            "http://127.0.0.1:54321",
            "http://localhost:54321",
            "http://[::1]:54321",
        ]
        for url in loopback_urls:
            with self.subTest(url=url):
                self.supabase_module._supabase_client = None
                self.supabase_module._service_role_supabase_client = None
                with (
                    patch.object(self.supabase_module.settings, "ENVIRONMENT", "development"),
                    patch.object(self.supabase_module.settings, "SUPABASE_URL", url),
                    patch.object(self.supabase_module.settings, "SUPABASE_ANON_KEY", "anon-key"),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_SERVICE_ROLE_KEY",
                        "service-role-key",
                    ),
                    patch.object(self.supabase_module, "create_client") as mock_create,
                ):
                    mock_client = MagicMock()
                    mock_create.return_value = mock_client

                    self.supabase_module.validate_supabase_url(url, "development")
                    c1 = self.supabase_module.get_supabase_client()
                    c2 = self.supabase_module.get_service_role_supabase_client()
                    c3 = self.supabase_module.create_scoped_supabase_client("user-jwt")

                    self.assertIs(c1, mock_client)
                    self.assertIs(c2, mock_client)
                    self.assertIs(c3, mock_client)
                    self.assertEqual(mock_create.call_count, 3)

    def test_remote_http_rejected_even_in_development(self):
        from unittest.mock import patch

        remote_http_urls = [
            "http://thustdjwwtkhlhbnuvin.supabase.co",
            "http://example.com:54321",
            "http://192.168.1.10:54321",
        ]
        for url in remote_http_urls:
            with self.subTest(url=url):
                self.supabase_module._supabase_client = None
                self.supabase_module._service_role_supabase_client = None
                with (
                    patch.object(self.supabase_module.settings, "ENVIRONMENT", "development"),
                    patch.object(self.supabase_module.settings, "SUPABASE_URL", url),
                    patch.object(self.supabase_module.settings, "SUPABASE_ANON_KEY", "anon-key"),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_SERVICE_ROLE_KEY",
                        "service-role-key",
                    ),
                ):
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_service_role_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.create_scoped_supabase_client("user-jwt")
                    conn_status = self.supabase_module.verify_supabase_connection()
                    self.assertEqual(conn_status["status"], "error")

    def test_loopback_http_rejected_outside_development(self):
        from unittest.mock import patch

        for env in ("production", "staging", "test", ""):
            with self.subTest(env=env):
                self.supabase_module._supabase_client = None
                self.supabase_module._service_role_supabase_client = None
                with (
                    patch.object(self.supabase_module.settings, "ENVIRONMENT", env),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_URL",
                        "http://127.0.0.1:54321",
                    ),
                    patch.object(self.supabase_module.settings, "SUPABASE_ANON_KEY", "anon-key"),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_SERVICE_ROLE_KEY",
                        "service-role-key",
                    ),
                ):
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_service_role_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.create_scoped_supabase_client("user-jwt")
                    conn_status = self.supabase_module.verify_supabase_connection()
                    self.assertEqual(conn_status["status"], "error")

    def test_https_allowed_remote_host_accepted(self):
        from unittest.mock import patch

        url = "https://thustdjwwtkhlhbnuvin.supabase.co"
        for env in ("development", "production"):
            with self.subTest(env=env):
                self.supabase_module._supabase_client = None
                self.supabase_module._service_role_supabase_client = None
                with (
                    patch.object(self.supabase_module.settings, "ENVIRONMENT", env),
                    patch.object(self.supabase_module.settings, "SUPABASE_URL", url),
                    patch.object(self.supabase_module.settings, "SUPABASE_ANON_KEY", "anon-key"),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_SERVICE_ROLE_KEY",
                        "service-role-key",
                    ),
                    patch.object(self.supabase_module, "create_client") as mock_create,
                ):
                    mock_create.return_value = MagicMock()
                    self.supabase_module.get_supabase_client()
                    self.supabase_module.get_service_role_supabase_client()
                    self.supabase_module.create_scoped_supabase_client("user-jwt")
                    self.assertEqual(mock_create.call_count, 3)

    def test_malformed_and_lookalike_loopback_urls_rejected(self):
        from unittest.mock import patch

        bad_urls = [
            "http://127.0.0.1.evil.com:54321",
            "http://localhost.evil.com",
            "http://evil.com/127.0.0.1",
            "http://localhost@evil.com:54321",
            "http://evil.com@127.0.0.1:54321",
            "ftp://127.0.0.1:54321",
            "http://127.0.0.1:notaport",
            "https://",
            "http://",
            "https://thustdjwwtkhlhbnuvin.supabase.co/path with spaces",
        ]
        for url in bad_urls:
            with self.subTest(url=url):
                self.supabase_module._supabase_client = None
                self.supabase_module._service_role_supabase_client = None
                with (
                    patch.object(self.supabase_module.settings, "ENVIRONMENT", "development"),
                    patch.object(self.supabase_module.settings, "SUPABASE_URL", url),
                    patch.object(self.supabase_module.settings, "SUPABASE_ANON_KEY", "anon-key"),
                    patch.object(
                        self.supabase_module.settings,
                        "SUPABASE_SERVICE_ROLE_KEY",
                        "service-role-key",
                    ),
                ):
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.get_service_role_supabase_client()
                    with self.assertRaises(ValueError):
                        self.supabase_module.create_scoped_supabase_client("user-jwt")
                    conn_status = self.supabase_module.verify_supabase_connection()
                    self.assertEqual(conn_status["status"], "error")


if __name__ == '__main__':
    unittest.main()

