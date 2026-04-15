"""
【Integrationテスト】認証APIエンドポイントのテスト
FastAPI TestClient + テスト用インメモリDB使用

【Cookie方式について】
リフレッシュトークンはレスポンスボディではなく HttpOnly Cookie で返されます。
FastAPI TestClient（requests ライブラリ）は Cookie を自動管理するため、
ログイン後のリクエストで自動的に Cookie が付与されます。

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
        """
        【期待結果】正常に登録できること
        - ステータスコード: 201
        - レスポンスに access_token が含まれること
        - リフレッシュトークンはボディではなく Cookie で返されること
        """
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "Password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        # リフレッシュトークンはCookieで管理するのでボディには含まれない
        assert "refresh_token" not in data
        # Cookieが設定されていること
        assert "refresh_token" in response.cookies

    def test_register_duplicate_email(self, client, registered_user):
        """
        【期待結果】同じメールアドレスで重複登録するとエラーになること
        ステータスコード: 409 (Conflict)
        """
        response = client.post(
            "/api/auth/register",
            json={
                "email": registered_user["email"],
                "password": "AnotherPassword123",
            },
        )
        assert response.status_code == 409

    def test_register_invalid_email(self, client):
        """
        【期待結果】不正なメール形式で登録するとバリデーションエラーになること
        ステータスコード: 422 (Unprocessable Entity)
        """
        response = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "Password123"},
        )
        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """
        【期待結果】パスワードが短すぎる場合エラーになること
        ステータスコード: 422 (8文字未満は拒否)
        """
        response = client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        """
        【期待結果】正しい認証情報でログインできること
        - ステータスコード: 200
        - レスポンスに access_token が含まれること
        - リフレッシュトークンはCookieで返されること（ボディには含まれない）
        """
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
        # リフレッシュトークンはCookieで管理するのでボディには含まれない
        assert "refresh_token" not in data
        # Cookieが設定されていること
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client, registered_user):
        """
        【期待結果】間違ったパスワードでログインに失敗すること
        ステータスコード: 401 (Unauthorized)
        """
        response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPassword999",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """
        【期待結果】存在しないメールアドレスでログインに失敗すること
        ステータスコード: 401 (存在有無を推測させないため401を返す)
        """
        response = client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "Password123"},
        )
        assert response.status_code == 401

    def test_account_lock_after_five_failures(self, client, registered_user):
        """
        【期待結果】5回ログイン失敗後にアカウントがロックされること
        - 5回目まで: 401 (Unauthorized)
        - 5回目: 423 (Locked) が返り、以降のリクエストも423
        """
        wrong_password = "WrongPassword999"

        # 5回ログイン失敗させる
        for attempt in range(1, 6):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": registered_user["email"],
                    "password": wrong_password,
                },
            )
            if attempt < 5:
                # 5回目未満は401
                assert response.status_code == 401, f"attempt {attempt}: expected 401"
            else:
                # 5回目でロックされる
                assert response.status_code == 423, f"attempt {attempt}: expected 423 (Locked)"

        # ロック後は正しいパスワードでも423になること
        response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert response.status_code == 423


class TestRefreshToken:
    def test_refresh_success(self, client, registered_user):
        """
        【期待結果】Cookieのリフレッシュトークンで新しいアクセストークンを取得できること
        TestClient は Cookie を自動管理するため、ログイン後のリフレッシュで自動的にCookieが送信される
        """
        # ログインしてCookieにリフレッシュトークンを受け取る
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert login_response.status_code == 200
        # TestClient がCookieを自動管理するため、次のリクエストで自動送信される

        # Cookieを使ってリフレッシュ（ボディは空でOK）
        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_refresh_without_cookie_fails(self, client):
        """
        【期待結果】Cookieなしでリフレッシュするとエラーになること
        ステータスコード: 401
        """
        # Cookieを持たない新しいクライアントで直接リフレッシュ
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401

    def test_refresh_token_rotation(self, client, registered_user):
        """
        【期待結果】リフレッシュ後に新しいCookieが発行され、古いトークンが失効すること
        Refresh Token Rotation: 使用済みトークンを再使用するとリプレイ攻撃として検知される
        """
        # ログイン
        client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )

        # 1回目のリフレッシュ（成功）
        response1 = client.post("/api/auth/refresh")
        assert response1.status_code == 200

        # 2回目のリフレッシュ（TestClientが新しいCookieで送信するため成功）
        response2 = client.post("/api/auth/refresh")
        assert response2.status_code == 200


class TestProtectedEndpoints:
    def test_me_without_token(self, client):
        """
        【期待結果】トークンなしで /api/auth/me にアクセスするとエラーになること
        ステータスコード: 401 または 403
        """
        response = client.get("/api/auth/me")
        assert response.status_code in (401, 403)

    def test_me_with_valid_token(self, client, auth_headers):
        """
        【期待結果】有効なアクセストークンで /api/auth/me にアクセスできること
        - ステータスコード: 200
        - レスポンスに email が含まれること
        """
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data

    def test_me_with_invalid_token(self, client):
        """
        【期待結果】無効なトークンで /api/auth/me にアクセスするとエラーになること
        ステータスコード: 401
        """
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogout:
    def test_logout_success(self, client, auth_headers, registered_user):
        """
        【期待結果】ログアウトが成功すること
        - ステータスコード: 200
        - ログアウト後のリフレッシュは失敗すること（Cookieが削除される）
        """
        # まずログインしてCookieを取得
        client.post(
            "/api/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )

        # ログアウト
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
