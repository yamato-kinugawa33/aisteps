"""
services/auth.py

認証機能のビジネスロジックをまとめたサービス層です。

【セキュリティ上の重要な実装】
1. タイミング攻撃対策: ユーザー不在時もダミーハッシュで検証
2. アカウントロック: 5回失敗→15分ロック
3. Refresh Token Rotation: 使用済みトークン検知→全セッション強制終了
4. トークンのDB管理: SHA-256ハッシュでDBに保存、即時失効可能
"""

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    hash_token,
    verify_password,
)
from models.refresh_token import RefreshToken
from models.user import User
from schemas.auth import MeResponse, UserCreate

logger = logging.getLogger(__name__)

# ─── アカウントロック設定 ───
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCK_DURATION_MINUTES = 15

# タイミング攻撃対策用ダミーハッシュ（モジュールロード時に一度だけ生成）
# ユーザーが存在しない場合でも同じ時間がかかるように使用する
_DUMMY_HASH = hash_password("dummy-password-for-timing-attack-prevention")


def _issue_refresh_token_to_db(user_id: int, db: Session) -> str:
    """
    新しいリフレッシュトークンを生成してDBに保存し、生のトークン値を返します。
    生の値はクライアントに渡し、DBにはSHA-256ハッシュのみを保存します。

    Returns:
        生のリフレッシュトークン（クライアントに渡す値）
    """
    raw_token = generate_refresh_token()
    token_hash = hash_token(raw_token)
    expires_at = get_refresh_token_expiry()

    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    return raw_token


def _revoke_all_tokens_for_user(user_id: int, db: Session) -> None:
    """
    指定ユーザーの全リフレッシュトークンを失効させます。
    リプレイ攻撃検知時やパスワード変更時に使用します。
    """
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked.is_(False),
    ).update({"is_revoked": True})
    db.commit()
    logger.warning("全リフレッシュトークンを失効: user_id=%d（リプレイ攻撃の可能性）", user_id)


def register_user(db: Session, user_data: UserCreate) -> tuple[str, str]:
    """
    新規ユーザーを登録してトークンペア (access_token, refresh_token) を返します。

    Raises:
        HTTPException 409: メールアドレスが既に登録されている場合
    """
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    hashed = hash_password(user_data.password)
    user = User(email=user_data.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("新規ユーザー登録完了: id=%d", user.id)
    access_token = create_access_token(user.id)
    raw_refresh_token = _issue_refresh_token_to_db(user.id, db)
    return access_token, raw_refresh_token


def authenticate_user(email: str, password: str, db: Session) -> User:
    """
    メールアドレスとパスワードを検証してUserオブジェクトを返します。

    【タイミング攻撃対策】
    ユーザーが存在しない場合もダミーハッシュで verify_password を実行することで
    レスポンス時間の差からユーザーの存在を推測されないようにしています。

    Raises:
        HTTPException 423: アカウントがロックされている場合
        HTTPException 401: 認証失敗の場合
    """
    user = db.query(User).filter(User.email == email).first()

    # ユーザー不在でも時間を消費してタイミング攻撃を防ぐ
    if not user:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    # アカウントロックチェック（DBのlocked_untilはtznaive）
    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        remaining_minutes = max(1, int((user.locked_until - now).total_seconds() // 60))
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"アカウントがロックされています。あと約{remaining_minutes}分後に再試行してください",
        )

    # パスワード検証
    if not verify_password(password, user.hashed_password):
        user.failed_login_count += 1

        if user.failed_login_count >= LOGIN_FAILURE_LIMIT:
            user.locked_until = now + timedelta(minutes=LOGIN_LOCK_DURATION_MINUTES)
            db.commit()
            logger.warning("アカウントロック: id=%d, failures=%d", user.id, user.failed_login_count)
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


def login_user(email: str, password: str, db: Session) -> tuple[str, str]:
    """
    認証情報を検証してトークンペアを返します。

    Returns:
        (access_token, raw_refresh_token) のタプル
    """
    user = authenticate_user(email, password, db)
    access_token = create_access_token(user.id)
    raw_refresh_token = _issue_refresh_token_to_db(user.id, db)
    return access_token, raw_refresh_token


def rotate_refresh_token(raw_token: str, db: Session) -> tuple[str, str]:
    """
    リフレッシュトークンを検証し、Refresh Token Rotationで新しいトークンペアを返します。

    【Refresh Token Rotation】
    トークンを一度使うたびに古いものを失効させ新しいものを発行します。
    失効済みトークンが再使用された場合（リプレイ攻撃）、
    そのユーザーの全セッションを強制終了します。

    Raises:
        HTTPException 401: トークンが無効・失効済み・期限切れの場合
    """
    token_hash = hash_token(raw_token)
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効です",
        )

    # 失効済みトークンの再使用 → リプレイ攻撃の可能性 → 全セッション強制終了
    if record.is_revoked:
        _revoke_all_tokens_for_user(record.user_id, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="セキュリティ上の理由により再ログインが必要です",
        )

    # 有効期限切れ（tznaive同士で比較）
    if record.expires_at < datetime.utcnow():
        record.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンの有効期限が切れています",
        )

    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
        )

    # 古いトークンを失効させて新しいトークンを発行（Rotation）
    record.is_revoked = True
    db.commit()

    new_access_token = create_access_token(user.id)
    new_raw_refresh_token = _issue_refresh_token_to_db(user.id, db)
    return new_access_token, new_raw_refresh_token


def revoke_refresh_token(raw_token: str, db: Session) -> None:
    """
    指定されたリフレッシュトークンを失効させます（ログアウト用）。
    存在しない場合はエラーを発生させずに無視します。
    """
    token_hash = hash_token(raw_token)
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if record and not record.is_revoked:
        record.is_revoked = True
        db.commit()
        logger.info("リフレッシュトークンを失効: user_id=%d", record.user_id)


def get_me(user: User) -> MeResponse:
    """
    UserオブジェクトをMeResponseスキーマに変換して返します。
    """
    return MeResponse.model_validate(user)
