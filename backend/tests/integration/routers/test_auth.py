"""
【Integrationテスト】認証APIエンドポイントのテスト
FastAPI TestClient + テスト用DB使用
NOTE: bcrypt, PyJWT, email-validator が必要です
"""

import pytest

try:
    import bcrypt  # noqa: F401
    import jwt  # noqa: F401

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not DEPS_AVAILABLE,
    reason="認証テストに必要なパッケージ (bcrypt, PyJWT) がインストールされていません。"
    "uv add bcrypt pyjwt 'pydantic[email]' を実行してください。",
)


class TestRegister:
    def test_register_success(self, client):
        """正常に登録できること"""
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "Password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_duplicate_email(self, client, registered_user):
        """同じメールアドレスで重複登録するとエラーになること"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": registered_user["email"],
                "password": "AnotherPassword123",
            },
        )
        assert response.status_code == 409

    def test_register_invalid_email(self, client):
        """不正なメール形式で登録するとバリデーションエラーになること"""
        response = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "Password123"},
        )
        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """パスワードが短すぎる場合エラーになること"""
        response = client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        """正しい認証情報でログインできること"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client, registered_user):
        """間違ったパスワードでログインに失敗すること"""
        response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPassword999",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """存在しないメールアドレスでログインに失敗すること"""
        response = client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "Password123"},
        )
        assert response.status_code == 401


class TestRefreshToken:
    def test_refresh_success(self, client, registered_user):
        """有効なリフレッシュトークンで新しいトークンを取得できること"""
        # まずログインしてリフレッシュトークンを取得
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # リフレッシュトークンで新しいトークンを取得
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_refresh_with_invalid_token(self, client):
        """無効なリフレッシュトークンでエラーになること"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    def test_me_without_token(self, client):
        """トークンなしで/api/auth/meにアクセスするとエラーになること"""
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_me_with_valid_token(self, client, auth_headers):
        """有効なトークンで/api/auth/meにアクセスできること"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
