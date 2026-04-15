"""
【Unitテスト】認証スキーマのバリデーションテスト
外部依存なし（DB接続不要）
NOTE: pydantic[email] (email-validator) が必要です
"""

import pytest
from pydantic import ValidationError

try:
    from schemas.auth import UserCreate

    SCHEMAS_AVAILABLE = True
except Exception:
    SCHEMAS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not SCHEMAS_AVAILABLE,
    reason="schemas.auth のインポートに必要なパッケージ (email-validator) がインストールされていません。"
    "uv add 'pydantic[email]' を実行してください。",
)


class TestUserCreate:
    def test_valid_input(self):
        """正常なemailとpasswordで作成できること"""
        user = UserCreate(email="valid@example.com", password="Password123")
        assert user.email == "valid@example.com"
        assert user.password == "Password123"

    def test_invalid_email_format(self):
        """不正なメール形式でバリデーションエラーになること"""
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="Password123")

    def test_password_too_short(self):
        """8文字未満のパスワードでバリデーションエラーになること"""
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com", password="short")

    def test_password_exactly_8_chars(self):
        """8文字ちょうどのパスワードは有効であること"""
        user = UserCreate(email="user@example.com", password="12345678")
        assert user.password == "12345678"

    def test_missing_email(self):
        """emailが未指定でバリデーションエラーになること"""
        with pytest.raises(ValidationError):
            UserCreate(password="Password123")

    def test_missing_password(self):
        """passwordが未指定でバリデーションエラーになること"""
        with pytest.raises(ValidationError):
            UserCreate(email="user@example.com")
