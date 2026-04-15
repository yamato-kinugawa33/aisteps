import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

from core.security import hash_password
from models.user import User


def make_user(
    email: str = "test@example.com",
    password: str = "Password123",
    is_active: bool = True,
) -> dict:
    """ユーザー作成用の辞書データを返す（DBには保存しない）"""
    return {
        "email": email,
        "password": password,
        "is_active": is_active,
    }


def create_user(
    db_session,
    email: str = "test@example.com",
    password: str = "Password123",
) -> User:
    """DBにユーザーを作成して返す"""
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
