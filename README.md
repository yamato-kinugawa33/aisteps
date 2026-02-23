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

- Python 3.11+
- Node.js 18+
- PostgreSQL

### 1. バックエンド

```bash
cd backend
cp .env.example .env
# .env を編集して GEMINI_API_KEY と DATABASE_URL を設定

pip install -r requirements.txt
uvicorn main:app --reload
```

API: http://localhost:8000

### 2. フロントエンド

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173

### 3. DB 作成

```sql
CREATE DATABASE roadmap_db;
```

テーブルはバックエンド起動時に自動作成されます。

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `GEMINI_API_KEY` | Google AI Studio で取得 |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` |

## Gemini API キー取得

https://aistudio.google.com/app/apikey でAPIキーを発行してください。

## Railway デプロイ

1. Railway でプロジェクト作成
2. PostgreSQL プラグインを追加
3. 環境変数 `GEMINI_API_KEY` を設定
4. `DATABASE_URL` は Railway が自動設定
5. GitHub リポジトリを接続してデプロイ
