# CI でのテスト実行

## CI テストとは

CI（継続的インテグレーション）は、コードを push または PR を作成するたびに自動でテストを実行する仕組みです。
人間が「テストを実行し忘れる」ことをなくし、問題を早期に検知します。

```
開発者が push
    ↓
GitHub Actions が自動起動
    ↓
テスト実行（全パスしたか？）
    ↓
PR のマージ可否に反映（ブランチ保護と組み合わせる）
```

---

## GitHub Actions の基本構造

設定ファイルは `.github/workflows/*.yml` に置きます。

```
.github/
└── workflows/
    ├── lint.yml     # リント
    └── test.yml     # テスト ← 今回追加
```

### yml ファイルの基本構造

```yaml
name: Test                      # Actions タブに表示される名前

on: [push, pull_request]        # 実行トリガー

jobs:
  job-name:                     # ジョブ名（自由に付ける）
    runs-on: ubuntu-latest      # 実行環境
    steps:
      - uses: actions/checkout@v4   # ステップ
      - run: echo "hello"           # ステップ
```

---

## 各オプションの説明

### `on`：実行トリガー

```yaml
# シンプルな書き方（push と PR 両方）
on: [push, pull_request]

# 詳細な書き方（ブランチを絞る）
on:
  push:
    branches: [main, develop]   # main と develop への push のみ
  pull_request:
    branches: [main]            # main への PR のみ
```

### `jobs`：並列実行の単位

job は**並列実行**されます。unit と integration を分けると、どちらが失敗したか一目でわかります。

```yaml
jobs:
  backend-unit:        # ← 並列実行
    ...
  backend-integration: # ← 並列実行
    ...
```

job 間に依存関係を持たせたい場合は `needs` を使います。

```yaml
jobs:
  test:
    ...
  deploy:
    needs: test   # test が成功したあとに deploy を実行
```

### `runs-on`：実行環境

```yaml
runs-on: ubuntu-latest   # Ubuntu（最も一般的）
runs-on: macos-latest    # macOS
runs-on: windows-latest  # Windows
```

### `defaults.run.working-directory`：作業ディレクトリ

monorepo でバックエンド・フロントエンドが分かれている場合に使います。

```yaml
defaults:
  run:
    working-directory: backend   # 全 run コマンドが backend/ で実行される
```

### `steps`：実行するステップ

```yaml
steps:
  # uses: 公開 Action を使う
  - uses: actions/checkout@v4        # リポジトリをチェックアウト
  - uses: astral-sh/setup-uv@v5      # uv をセットアップ

  # run: シェルコマンドを実行
  - run: uv sync
  - run: uv run pytest tests/unit/ -q

  # name: ステップに名前を付ける（省略可）
  - name: Run tests
    run: uv run pytest tests/ -q
```

### `env`：環境変数

```yaml
env:
  # シークレットから取得（GitHub Settings で登録）
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}

  # フォールバック付き（シークレット未登録でも CI が動く）
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY || 'fallback-value' }}

  # 固定値（秘密情報でないもの）
  ALLOWED_ORIGINS: http://localhost:5173
```

---

## シークレットの登録方法

本番用の API キーなど秘密情報は yml に直接書かず、GitHub の Secrets に登録します。

1. GitHub のリポジトリページを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. Name と Value を入力して保存
5. yml 内で `${{ secrets.SECRET_NAME }}` として参照

> **注意**: Secrets に登録した値はログに `***` として表示され、中身は見えません。

---

## このプロジェクトの構成

```yaml
# test.yml の構成
backend-unit:
  # SQLite インメモリを使うため DB サービス不要
  # conftest.py が環境変数のデフォルト値を設定する
  - uv run pytest tests/unit/ -q

backend-integration:
  # 同上（conftest.py が SQLite に差し替えるため PostgreSQL 不要）
  - uv run pytest tests/integration/ -q
```

テストの DB は `conftest.py` で SQLite インメモリに差し替えているため、
CI 環境に PostgreSQL を用意する必要はありません。

---

## ブランチ保護ルールの設定（マージ前にテスト必須にする）

1. GitHub の **Settings** → **Branches**
2. **Add branch protection rule** をクリック
3. Branch name pattern に `main` を入力
4. **Require status checks to pass before merging** にチェック
5. 必須にしたいジョブ名（`Backend Unit Tests` など）を検索して追加
6. **Save changes**

これで、テストが失敗した PR は main にマージできなくなります。

---

## よく使う pytest オプション

```bash
uv run pytest tests/unit/ -q          # quiet モード（簡潔な出力）
uv run pytest tests/ -v               # verbose（テスト名を全表示）
uv run pytest tests/ --tb=short       # 失敗時のトレースバックを短縮
uv run pytest tests/unit/ tests/integration/ -q  # 複数ディレクトリ指定
```
