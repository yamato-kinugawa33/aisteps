"""
【Unitテスト】認証サービスのロジックテスト
DB不要（モックまたはインメモリDB）
"""

import os
from datetime import timedelta

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest

try:
    from core.security import (
        create_access_token,
        decode_token,
        hash_password,
        verify_password,
    )

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not SECURITY_AVAILABLE,
    reason="core.security のインポートに必要なパッケージ (bcrypt, PyJWT) がインストールされていません。"
    "uv add bcrypt pyjwt を実行してください。",
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        """ハッシュが平文パスワードと異なること"""
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"

    def test_verify_correct_password(self):
        """正しいパスワードで検証が成功すること"""
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_verify_wrong_password(self):
        """間違ったパスワードで検証が失敗すること"""
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """同じパスワードでも毎回違うハッシュになること（ソルト確認）"""
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2

    def test_empty_password_raises(self):
        """空パスワードでValueErrorが発生すること"""
        with pytest.raises(ValueError):
            hash_password("")


class TestJWTToken:
    def test_create_and_decode_token(self):
        """トークン生成とデコードが一致すること"""
        user_id = 42
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)

    def test_expired_token_raises(self):
        """有効期限切れトークンでValueErrorが発生すること"""
        token = create_access_token(1, expires_delta=timedelta(seconds=-1))
        with pytest.raises(ValueError, match="expired"):
            decode_token(token)

    def test_tampered_token_raises(self):
        """改ざんされたトークンでValueErrorが発生すること"""
        token = create_access_token(1)
        tampered = token + "tampered"
        with pytest.raises(ValueError):
            decode_token(tampered)

    def test_token_contains_correct_user_id(self):
        """トークンに正しいuser_idが含まれること"""
        user_id = 99
        token = create_access_token(user_id)
        payload = decode_token(token)
        decoded_id = int(payload["sub"])
        assert decoded_id == user_id
