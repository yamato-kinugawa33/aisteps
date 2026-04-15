"""
main.py

FastAPIアプリケーションのエントリーポイントです。

【このファイルの役割】
- FastAPIアプリの設定（CORS・ミドルウェア・ルーターの登録）
- アプリ起動時のDB初期化

【新しく追加したもの】
- slowapi: レート制限ライブラリの設定（ブルートフォース攻撃対策）
- SecurityHeadersMiddleware: セキュリティヘッダーの自動付与
- auth router: 認証関連のエンドポイント群を登録
"""

import os

from dotenv import load_dotenv

# .envファイルを読み込む（DATABASE_URL, JWT_SECRET_KEY等の環境変数を設定する）
load_dotenv()

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from db.database import Base, engine  # noqa: E402
from middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402
from routers import roadmap  # noqa: E402
from routers import auth  # noqa: E402


# ─────────────────────────────────────────────
# レート制限の設定
# ─────────────────────────────────────────────

# Limiter: リクエスト元のIPアドレスを識別キーとしてレート制限を管理するオブジェクト
# 各エンドポイントに @limiter.limit("5/minute") のようにデコレータで制限を設定できる
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────────────────────
# アプリケーション起動・終了時のライフサイクル
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理。
    yield前: アプリ起動時に実行（DBテーブルの自動作成）
    yield後: アプリ終了時に実行（クリーンアップ処理）
    """
    # モデルをインポートして Base に登録する必要がある（テーブル定義を Base に認識させる）
    import models.user  # noqa: F401
    import models.roadmap  # noqa: F401

    # DBにテーブルが存在しない場合のみ新規作成する（既存テーブルには影響なし）
    Base.metadata.create_all(bind=engine)
    yield
    # アプリ終了時の処理（必要に応じてここに追加）


# ─────────────────────────────────────────────
# FastAPIアプリケーションの初期化
# ─────────────────────────────────────────────

app = FastAPI(
    title="Career Roadmap Generator",
    description="AIがキャリアロードマップを生成するAPIサーバー",
    lifespan=lifespan,
)

# slowapiの設定: アプリに Limiter を紐付ける
# RateLimitExceeded エラーが発生したときに 429 を返すハンドラーを登録
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─────────────────────────────────────────────
# ミドルウェアの設定（上から順に外側から処理される）
# ─────────────────────────────────────────────

# セキュリティヘッダーミドルウェア: 全レスポンスにセキュリティヘッダーを付与
app.add_middleware(SecurityHeadersMiddleware)

# CORS設定: フロントエンドのオリジンからのリクエストを許可する
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not any(origins):
    raise ValueError("ALLOWED_ORIGINS が設定されていません。.envファイルを確認してください")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    # 必要なHTTPメソッドのみ許可（"*" より安全）
    allow_methods=["GET", "POST"],
    # 必要なヘッダーのみ許可
    allow_headers=["Authorization", "Content-Type"],
)


# ─────────────────────────────────────────────
# ルーターの登録
# ─────────────────────────────────────────────

# 認証関連エンドポイント: /api/auth/*
app.include_router(auth.router)

# ロードマップ関連エンドポイント: /api/roadmaps/*
app.include_router(roadmap.router)


# ─────────────────────────────────────────────
# ヘルスチェックエンドポイント
# ─────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    """
    サーバーの稼働確認用エンドポイント。認証不要でアクセスできます。
    デプロイ環境のヘルスチェックに使用されます。
    """
    return {"status": "ok"}
