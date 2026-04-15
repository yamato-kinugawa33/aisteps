"""
services/auth.py

認証機能のビジネスロジックをまとめたサービス層です。

【このファイルの役割】
- ユーザー登録・ログイン・トークンリフレッシュなどの処理を実装します。
- ルーター（routers/auth.py）はHTTPの入出力を担当し、
  実際の処理はこのサービス層が担当します（責務の分離）。

【セキュリティ上の重要な実装】
- タイミング攻撃対策: ユーザーが存在しない場合もダミーハッシュで検証を実行し、
  レスポンス時間の差からユーザーの存在を推測されないようにする
- アカウントロック: 5回連続ログイン失敗で15分間ロック
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from models.user import User
from schemas.auth import MeResponse, TokenResponse, UserCreate

# セキュリティ関連のイベントをログに記録するロガー
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# アカウントロック設定
# ─────────────────────────────────────────────

# 何回失敗したらロックするか
LOGIN_FAILURE_LIMIT = 5

# ロックする時間（分）
LOGIN_LOCK_DURATION_MINUTES = 15

# タイミング攻撃対策用ダミーハッシュ
# ユーザーが存在しない場合でも同じ時間がかかるように使用する
_DUMMY_HASH = hash_password("dummy-password-for-timing-attack-prevention")


def register_user(db: Session, user_data: UserCreate) -> TokenResponse:
    """
    新規ユーザーを登録してJWTトークンを返します。

    処理の流れ:
        1. メールアドレスの重複チェック
        2. パスワードをbcryptでハッシュ化
        3. DBにユーザーを保存
        4. アクセストークンとリフレッシュトークンを生成して返す

    Args:
        db: DBセッション
        user_data: 登録するユーザーのメールアドレスとパスワード

    Returns:
        アクセストークンとリフレッシュトークン

    Raises:
        HTTPException 409: 同じメールアドレスが既に登録されている場合
    """
    # メールアドレスの重複チェック
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    # パスワードをハッシュ化して保存（平文パスワードはDBに保存しない）
    hashed = hash_password(user_data.password)
    user = User(email=user_data.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("新規ユーザー登録: email_prefix=%s", user_data.email[:3])

    # トークンを発行して返す
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def authenticate_user(email: str, password: str, db: Session) -> User:
    """
    メールアドレスとパスワードを検証してUserオブジェクトを返します。

    セキュリティ考慮点:
        - タイミング攻撃対策: ユーザーが存在しない場合もパスワード検証を実行する
          （処理時間の差からユーザーの存在を推測されないようにする）
        - アカウントロック: 5回失敗で15分間ロック
        - ログイン成功時: 失敗カウントをリセット

    Args:
        email: ログインに使うメールアドレス
        password: 入力されたパスワード
        db: DBセッション

    Returns:
        認証成功したUserオブジェクト

    Raises:
        HTTPException 423: アカウントがロックされている場合
        HTTPException 401: メールアドレスまたはパスワードが間違っている場合
    """
    user = db.query(User).filter(User.email == email).first()

    # タイミング攻撃対策: ユーザーが存在しない場合もハッシュ検証を実行して時間を消費する
    if not user:
        # ダミーハッシュで検証（結果は使わない）
        verify_password(password, _DUMMY_HASH)
        # ユーザーとパスワードどちらが間違っているか教えない（セキュリティのため）
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    # アカウントロックのチェック
    if user.locked_until and user.locked_until > datetime.now(timezone.utc).replace(tzinfo=None):
        remaining = int((user.locked_until - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"アカウントがロックされています。あと約{remaining}分後に再試行してください",
        )

    # パスワードの検証
    if not verify_password(password, user.hashed_password):
        # ログイン失敗回数を増やす
        user.failed_login_count += 1

        # LOGIN_FAILURE_LIMIT 回以上失敗したらロックする
        if user.failed_login_count >= LOGIN_FAILURE_LIMIT:
            user.locked_until = (
                datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(minutes=LOGIN_LOCK_DURATION_MINUTES)
            )
            db.commit()
            logger.warning(
                "アカウントロック: email_prefix=%s, failures=%d",
                email[:3], user.failed_login_count
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"ログイン失敗が{LOGIN_FAILURE_LIMIT}回に達しました。"
                       f"{LOGIN_LOCK_DURATION_MINUTES}分後に再試行してください",
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    # ログイン成功: 失敗カウントとロックをリセット
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    return user


def login_user(email: str, password: str, db: Session) -> TokenResponse:
    """
    認証情報を検証してJWTトークンを返します。

    Args:
        email: メールアドレス
        password: パスワード
        db: DBセッション

    Returns:
        アクセストークンとリフレッシュトークン
    """
    user = authenticate_user(email, password, db)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh_tokens(refresh_token: str, db: Session) -> TokenResponse:
    """
    リフレッシュトークンを検証して新しいトークンペアを返します。

    【リフレッシュトークンとは？】
    アクセストークンの有効期限は30分と短い。しかし毎回ログインは不便なので、
    7日間有効なリフレッシュトークンを使って新しいアクセストークンを取得できる。

    Args:
        refresh_token: リフレッシュトークン（クライアントが保存しているもの）
        db: DBセッション

    Returns:
        新しいアクセストークンとリフレッシュトークン

    Raises:
        HTTPException 401: リフレッシュトークンが無効・期限切れの場合
    """
    try:
        user_id = decode_refresh_token(refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"リフレッシュトークンが無効です: {e}",
        ) from e

    # ユーザーの存在確認
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
        )

    # 新しいトークンペアを発行
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


def get_me(user: User) -> MeResponse:
    """
    UserオブジェクトをMeResponseスキーマに変換して返します。

    Args:
        user: 認証済みのUserオブジェクト

    Returns:
        ユーザー情報（id, email, is_active, created_at）
    """
    return MeResponse.model_validate(user)
