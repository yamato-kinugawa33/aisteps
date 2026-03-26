# キャリアロードマップ生成ツール

やりたいことを入力すると、AIが自己批判ループでキャリアロードマップを生成するWebアプリ。

## 技術スタック

- **Backend**: Python / FastAPI / SQLAlchemy
- **Frontend**: React / TypeScript / Vite
- **DB**: PostgreSQL
- **AI**: Gemini API (gemini-1.5-flash)
- **Deploy**: Railway

## ローカル開発

### 前提条件

- [uv](https://docs.astral.sh/uv/getting-started/installation/) （Pythonパッケージマネージャー）
- Node.js 18+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 1. 環境変数の設定

```bash
cp backend/.env.example backend/.env
# backend/.env を編集して GEMINI_API_KEY を設定
```

### 2. Docker で起動

```bash
docker compose up --build
```

| サービス | URL |
|----------|-----|
| フロントエンド | http://localhost:5173 |
| バックエンド API | http://localhost:8000 |
| DB | localhost:5432 |

テーブルはバックエンド起動時に自動作成されます。

### パッケージを追加する場合

```bash
# ローカルの uv でパッケージを追加（pyproject.toml と uv.lock を更新）
cd backend
uv add <package-name>

# イメージを再ビルドしてコンテナに反映
docker compose up --build
```

### ローカルに仮想環境を作る場合

Docker を使わずにバックエンドをローカルで直接実行したい場合は、`uv sync` で仮想環境を作成する。

```bash
cd backend
uv sync          # uv.lock の内容をもとに .venv を作成
uv run uvicorn main:app --reload
```

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `GEMINI_API_KEY` | Google AI Studio で取得 |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` |

## Gemini API キー取得

https://aistudio.google.com/app/apikey でAPIキーを発行してください。

## Railway デプロイ

1. Railway でプロジェクト作成
2. PostgreSQL プラグインを追加
3. 環境変数 `GEMINI_API_KEY` を設定
4. 環境変数 `ALLOWED_ORIGINS` を設定（フロントURL）
5. `DATABASE_URL` は Railway が自動設定
6. GitHub リポジトリを接続してデプロイ
