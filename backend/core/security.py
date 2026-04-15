"""
core/security.py

パスワードハッシュ化とJWT（JSON Web Token）の生成・検証を行うユーティリティモジュールです。

【このファイルの役割】
- パスワードの安全な保存（bcryptハッシュ化）
- ログイン後に発行するJWTトークンの生成とデコード

【bcryptとは？】
パスワードを安全に保存するための「ハッシュ関数」です。
- 同じパスワードでも毎回異なるハッシュ値になる（ソルトが自動付与される）
- ハッシュから元のパスワードを逆算することが極めて困難
- 処理に意図的に時間をかけることでブルートフォース攻撃を防ぐ

【JWTとは？】
ユーザーが「ログイン済みであること」を証明する暗号化されたトークンです。
- ヘッダー.ペイロード.署名 の3パートからなる文字列
- 署名を検証することで改ざんを検知できる
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# ─────────────────────────────────────────────
# 設定値
# ─────────────────────────────────────────────

# JWT署名に使う秘密鍵（環境変数必須）
# 未設定の場合はKeyErrorが発生してサーバーが起動しない（セキュリティ上の意図的な設計）
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]

# 署名アルゴリズム: HS256 = HMAC-SHA256（共通鍵方式）
ALGORITHM = "HS256"

# アクセストークンの有効期限（30分）
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# リフレッシュトークンの有効期限（7日）
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ─────────────────────────────────────────────
# パスワード管理
# ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    平文パスワードをbcryptでハッシュ化して返します。
    DBには必ずこの関数で変換したハッシュ値を保存してください。

    Args:
        password: ハッシュ化したい平文パスワード

    Returns:
        bcryptハッシュ文字列（例: "$2b$12$..."）

    Raises:
        ValueError: パスワードが空の場合
    """
    if not password:
        raise ValueError("パスワードが空です")
    # gensalt() が自動でランダムなソルト（128bit）を生成する
    # ソルトとはハッシュのランダム化に使う値で、同じパスワードでも毎回異なるハッシュになる
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    平文パスワードとbcryptハッシュを照合します。
    ログイン時の認証に使用します。

    Args:
        plain_password: ユーザーが入力した平文パスワード
        hashed_password: DBに保存されているハッシュ値

    Returns:
        True: パスワードが一致した場合
        False: パスワードが一致しない場合
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ─────────────────────────────────────────────
# JWTトークン管理
# ─────────────────────────────────────────────

def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """
    アクセストークン（JWT）を生成して返します。
    APIリクエストの認証ヘッダーに使うトークンです。

    Args:
        user_id: JWTに埋め込むユーザーID
        expires_delta: 有効期限の延長（Noneの場合は ACCESS_TOKEN_EXPIRE_MINUTES が適用）

    Returns:
        JWT文字列（例: "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."）
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # ペイロード: トークンに埋め込む情報
    # "sub" (subject): 誰のトークンか = ユーザーID（文字列として保存）
    # "exp" (expiration): 有効期限
    # "iat" (issued at): 発行日時
    # "type": アクセストークンであることを明示
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + expires_delta,
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    リフレッシュトークン（JWT）を生成して返します。
    アクセストークンの期限切れ後に新しいアクセストークンを取得するためのトークンです。

    Args:
        user_id: JWTに埋め込むユーザーID

    Returns:
        JWT文字列
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now,
        # リフレッシュトークンをアクセストークンと区別するためのフィールド
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """
    アクセストークンをデコードしてユーザーIDを返します。
    APIリクエストの認証チェックに使用します。

    Args:
        token: JWTアクセストークン文字列

    Returns:
        トークンに埋め込まれたユーザーID（整数）

    Raises:
        ValueError: トークンが無効・期限切れ・改ざんされている場合
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise ValueError("トークンの有効期限が切れています") from e
    except jwt.InvalidTokenError as e:
        raise ValueError(f"無効なトークンです: {e}") from e

    # トークンの種別チェック: アクセストークンでないと拒否
    if payload.get("type") != "access":
        raise ValueError("トークン種別が不正です（access が必要です）")

    return int(payload["sub"])


def decode_refresh_token(token: str) -> int:
    """
    リフレッシュトークンをデコードしてユーザーIDを返します。

    Args:
        token: JWTリフレッシュトークン文字列

    Returns:
        トークンに埋め込まれたユーザーID（整数）

    Raises:
        ValueError: トークンが無効・期限切れ・改ざんされている場合
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise ValueError("リフレッシュトークンの有効期限が切れています") from e
    except jwt.InvalidTokenError as e:
        raise ValueError(f"無効なリフレッシュトークンです: {e}") from e

    # トークンの種別チェック: リフレッシュトークンでないと拒否
    if payload.get("type") != "refresh":
        raise ValueError("トークン種別が不正です（refresh が必要です）")

    return int(payload["sub"])
