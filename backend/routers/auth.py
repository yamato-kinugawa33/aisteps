"""
routers/auth.py

認証関連のAPIエンドポイントを定義するファイルです。

【HttpOnly Cookie によるリフレッシュトークン管理】
リフレッシュトークンはHTTPレスポンスのボディではなく、HttpOnly Cookieで返します。
- HttpOnly: JavaScriptからCookieの値を読めない（XSS攻撃でトークンを盗めない）
- SameSite=Lax: CSRF攻撃を軽減
- Path=/api/auth/refresh: このパスへのリクエスト時のみCookieを送信

フロントエンド側は refresh_token を localStorage に保存する必要がなくなります。
リフレッシュ時はブラウザが自動でCookieを送信します（credentials: 'include' が必要）。

【エンドポイント一覧】
    POST /api/auth/register  - 新規ユーザー登録（3回/時/IPのレート制限）
    POST /api/auth/login     - ログイン（5回/分/IPのレート制限）
    POST /api/auth/logout    - ログアウト（Cookieのリフレッシュトークンを失効）
    POST /api/auth/refresh   - アクセストークン更新（20回/時/IPのレート制限）
    GET  /api/auth/me        - 現在のユーザー情報取得
"""

import os

from fastapi import APIRouter, Cookie, Depends, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from db.database import get_db
from models.user import User
from schemas.auth import (
    LoginRequest,
    MeResponse,
    TokenResponse,
    UserCreate,
)
from services.auth import (
    get_me,
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# ─── Cookie設定 ───
# 本番環境（HTTPS）ではsecure=Trueにする
# 開発環境（HTTP localhost）ではFalseにしないとCookieが送信されない
_COOKIE_SECURE = os.getenv("ENVIRONMENT", "development") == "production"
# リフレッシュトークンの有効期限（秒）= 7日
_REFRESH_MAX_AGE = 7 * 24 * 60 * 60


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    """
    レスポンスにリフレッシュトークンのHttpOnly Cookieをセットするヘルパー関数。

    Args:
        response: FastAPIのResponseオブジェクト
        raw_refresh_token: セットする生のリフレッシュトークン
    """
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,          # JavaScript からアクセス不可（XSS対策）
        samesite="lax",         # CSRF軽減（strictだとCORSで送信されない場合あり）
        secure=_COOKIE_SECURE,  # 本番はHTTPS必須
        max_age=_REFRESH_MAX_AGE,
        path="/api/auth",       # /api/auth/* へのリクエスト時のみ送信
    )


def _clear_refresh_cookie(response: Response) -> None:
    """
    リフレッシュトークンのCookieを削除するヘルパー関数（ログアウト時に使用）。
    """
    response.delete_cookie(key="refresh_token", path="/api/auth")


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("3/hour")  # アカウント大量作成を防ぐレート制限
def register(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    新規ユーザー登録エンドポイント。

    レート制限: 同一IPから1時間に3回まで

    成功レスポンス (201):
        access_token: アクセストークン（30分有効）
        token_type: "bearer"
        ※ リフレッシュトークンは HttpOnly Cookie で返します（レスポンスボディには含まない）

    エラー:
        422: バリデーションエラー
        409: メールアドレス重複
        429: レート制限超過
    """
    access_token, raw_refresh_token = register_user(db, user_data)
    # リフレッシュトークンはCookieにセット（ボディには含めない）
    _set_refresh_cookie(response, raw_refresh_token)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # ブルートフォース対策のレート制限
def login(
    request: Request,
    response: Response,
    user_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    ログインエンドポイント。

    レート制限: 同一IPから1分間に5回まで

    成功レスポンス (200):
        access_token: アクセストークン（30分有効）
        ※ リフレッシュトークンは HttpOnly Cookie で返します

    エラー:
        401: 認証失敗
        423: アカウントロック
        429: レート制限超過
    """
    access_token, raw_refresh_token = login_user(user_data.email, user_data.password, db)
    _set_refresh_cookie(response, raw_refresh_token)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=200)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    # Cookie から自動的にリフレッシュトークンを受け取る
    # ブラウザが /api/auth への全リクエストに自動でCookieを付与する
    refresh_token: str | None = Cookie(default=None),
    _current_user: User = Depends(get_current_user),
):
    """
    ログアウトエンドポイント。

    Bearerトークン認証が必要です（Authorizationヘッダーに access_token が必要）。

    処理:
        1. CookieのリフレッシュトークンをDBで失効させる
        2. レスポンスでCookieを削除する

    成功レスポンス (200):
        {"message": "ログアウトしました"}
    """
    if refresh_token:
        # DBでリフレッシュトークンを失効（ブラックリスト登録）
        revoke_refresh_token(refresh_token, db)
    # Cookieを削除してクライアント側からもトークンを消す
    _clear_refresh_cookie(response)
    return {"message": "ログアウトしました"}


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/hour")  # リフレッシュ乱用対策
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    # Cookie からリフレッシュトークンを自動取得
    refresh_token: str | None = Cookie(default=None),
):
    """
    アクセストークン更新エンドポイント。

    レート制限: 同一IPから1時間に20回まで

    リフレッシュトークンはCookieから自動的に取得します（ボディへの記載不要）。
    Refresh Token Rotation により古いトークンは失効し、新しいCookieがセットされます。

    成功レスポンス (200):
        access_token: 新しいアクセストークン
        ※ 新しいリフレッシュトークンはCookieで返します

    エラー:
        401: リフレッシュトークンが無効・期限切れ・未提供
        429: レート制限超過
    """
    from fastapi import HTTPException, status

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが提供されていません",
        )

    new_access_token, new_raw_refresh_token = rotate_refresh_token(refresh_token, db)
    # 新しいリフレッシュトークンをCookieにセット（古いトークンは失効済み）
    _set_refresh_cookie(response, new_raw_refresh_token)
    return TokenResponse(access_token=new_access_token, token_type="bearer")


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    """
    現在ログイン中のユーザー情報を取得するエンドポイント。

    Bearerトークン認証が必要です。
    Authorization: Bearer <access_token> ヘッダーを付けてリクエストしてください。

    成功レスポンス (200):
        id, email, is_active, created_at
    """
    return get_me(current_user)
