"""
routers/auth.py

認証関連のAPIエンドポイントを定義するファイルです。

【エンドポイント一覧】
    POST /api/auth/register  - 新規ユーザー登録
    POST /api/auth/login     - ログイン
    POST /api/auth/logout    - ログアウト
    POST /api/auth/refresh   - アクセストークン更新
    GET  /api/auth/me        - 現在のユーザー情報取得

【slowapiによるレート制限】
    ログインエンドポイントには1分間に5回のレート制限を設定しています。
    これにより、ブルートフォース攻撃（パスワードの総当たり試行）を防ぎます。
"""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from db.database import get_db
from models.user import User
from schemas.auth import (
    LogoutRequest,
    MeResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from services.auth import get_me, login_user, refresh_tokens, register_user

# このルーターの全エンドポイントは /api/auth のプレフィックスを持つ
router = APIRouter(prefix="/api/auth", tags=["auth"])

# レート制限ロジック: リクエスト元のIPアドレスを識別キーとして使用
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    新規ユーザー登録エンドポイント。

    リクエストボディ:
        email: メールアドレス
        password: パスワード（8文字以上）

    成功レスポンス (201):
        access_token: アクセストークン
        refresh_token: リフレッシュトークン
        token_type: "bearer"

    エラーレスポンス:
        422: バリデーションエラー（不正なメール形式、パスワード不足など）
        409: メールアドレスが既に登録済み
    """
    return register_user(db, user_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # 1分間に同じIPからのリクエストを5回まで許可（ブルートフォース対策）
def login(request: Request, user_data: LoginRequest, db: Session = Depends(get_db)):
    """
    ログインエンドポイント。

    レート制限: 同一IPから1分間に5回まで

    リクエストボディ:
        email: メールアドレス
        password: パスワード

    成功レスポンス (200):
        access_token: アクセストークン（有効期限30分）
        refresh_token: リフレッシュトークン（有効期限7日）
        token_type: "bearer"

    エラーレスポンス:
        401: 認証失敗（メールアドレスまたはパスワードが間違っている）
        423: アカウントロック（5回連続失敗）
        429: レート制限超過
    """
    return login_user(user_data.email, user_data.password, db)


@router.post("/logout", status_code=200)
def logout(
    _request_body: LogoutRequest,
    _current_user: User = Depends(get_current_user),
):
    """
    ログアウトエンドポイント。

    このエンドポイントはBearerトークン認証が必要です。
    JWTはステートレス（サーバー側に保存しない）なため、
    クライアント側でトークンを削除することでログアウトを実現します。

    リクエストボディ:
        refresh_token: 使用したリフレッシュトークン

    成功レスポンス (200):
        {"message": "ログアウトしました"}

    エラーレスポンス:
        401/403: 認証トークンが無効
    """
    # NOTE: 将来的にはリフレッシュトークンをDBに保存してブラックリスト管理することで
    # 完全な無効化が可能になります（現在はJWTの有効期限が来るまで有効）
    return {"message": "ログアウトしました"}


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/hour")  # 1時間に同じIPからのリクエストを20回まで許可
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    """
    アクセストークン更新エンドポイント。

    レート制限: 同一IPから1時間に20回まで

    リクエストボディ:
        refresh_token: 保存しているリフレッシュトークン

    成功レスポンス (200):
        access_token: 新しいアクセストークン
        refresh_token: 新しいリフレッシュトークン
        token_type: "bearer"

    エラーレスポンス:
        401: リフレッシュトークンが無効または期限切れ
        429: レート制限超過
    """
    return refresh_tokens(body.refresh_token, db)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    """
    現在のユーザー情報取得エンドポイント。

    このエンドポイントはBearerトークン認証が必要です。
    Authorizationヘッダーに "Bearer <access_token>" を付けてリクエストしてください。

    成功レスポンス (200):
        id: ユーザーID
        email: メールアドレス
        is_active: アカウントが有効かどうか
        created_at: アカウント作成日時

    エラーレスポンス:
        401/403: 認証トークンが無効
    """
    return get_me(current_user)
