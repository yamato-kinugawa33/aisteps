"""
models/refresh_token.py

リフレッシュトークンをDBで管理するためのモデルです。

【なぜDBでリフレッシュトークンを管理するのか？】
JWTはサーバーが「秘密鍵を知っていれば」誰でも検証できる「ステートレス」な仕組みです。
つまり一度発行したJWTは、有効期限が来るまで無効化できません。

リフレッシュトークン（7日間有効）を盗まれた場合に即座に無効化できるよう、
DB側でレコードを管理します。ログアウト時やリプレイ攻撃検知時に
DBのis_revokedをTrueにするだけで即座に使用不可にできます。

【Refresh Token Rotationとは？】
リフレッシュトークンを使うたびに古いトークンを失効させ、新しいトークンを発行します。
もし古いトークンが再利用されたら（リプレイ攻撃）、
そのユーザーの全セッションを強制終了します。

【セキュリティ: トークン値はハッシュ化して保存】
リフレッシュトークンの生の値（raw token）はDBに保存しません。
SHA-256でハッシュ化した値のみを保存し、生の値はレスポンスとCookieにのみ含めます。
DBが漏洩してもトークンそのものは復元できません。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class RefreshToken(Base):
    """
    リフレッシュトークンのDBレコードを表すモデルクラス。

    カラム:
        id: レコードの一意なID
        user_id: どのユーザーのトークンか（usersテーブルへの外部キー）
        token_hash: SHA-256でハッシュ化したトークン値（生の値は保存しない）
        is_revoked: 失効済みかどうか（True = 使用不可）
        expires_at: トークンの有効期限（この日時を過ぎると使用不可）
        created_at: レコードの作成日時
    """

    __tablename__ = "refresh_tokens"

    # 主キー
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # どのユーザーのトークンか（usersテーブルのidと紐付ける）
    # ForeignKey: 参照先のテーブル.カラム名を指定
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # トークンのSHA-256ハッシュ値（検索に使うためインデックスを張る）
    # raw tokenではなくハッシュのみを保存（セキュリティのため）
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    # 失効フラグ: ログアウト・パスワード変更・リプレイ攻撃検知時にTrueにする
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # トークンの有効期限（7日後に設定される）
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # レコード作成日時
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
