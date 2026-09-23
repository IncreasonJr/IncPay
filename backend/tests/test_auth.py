import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app


class TestAuthEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_auth_me_no_token(self):
        """Request without Authorization header returns 401."""
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})

    def test_auth_me_invalid_token(self):
        """Request with invalid token returns 401."""
        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.side_effect = Exception("invalid JWT: unable to parse signature")

        with patch("app.auth.get_supabase_client", return_value=mock_supabase):
            response = self.client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer bad_token"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"detail": "Not authenticated"})

    def test_auth_me_valid_token_mocked(self):
        """Request with valid token returns user id and email."""
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "admin@incpay.com"

        mock_user_response = MagicMock()
        mock_user_response.user = mock_user

        mock_supabase = MagicMock()
        mock_supabase.auth.get_user.return_value = mock_user_response

        with patch("app.auth.get_supabase_client", return_value=mock_supabase):
            response = self.client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer valid_jwt_token"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["email"], "admin@incpay.com")
            self.assertEqual(data["id"], str(mock_user.id))


if __name__ == "__main__":
    unittest.main()
