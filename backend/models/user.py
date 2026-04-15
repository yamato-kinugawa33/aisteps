"""
models/user.py

usersテーブルのSQLAlchemyモデルを定義するファイルです。

【このファイルの役割】
- データベースの「users」テーブルの構造をPythonクラスとして表現します。
- SQLAlchemyのORM（Object-Relational Mapping）を使うことで、
  SQLを直接書かずにPythonオブジェクトとしてDBを操作できます。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class User(Base):
    """
    ユーザー情報を保存するテーブルのモデルクラス。

    カラム:
        id: ユーザーの一意なID（自動採番）
        email: メールアドレス（ログインに使用、重複不可）
        hashed_password: bcryptでハッシュ化されたパスワード（平文は保存しない）
        is_active: アカウントが有効かどうか（無効化機能に使用）
        failed_login_count: ログイン失敗回数（アカウントロックに使用）
        locked_until: アカウントロックの解除日時（Noneなら未ロック）
        created_at: アカウント作成日時
        updated_at: 最終更新日時
    """

    __tablename__ = "users"

    # 主キー: 整数の自動採番ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # メールアドレス: ユニーク制約あり（同じメールアドレスは1つだけ）
    # index=True: メールアドレスでの検索を高速化するためインデックスを張る
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # パスワードのbcryptハッシュ値（絶対に平文パスワードを保存しないこと）
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # アカウントの有効フラグ（Falseにするとログイン不可）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ログイン失敗回数: 5回以上でアカウントをロックする
    failed_login_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # アカウントロック解除日時: この日時を過ぎるとロックが解除される（Noneはロックなし）
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # レコードの作成日時: DBサーバーの現在時刻で自動設定
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # レコードの更新日時: 更新するたびに自動で現在時刻に更新される
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
