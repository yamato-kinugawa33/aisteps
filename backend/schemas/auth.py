"""
schemas/auth.py

認証機能に関するPydanticスキーマを定義するファイルです。

【このファイルの役割】
- APIのリクエスト・レスポンスのデータ構造と型を定義します。
- Pydanticが自動的にバリデーション（入力値の検証）を行います。
- EmailStrを使ってメールアドレスの形式チェックも自動で行います。

【Pydanticスキーマとは？】
Pythonのクラスとして「どんなデータを受け取るか」を定義するものです。
FastAPIがリクエストを受け取ると、自動的にこのスキーマで検証してくれます。
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """
    ユーザー登録リクエストのスキーマ。
    POST /api/auth/register のリクエストボディに対応します。

    Attributes:
        email: メールアドレス（EmailStrで形式チェック）
        password: パスワード（8文字以上のバリデーション付き）
    """

    # EmailStr: "user@example.com"のような正しいメール形式かチェックする特別な型
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        """
        パスワードの長さを検証するバリデーター。
        8文字未満の場合はValidationErrorを発生させます。
        """
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上必要です")
        return v


class LoginRequest(BaseModel):
    """
    ログインリクエストのスキーマ。
    POST /api/auth/login のリクエストボディに対応します。

    Attributes:
        email: メールアドレス
        password: パスワード（バリデーションなし: 間違っていてもサーバー側で確認）
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    認証成功時のレスポンススキーマ。
    登録・ログイン・トークンリフレッシュ時に返されます。

    Attributes:
        access_token: APIアクセスに使う短命なJWTトークン（有効期限30分）
        refresh_token: アクセストークンを更新するための長命なJWTトークン（有効期限7日）
        token_type: トークンの種類（常に "bearer"）
    """

    access_token: str
    refresh_token: str
    # デフォルト値を設定しているので、レスポンスを作るとき token_type は省略可能
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """
    トークンリフレッシュリクエストのスキーマ。
    POST /api/auth/refresh のリクエストボディに対応します。

    Attributes:
        refresh_token: 保存しておいたリフレッシュトークン
    """

    refresh_token: str


class LogoutRequest(BaseModel):
    """
    ログアウトリクエストのスキーマ。
    POST /api/auth/logout のリクエストボディに対応します。

    Attributes:
        refresh_token: 無効化したいリフレッシュトークン
    """

    refresh_token: str


class MeResponse(BaseModel):
    """
    現在のユーザー情報レスポンススキーマ。
    GET /api/auth/me のレスポンスに対応します。

    Attributes:
        id: ユーザーID
        email: メールアドレス
        is_active: アカウントが有効かどうか
        created_at: アカウント作成日時
    """

    id: int
    email: str
    is_active: bool
    created_at: datetime

    # from_attributes=True: SQLAlchemyモデルのオブジェクトを直接変換できるようにする設定
    model_config = {"from_attributes": True}
