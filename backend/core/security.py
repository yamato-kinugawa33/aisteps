"""
core/security.py

パスワードハッシュ化とJWT（JSON Web Token）の生成・検証、
および不透明リフレッシュトークンの生成・ハッシュ化を行うユーティリティモジュールです。

【このファイルの役割】
- パスワードの安全な保存（bcryptハッシュ化）
- ログイン後に発行するJWTアクセストークンの生成とデコード
- リフレッシュトークン（ランダム文字列）の生成とSHA-256ハッシュ化

【bcryptとは？】
パスワードを安全に保存するための「ハッシュ関数」です。
- 同じパスワードでも毎回異なるハッシュ値になる（ソルトが自動付与される）
- ハッシュから元のパスワードを逆算することが極めて困難
- rounds=12: 処理に意図的に時間をかけることでブルートフォース攻撃を防ぐ

【JWTとは？】
ユーザーが「ログイン済みであること」を証明する暗号化されたトークンです。
短命（30分）なため、アクセストークンとして使用します。

【リフレッシュトークンとは？】
secrets.token_urlsafe()で生成するランダムな文字列です（JWTではない）。
DB管理で即時失効できるため、長命（7日）なリフレッシュ用として使います。
"""

import hashlib
import os
import secrets
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

# アクセストークンの有効期限（30分: 短命なので盗まれても被害を最小化できる）
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
    # gensalt(rounds=12): コストファクターを12に明示設定（仕様書要件）
    # コストファクターが高いほどハッシュ計算に時間がかかりブルートフォースが難しくなる
    # 12 ≈ ログイン1回あたり約0.3秒（セキュリティと利便性のバランス）
    salt = bcrypt.gensalt(rounds=12)
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
# JWTアクセストークン管理
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
    # "type": アクセストークンであることを明示（リフレッシュトークンと区別するため）
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + expires_delta,
        "iat": now,
        "type": "access",
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
        ValueError: アクセストークン以外のトークンが渡された場合
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise ValueError("トークンの有効期限が切れています") from e
    except jwt.InvalidTokenError as e:
        # 内部エラーの詳細はログに残すが、呼び出し元には汎用メッセージを返す
        raise ValueError("無効なトークンです") from e

    # トークンの種別チェック: アクセストークン以外は拒否
    # リフレッシュトークンをアクセストークンとして使い回す攻撃を防ぐ
    if payload.get("type") != "access":
        raise ValueError("トークン種別が不正です（accessトークンが必要です）")

    return int(payload["sub"])


# ─────────────────────────────────────────────
# 不透明リフレッシュトークン管理
# ─────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    ランダムな不透明リフレッシュトークンを生成します。

    【JWTではなくランダム文字列を使う理由】
    JWTはデコードすれば有効期限が確認できる「自己完結型」トークンです。
    リフレッシュトークンはDBで管理して即時失効できるようにしたいため、
    情報を持たないランダム文字列（不透明トークン）を使います。

    Returns:
        URL安全なランダム文字列（44文字, 256bit相当のエントロピー）
    """
    # token_urlsafe(32): 32バイト = 256ビットのランダムデータをBase64URL encode
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """
    トークン文字列をSHA-256でハッシュ化して返します。
    DBにはハッシュ値のみを保存し、生の値は保存しません。

    【なぜハッシュ化して保存するのか？】
    DBが漏洩した場合でも、ハッシュ値からは元のトークンを復元できないため、
    攻撃者がトークンを悪用することを防げます。

    Args:
        raw_token: 生のトークン文字列

    Returns:
        SHA-256ハッシュの16進数文字列（64文字）
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_refresh_token_expiry() -> datetime:
    """
    リフレッシュトークンの有効期限日時を返します（DBに保存するutc時刻）。

    Returns:
        現在時刻 + REFRESH_TOKEN_EXPIRE_DAYS のUTC datetime（tznaive）
    """
    # DBには timezone-naive の datetime を保存（PostgreSQLのDateTimeと合わせる）
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
