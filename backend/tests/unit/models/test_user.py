"""
【Unitテスト】Userモデルの構造テスト
DB接続不要（テーブル定義のテスト）
"""

from models.user import User


class TestUserModel:
    def test_tablename(self):
        """テーブル名が "users" であること"""
        assert User.__tablename__ == "users"

    def test_columns_exist(self):
        """必要なカラムが全て存在すること"""
        columns = {c.name for c in User.__table__.columns}
        expected = {
            "id",
            "email",
            "hashed_password",
            "is_active",
            "failed_login_count",
            "locked_until",
            "created_at",
            "updated_at",
        }
        assert expected == columns

    def test_email_is_unique(self):
        """emailカラムにunique制約があること"""
        email_col = User.__table__.columns["email"]
        assert email_col.unique is True
