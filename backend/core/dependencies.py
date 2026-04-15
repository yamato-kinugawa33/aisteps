"""
core/dependencies.py

FastAPIの「依存性注入（Dependency Injection）」用の関数を定義するファイルです。

【このファイルの役割】
- 認証が必要なAPIエンドポイントで使う `get_current_user` 関数を提供します。
- FastAPIの `Depends()` と組み合わせることで、認証チェックを自動化できます。

【依存性注入（Depends）とは？】
エンドポイント関数の引数に `Depends(関数)` と書くと、
FastAPIが自動でその関数を呼び出して結果を渡してくれる仕組みです。

使い方の例:
    @router.get("/protected")
    def protected_route(
        current_user: User = Depends(get_current_user)  # 自動で認証チェック
    ):
        return {"email": current_user.email}
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.database import get_db
from models.user import User

# HTTPBearer: "Authorization: Bearer <token>" ヘッダーを自動で読み取るFastAPIの仕組み
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    リクエストのAuthorizationヘッダーからJWTを取得し、
    対応するUserオブジェクトを返します。

    認証が必要なエンドポイントで `Depends(get_current_user)` として使用します。

    Args:
        credentials: FastAPIが自動で "Bearer <token>" から抽出したトークン情報
        db: DBセッション

    Returns:
        認証済みのUserオブジェクト

    Raises:
        HTTPException 401: トークンが無効・期限切れ・改ざんの場合
        HTTPException 401: ユーザーが存在しないまたは無効化されている場合
    """
    token = credentials.credentials

    # JWTをデコードしてuser_idを取得
    try:
        user_id = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",  # 内部エラーの詳細は含めない（T11対策）
            # WWW-Authenticate ヘッダー: クライアントに「Bearerトークンが必要」と伝える
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # DBからユーザーを取得
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # アカウントが無効化されていないか確認
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="アカウントが無効化されています",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
