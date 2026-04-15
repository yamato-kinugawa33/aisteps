import os

# テスト用環境変数を最初に設定する（モジュールインポート前に必要）
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://localhost/test"
)  # get_dbをオーバーライドするので実際には使わない
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

# NOTE: database.py はインポート時に DATABASE_URL を検証するため、
# 上記の os.environ.setdefault の後にインポートする必要がある
from db.database import Base, get_db  # noqa: E402

# SQLiteインメモリDBを使用（CIやローカルで外部DBなしで動作）
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# SQLiteでは外部キー制約が無効なので有効化する
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# JSONB -> JSON の型置換はDDL発行前に行う必要がある
# テーブル作成前にカラムの型を上書きする
def _patch_jsonb_columns():
    """SQLiteでJSONBを使っているカラムをJSONに置き換える"""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()


TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


@pytest.fixture(scope="session")
def setup_db():
    """テスト用DBのテーブル作成・削除（session scope）"""
    # モデルを全てインポートして Base に登録する
    import models.roadmap  # noqa: F401
    import models.refresh_token  # noqa: F401
    import models.user  # noqa: F401

    # SQLiteのためJSONB -> JSON に型を置き換える
    _patch_jsonb_columns()

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_db):
    """各テスト後にロールバックするDBセッション"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """DB差し替え済みのFastAPI TestClient"""
    # main.pyのインポート時にDBへの接続が発生するため、遅延インポートする
    from main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """事前登録済みユーザー情報"""
    user_data = {"email": "testuser@example.com", "password": "Password123"}
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    return user_data


@pytest.fixture
def auth_headers(client, registered_user):
    """{"Authorization": "Bearer <token>"} 形式のヘッダー"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
