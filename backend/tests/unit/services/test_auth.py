"""
【Unitテスト】認証サービスのロジックテスト
DB不要（モックまたはインメモリDB）

【テストの期待結果】
- パスワードは bcrypt でハッシュ化され、平文と異なる値になること
- 同じパスワードでもソルトにより毎回異なるハッシュが生成されること
- 正しいパスワードは verify_password で True が返ること
- JWTはデコードするとユーザーIDが取得できること
- 期限切れ・改ざんされたJWTはValueErrorを発生させること
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
        decode_access_token,  # 正しい関数名（decode_token ではない）
        hash_password,
        verify_password,
        generate_refresh_token,
        hash_token,
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
        """
        【期待結果】ハッシュが平文パスワードと異なること
        bcrypt はパスワードを変換するので元の文字列とは一致しない
        """
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"

    def test_verify_correct_password(self):
        """
        【期待結果】正しいパスワードで検証が成功すること
        ハッシュ化したパスワードと元のパスワードが一致する場合 True を返す
        """
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_verify_wrong_password(self):
        """
        【期待結果】間違ったパスワードで検証が失敗すること
        異なるパスワードで比較した場合 False を返す
        """
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_produces_different_hashes(self):
        """
        【期待結果】同じパスワードでも毎回違うハッシュになること（ソルト確認）
        bcrypt はランダムなソルトを自動付与するため、同じパスワードでも異なる値になる
        """
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2

    def test_empty_password_raises(self):
        """
        【期待結果】空パスワードでValueErrorが発生すること
        空文字列はセキュリティ上問題があるため拒否する
        """
        with pytest.raises(ValueError):
            hash_password("")


class TestJWTToken:
    def test_create_and_decode_token(self):
        """
        【期待結果】トークン生成とデコードが一致すること
        create_access_token で生成したトークンから decode_access_token で user_id が取得できる
        """
        user_id = 42
        token = create_access_token(user_id)
        # decode_access_token は int 型の user_id を直接返す（dictではない）
        decoded_id = decode_access_token(token)
        assert decoded_id == user_id

    def test_expired_token_raises(self):
        """
        【期待結果】有効期限切れトークンでValueErrorが発生すること
        expires_delta に負の値を渡すと即座に期限切れになる
        """
        token = create_access_token(1, expires_delta=timedelta(seconds=-1))
        with pytest.raises(ValueError):
            decode_access_token(token)

    def test_tampered_token_raises(self):
        """
        【期待結果】改ざんされたトークンでValueErrorが発生すること
        署名が壊れたJWTはデコードに失敗する
        """
        token = create_access_token(1)
        tampered = token + "tampered"
        with pytest.raises(ValueError):
            decode_access_token(tampered)

    def test_token_contains_correct_user_id(self):
        """
        【期待結果】トークンに正しいuser_idが含まれること
        デコード結果の int 値が生成時の user_id と一致すること
        """
        user_id = 99
        token = create_access_token(user_id)
        decoded_id = decode_access_token(token)
        assert decoded_id == user_id


class TestRefreshTokenUtils:
    def test_generate_refresh_token_is_unique(self):
        """
        【期待結果】リフレッシュトークンが毎回異なること
        secrets.token_urlsafe はランダムな文字列を生成するため重複しない
        """
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        assert token1 != token2

    def test_generate_refresh_token_length(self):
        """
        【期待結果】リフレッシュトークンが十分な長さを持つこと
        32バイト（256bit）の Base64URL エンコードで 43文字以上になる
        """
        token = generate_refresh_token()
        assert len(token) >= 40  # base64urlの最小長

    def test_hash_token_is_deterministic(self):
        """
        【期待結果】同じトークンを渡すと毎回同じハッシュになること
        SHA-256 は決定的なハッシュ関数なので同じ入力から同じ出力が得られる
        """
        raw = "some-opaque-refresh-token"
        hash1 = hash_token(raw)
        hash2 = hash_token(raw)
        assert hash1 == hash2

    def test_hash_token_different_inputs_produce_different_hashes(self):
        """
        【期待結果】異なるトークンから異なるハッシュが生成されること
        """
        hash1 = hash_token("token-aaa")
        hash2 = hash_token("token-bbb")
        assert hash1 != hash2

    def test_hash_token_length(self):
        """
        【期待結果】SHA-256 ハッシュは 64文字の16進数文字列になること
        """
        hashed = hash_token("any-token")
        assert len(hashed) == 64
