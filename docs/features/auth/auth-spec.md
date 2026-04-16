# ログイン認証機能 仕様書

**プロジェクト**: aisteps  
**作成日**: 2026-04-16  
**対象機能**: ログイン認証機能（ユーザー登録・ログイン・セッション管理・パスワードリセット）

---

## 目次

1. [要件定義](#1-要件定義)
2. [実装スケジュール](#2-実装スケジュール)
3. [技術設計](#3-技術設計)
4. [テスト計画](#4-テスト計画)
5. [UIデザイン仕様](#5-uiデザイン仕様)
6. [セキュリティ仕様](#6-セキュリティ仕様)

---

## 1. 要件定義

### 機能要件

#### 1.1 ユーザー登録
- メールアドレスとパスワードによる新規アカウント作成
- メールアドレスの重複チェック（既存アカウントとの照合）
- パスワードの強度バリデーション（8文字以上、英数字混在）
- 登録完了後、自動ログイン状態にしてホーム画面へリダイレクト
- 将来的な拡張として、メール確認（Email Verification）フローを考慮した設計にする

#### 1.2 ログイン
- メールアドレスとパスワードによる認証
- 認証成功後、JWTトークン（アクセストークン + リフレッシュトークン）を発行
- ログイン失敗時の汎用エラーメッセージ（「メールアドレスまたはパスワードが正しくありません」）
- 連続ログイン失敗時のアカウントロック機能（5回失敗で15分ロック）

#### 1.3 ログアウト
- フロントエンドのトークン（localStorage または httpOnly Cookie）を削除
- リフレッシュトークンをサーバー側でブラックリスト登録し無効化

#### 1.4 セッション管理
- アクセストークンの有効期限：30分
- リフレッシュトークンの有効期限：7日
- アクセストークン期限切れ時、リフレッシュトークンで自動更新（サイレントリフレッシュ）
- リフレッシュトークンの使い回し防止（Refresh Token Rotation）

#### 1.5 認証付きロードマップ生成
- 未ログイン状態でロードマップ生成を試みた場合、ログイン画面へリダイレクト
- ログイン済みユーザーのロードマップ生成履歴をユーザーアカウントに紐付けて保存
- 認証が必要なAPIエンドポイントへのBearerトークン送信

#### 1.6 パスワードリセット（フェーズ2）
- メールアドレスを入力してリセット用URLを受信
- リセットトークンの有効期限：1時間
- リセット完了後、既存のリフレッシュトークンを全無効化

### 非機能要件

#### セキュリティ
- パスワードは bcrypt（cost factor 12以上）でハッシュ化して保存
- JWTの署名アルゴリズムは HS256（将来的にRS256へ移行を検討）
- httpOnly + SameSite=Strict Cookie によるトークン保存（XSS対策）
- CORS設定：フロントエンドのオリジンのみ許可
- SQLインジェクション対策：SQLAlchemy ORMのパラメータバインディングを必ず使用
- HTTPS通信を前提とした設計（本番環境）
- ログイン試行のレート制限（同一IPから1分間に10回まで）

#### 性能
- ログインAPIのレスポンスタイム：p99 で500ms以内
- トークン検証処理：p99 で50ms以内（DBアクセス不要なJWT署名検証）
- 同時接続100ユーザーでの正常動作を保証

#### 可用性
- 認証サービスの可用性：99.9%以上（月間ダウンタイム43分以内）
- リフレッシュトークンのストア（DB）は既存のPostgreSQLを使用し、別途インフラを増やさない

#### 保守性
- 認証ロジックは既存のレイヤー構成（`backend/` 配下）に沿ったディレクトリ構造で実装
- 認証関連のコードは `auth` モジュールに集約し、他機能から疎結合に保つ
- テストカバレッジ：認証関連ロジックで80%以上

### ユーザーストーリー

| # | ロール | ストーリー | 受け入れ条件 |
|---|--------|-----------|-------------|
| US-01 | 新規ユーザー | メールとパスワードで登録したい | 登録フォームに入力→送信後、自動ログインされホームへ遷移する |
| US-02 | 登録済みユーザー | メールとパスワードでログインしたい | 正しい情報を入力→ホームへ遷移し、ヘッダーにアカウント名が表示される |
| US-03 | ログイン済みユーザー | ログアウトしたい | ヘッダーのログアウトボタン押下→ログイン画面へ遷移し、保護されたページへアクセス不可になる |
| US-04 | ログイン済みユーザー | ロードマップを生成して履歴を残したい | 生成したロードマップが自分のアカウントに紐付いて保存・参照できる |
| US-05 | 未ログインユーザー | ロードマップ生成を試みたとき | ログインページへリダイレクトされ、ログイン後に元の操作へ戻れる |
| US-06 | ログイン済みユーザー | 長時間利用してもログアウトされたくない | 操作中はサイレントリフレッシュで継続利用でき、7日間操作なしで自動ログアウトされる |
| US-07 | ユーザー | パスワードを忘れた | メールアドレスを入力してリセットメールを受信し、新パスワードを設定できる（フェーズ2） |

---

## 2. 実装スケジュール

### 前提条件・方針
- 開発者：1名（フルスタック）
- 1スプリント = 1週間
- 優先度：高 / 中 / 低 の3段階
- 工数単位：時間（h）

### フェーズ1：認証基盤の実装（Week 1〜2）

**目標：** バックエンドの認証APIとDBスキーマを完成させる

| タスクID | タスク名 | 優先度 | 工数 | 完了条件 |
|----------|---------|--------|------|---------|
| T-01 | DBスキーマ設計・マイグレーション（`users`・`refresh_tokens`テーブル） | 高 | 3h | Alembicマイグレーション適用済み |
| T-02 | ユーザー登録API（`POST /api/auth/register`） | 高 | 4h | バリデーション・bcryptハッシュ化・JWT発行まで動作 |
| T-03 | ログインAPI（`POST /api/auth/login`） | 高 | 4h | アクセストークン＋リフレッシュトークン発行、ロック機能込み |
| T-04 | トークンリフレッシュAPI（`POST /api/auth/refresh`） | 高 | 3h | Rotation実装、古いトークンの無効化 |
| T-05 | ログアウトAPI（`POST /api/auth/logout`） | 高 | 2h | リフレッシュトークンのブラックリスト登録 |
| T-06 | JWT検証ミドルウェア・依存関数（`get_current_user`） | 高 | 3h | 保護されたエンドポイントへの適用テスト済み |
| T-07 | 既存ロードマップAPIへの認証ガード追加 | 高 | 2h | 未認証リクエストで401が返る |
| T-08 | バックエンド認証ロジックの単体テスト（pytest） | 高 | 4h | カバレッジ80%以上 |

**Week 1〜2 合計工数目安：** 約25h

### フェーズ2：フロントエンド認証UIの実装（Week 3〜4）

**目標：** ログイン・登録画面の作成とAPIとの結合

| タスクID | タスク名 | 優先度 | 工数 | 完了条件 |
|----------|---------|--------|------|---------|
| T-09 | 認証状態管理（React Context + useReducer）の実装 | 高 | 4h | ログイン状態のグローバル管理、リロード後も維持 |
| T-10 | ログイン画面（`/login`）の実装 | 高 | 4h | フォームバリデーション・エラー表示・API呼び出し |
| T-11 | ユーザー登録画面（`/register`）の実装 | 高 | 4h | フォームバリデーション・エラー表示・API呼び出し |
| T-12 | サイレントリフレッシュ処理の実装（Axios Interceptor等） | 高 | 4h | アクセストークン期限切れ時に自動更新される |
| T-13 | PrivateRoute（認証ガード）コンポーネントの実装 | 高 | 3h | 未ログイン状態でのアクセス時、`/login`へリダイレクト |
| T-14 | ヘッダーへのログイン状態表示・ログアウトボタン追加 | 中 | 3h | ログイン中はユーザー名表示、ログアウトで状態クリア |
| T-15 | ロードマップ生成履歴のユーザー紐付け対応（フロント側） | 中 | 3h | 生成後、自分の履歴として一覧表示される |

**Week 3〜4 合計工数目安：** 約25h

### フェーズ3：セキュリティ強化・パスワードリセット（Week 5〜6）

**目標：** パスワードリセット機能とセキュリティ仕上げ

| タスクID | タスク名 | 優先度 | 工数 | 完了条件 |
|----------|---------|--------|------|---------|
| T-16 | パスワードリセットメール送信API | 中 | 5h | トークン生成・メール送信動作確認 |
| T-17 | パスワードリセット実行API | 中 | 3h | トークン検証・パスワード更新・既存セッション全無効化 |
| T-18 | パスワードリセット画面（`/forgot-password`）の実装 | 中 | 4h | メール入力・新パスワード入力フォームの動作確認 |
| T-19 | レート制限設定（`slowapi`導入） | 高 | 2h | `/api/auth/*` エンドポイントに適用済み |
| T-20 | E2Eテスト（登録→ログイン→ロードマップ生成→ログアウトの基本フロー） | 中 | 6h | Playwrightでのシナリオテスト全パス |
| T-21 | 本番環境向けセキュリティ確認（HTTPS・Cookie設定・CORS最終確認） | 高 | 3h | セキュリティチェックリスト全項目クリア |

**Week 5〜6 合計工数目安：** 約23h

### マイルストーン

| マイルストーン | 期日 | 達成条件 |
|--------------|------|---------|
| M1: 認証API完成 | Week 2末（2026-04-29） | 全認証APIがcurlで動作確認済み |
| M2: フロント結合完了 | Week 4末（2026-05-13） | ブラウザ上でログイン〜ロードマップ生成が一気通貫で動作 |
| M3: 機能完成・テスト完了 | Week 6末（2026-05-27） | パスワードリセット含む全機能完成、テストカバレッジ達成 |

### リスクと対策

| リスク | 影響度 | 対策 |
|-------|--------|------|
| リフレッシュトークン管理の実装複雑化 | 高 | フェーズ1で早期にスパイク実装・検証を行う |
| メール送信サービスの選定・設定コスト | 中 | フェーズ3まで後回しにし、フェーズ1〜2はSMTPモック対応 |
| 既存ロードマップデータとのユーザー紐付け | 中 | 既存データはNULL許容で移行し、新規データから紐付け開始 |

---

## 3. 技術設計

### アーキテクチャ概要

#### 認証方式：JWT（Bearer Token）採用

| 観点 | JWT | Server Session |
|------|-----|----------------|
| スケーラビリティ | サーバーレスで水平スケール可 | セッションストア必要（Redis等） |
| 現構成との親和性 | 現 FastAPI がステートレスなので自然 | DB/Redis追加コストが発生 |
| Railway デプロイ | 追加インフラ不要 | Redis追加が必要 |

**トークン仕様：**
- アクセストークン：有効期限 30分、HS256署名
- リフレッシュトークン：有効期限 7日、DB保存（失効管理のため）

#### 認証フロー

```
[Browser]                        [FastAPI]                     [PostgreSQL]
   |                                 |                               |
   |-- POST /api/auth/register ----->|                               |
   |                                 |-- INSERT users -------------->|
   |<-- { access_token, refresh } ---|                               |
   |                                 |                               |
   |-- POST /api/auth/login -------->|                               |
   |                                 |-- SELECT user (email) ------->|
   |                                 |   verify bcrypt hash          |
   |<-- { access_token, refresh } ---|                               |
   |                                 |                               |
   |-- GET /api/roadmaps             |                               |
   |   Authorization: Bearer <JWT> ->|                               |
   |                                 |   verify JWT signature        |
   |<-- [roadmap list] --------------|                               |
```

### バックエンド設計

#### データモデル

**`backend/models/user.py`**
```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

**`backend/models/refresh_token.py`**
```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

> **セキュリティ方針：** リフレッシュトークンはDB保存前にSHA-256ハッシュ化。生トークンはレスポンス時のみ返す。

#### APIエンドポイント設計

| Method | Path | 認証要否 | 説明 |
|--------|------|----------|------|
| POST | `/api/auth/register` | 不要 | 新規ユーザー登録 |
| POST | `/api/auth/login` | 不要 | メール+パスワードでログイン |
| POST | `/api/auth/logout` | 必要（Bearer） | リフレッシュトークン失効 |
| POST | `/api/auth/refresh` | 不要（refresh_token） | アクセストークン再発行 |
| GET | `/api/auth/me` | 必要（Bearer） | 現在のユーザー情報取得 |

#### JWTペイロード設計

```json
{
  "sub": "42",
  "exp": 1744123456,
  "iat": 1744121656,
  "type": "access"
}
```

#### 追加ファイル一覧

| ファイルパス | 役割 |
|-------------|------|
| `backend/models/user.py` | User SQLAlchemy モデル |
| `backend/models/refresh_token.py` | RefreshToken SQLAlchemy モデル |
| `backend/schemas/auth.py` | 認証関連 Pydantic スキーマ |
| `backend/routers/auth.py` | `/api/auth/*` エンドポイント定義 |
| `backend/services/auth.py` | JWT生成・検証・ハッシュ処理のビジネスロジック |
| `backend/core/security.py` | bcrypt ハッシュ、JWT encode/decode ユーティリティ |
| `backend/core/dependencies.py` | `get_current_user` FastAPI Depends 関数 |

#### `backend/core/security.py`

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("パスワードが空です")
    return pwd_context.hash(password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        SECRET_KEY, algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise ValueError("無効なトークンです")
    if payload.get("type") != "access":
        raise ValueError("トークン種別が不正です")
    return int(payload["sub"])
```

#### `backend/core/dependencies.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from db.database import get_db
from core.security import decode_access_token
from models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        user_id = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
    return user
```

#### 追加パッケージ（pyproject.toml）

```toml
"python-jose[cryptography]>=3.3.0",
"passlib[bcrypt]>=1.7.4",
"slowapi>=0.1.9",
```

### フロントエンド設計

#### コンポーネント設計

| コンポーネント | ファイルパス | 役割 |
|--------------|-------------|------|
| `LoginPage` | `src/pages/LoginPage.tsx` | ログインフォーム |
| `RegisterPage` | `src/pages/RegisterPage.tsx` | 新規登録フォーム |
| `AuthGuard` | `src/components/auth/AuthGuard.tsx` | 未認証時リダイレクト |
| `AuthProvider` | `src/contexts/AuthContext.tsx` | 認証状態のコンテキスト提供 |

#### 状態管理（AuthContext）

```tsx
// src/contexts/AuthContext.tsx
interface AuthState {
  user: { id: number; email: string } | null;
  accessToken: string | null;
  isLoading: boolean;
}
```

**方針：** React Context + `useReducer` でグローバル認証状態を管理。リフレッシュトークンは `localStorage` に保存。

#### ルーティング（react-router-dom v6）

```tsx
// src/App.tsx
<BrowserRouter>
  <AuthProvider>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <AuthGuard>
            <MainPage />
          </AuthGuard>
        }
      />
    </Routes>
  </AuthProvider>
</BrowserRouter>
```

#### `src/api/auth.ts`（新規追加）

```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function loginApi(email: string, password: string) {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("認証失敗");
  return res.json() as Promise<{ access_token: string; refresh_token: string; token_type: string }>;
}

export async function refreshTokenApi(refreshToken: string) {
  const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) throw new Error("トークン更新失敗");
  return res.json() as Promise<{ access_token: string }>;
}
```

#### 実装優先順位

| フェーズ | 内容 |
|---------|------|
| Phase 1 | `models/user.py`、`core/security.py`、`routers/auth.py`（register/login/refresh/me）実装 |
| Phase 2 | `models/refresh_token.py` によるリフレッシュトークン管理・ログアウト実装 |
| Phase 3 | フロントエンド：`AuthContext`・`LoginPage`・`RegisterPage`・`AuthGuard` 実装 |
| Phase 4 | 既存 `/api/roadmaps` エンドポイントへ `get_current_user` Depends 付与 |

#### 環境変数追加

```
JWT_SECRET_KEY=<openssl rand -hex 32 で生成>
```

---

## 4. テスト計画

### テスト戦略

**TDDアプローチ（RED → GREEN → REFACTOR）**

```
        /\
       /E2E\        ← 少数・高コスト（Playwright: 主要フロー 5〜8件）
      /------\
     /  統合   \     ← 中程度（pytest TestClient: 15〜20件）
    /----------\
   /  Unit Test \   ← 多数・低コスト（pytest: 40〜50件）
  /--------------\
```

| レイヤー | ツール | 目標件数 | 実行タイミング |
|---------|-------|---------|-------------|
| Unit | pytest | 40〜50件 | pre-commit / CI push |
| Integration | pytest + TestClient | 15〜20件 | CI push |
| E2E | Playwright | 5〜8件 | CI merge前 |

### Unit Test 計画

#### `tests/schemas/test_auth.py`

```python
class TestUserCreateSchema:
    def test_valid_input(self): ...
    def test_invalid_email_format(self): ...   # 422 期待
    def test_password_too_short(self): ...     # 8文字未満 → 422
    def test_missing_email(self): ...
    def test_missing_password(self): ...
```

#### `tests/services/test_auth.py`

```python
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self): ...
    def test_verify_correct_password(self): ...
    def test_verify_wrong_password(self): ...
    def test_same_password_produces_different_hashes(self): ...  # ソルト確認
    def test_empty_password_raises(self): ...

class TestJWTToken:
    def test_create_and_decode_token(self): ...
    def test_expired_token_raises(self): ...
    def test_tampered_token_raises(self): ...
    def test_token_contains_expiry(self): ...
```

### Integration Test 計画

#### テスト用フィクスチャ（`tests/conftest.py`）

```python
@pytest.fixture(scope="session", autouse=True)
def setup_db(): ...          # テーブル作成・削除

@pytest.fixture()
def db_session(): ...        # ロールバック付きセッション

@pytest.fixture()
def client(db_session): ...  # DB差し替え済み TestClient

@pytest.fixture()
def registered_user(client): ...  # 事前登録ユーザー

@pytest.fixture()
def auth_headers(client, registered_user): ...  # Bearer ヘッダー
```

#### `tests/routers/test_auth.py`

```python
class TestRegister:
    def test_register_success(self): ...               # 201
    def test_register_duplicate_email(self): ...       # 409
    def test_register_invalid_email(self): ...         # 422
    def test_register_weak_password(self): ...         # 422

class TestLogin:
    def test_login_success(self): ...                  # 200 + JWT
    def test_login_wrong_password(self): ...           # 401
    def test_login_nonexistent_user(self): ...         # 401

class TestProtectedEndpoints:
    def test_get_roadmaps_without_token(self): ...     # 401
    def test_get_roadmaps_with_valid_token(self): ...  # 200
    def test_get_roadmaps_with_invalid_token(self): .. # 401
    def test_get_roadmaps_with_expired_token(self): .. # 401

class TestPasswordReset:
    def test_reset_existing_email(self): ...           # 200
    def test_reset_nonexistent_email(self): ...        # 200（存在有無を漏らさない）
    def test_reset_with_invalid_token(self): ...       # 400
```

### E2E Test 計画（Playwright）

```python
# frontend/tests/e2e/test_auth.py

class TestUserRegistration:
    def test_successful_registration(self, page): ...
    def test_registration_with_existing_email(self, page): ...

class TestLoginLogout:
    def test_successful_login(self, page): ...
    def test_login_with_wrong_password(self, page): ...
    def test_logout(self, page): ...

class TestProtectedPageAccess:
    def test_unauthenticated_redirect_to_login(self, page): ...
    def test_roadmap_generation_requires_login(self, page): ...
```

### テストデータ管理（`tests/factories.py`）

```python
def make_user(email="default@example.com", password="Password123", is_active=True) -> dict:
    return {"email": email, "hashed_password": hash_password(password), "is_active": is_active}

def create_user(db_session, **kwargs) -> User: ...
def create_roadmap(db_session, user_id: int, goal: str = "テスト目標") -> Roadmap: ...
```

### テストカバレッジ目標

| モジュール | 目標カバレッジ |
|-----------|-------------|
| `services/auth.py` | **95%以上** |
| `routers/auth.py` | **90%以上** |
| `schemas/auth.py` | **90%以上** |
| 全体 | **85%以上** |

```bash
uv run pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=85
```

### TDD 実装推奨順序

```
Phase 1（Unit）
  1. tests/schemas/test_auth.py → schemas/auth.py
  2. tests/services/test_auth.py → services/auth.py
  3. tests/models/test_user.py → models/user.py

Phase 2（Integration）
  4. tests/routers/test_auth.py → routers/auth.py
  5. Roadmap エンドポイントに認証ガードを追加

Phase 3（E2E）
  6. フロントエンドに認証 UI を実装
  7. frontend/tests/e2e/test_auth.py を実行して確認
```

---

## 5. UIデザイン仕様

### デザイン原則

| 原則 | 意図 |
|---|---|
| **信頼感** | 清潔な白背景と整合したレイアウトで安心感を演出 |
| **一貫性** | 既存のロードマップ画面と同じカラートークン・角丸・シャドウを使用 |
| **シンプル** | 入力フィールドは最小限に絞り、「ゴールへ進む」ことを優先 |
| **フィードバック** | バリデーション・ローディング・エラーを即時・明瞭に伝える |

### デザイントークン

```css
/* ブランドカラー */
--color-primary:        #6c63ff;
--color-primary-hover:  #574fd6;
--color-primary-light:  #f0eeff;

/* テキスト */
--color-text-base:      #1a1a2e;
--color-text-muted:     #555555;

/* 背景・ボーダー */
--color-bg-page:        #f5f7fa;
--color-bg-card:        #ffffff;
--color-border-default: #e0e0e0;
--color-border-focus:   #6c63ff;
--color-border-error:   #e53935;

/* セマンティック */
--color-error-bg:       #fff0f0;
--color-error-text:     #c62828;
--color-success:        #4caf50;
--color-success-bg:     #e8f5e9;
--color-info-bg:        #e3f2fd;

/* シャドウ・角丸 */
--shadow-card: 0 2px 8px rgba(0, 0, 0, 0.08);
--radius-lg:   12px;
```

### 認証ページ一覧

| ページ名 | パス | 概要 |
|---|---|---|
| ログインページ | `/login` | メール + パスワードで認証 |
| 新規登録ページ | `/register` | アカウント作成 |
| パスワードリセット申請 | `/forgot-password` | リセットリンク送信 |
| メール認証完了 | `/email-verified` | 登録・リセット完了通知 |

### ワイヤーフレーム（共通レイアウト）

```
┌─────────────────────────────────────────────────┐
│                  <ページ背景 #f5f7fa>             │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │    [アイコン]  aisteps                     │  │
│  │    AIがあなたのキャリアをナビゲート          │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │      認証カード（max-width: 420px）         │  │
│  │      background: #fff / border-radius: 12px│  │
│  │                                            │  │
│  │  [ページ固有のコンテンツ]                  │  │
│  │                                            │  │
│  └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### ワイヤーフレーム（ログインページ）

```
┌────────────────────────────────────────┐
│  ログイン                               │
│  ─────────────────────────────────     │
│                                         │
│  メールアドレス                         │
│  ┌─────────────────────────────────┐   │
│  │  user@example.com               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  パスワード                             │
│  ┌───────────────────────────── [👁]┐  │
│  │  ••••••••                        │   │
│  └─────────────────────────────────┘   │
│                        [パスワードを忘れた方] │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │         ログイン                │   │
│  └─────────────────────────────────┘   │
│                                         │
│  アカウントをお持ちでない方 → 新規登録  │
└────────────────────────────────────────┘
```

### ワイヤーフレーム（新規登録ページ）

```
┌────────────────────────────────────────┐
│  新規登録                               │
│  ─────────────────────────────────     │
│                                         │
│  メールアドレス                         │
│  ┌─────────────────────────────────┐   │
│  │  user@example.com               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  パスワード                             │
│  ┌───────────────────────────── [👁]┐  │
│  │  ••••••••                        │   │
│  └─────────────────────────────────┘   │
│  ○───●────────── パスワード強度メーター │
│  8文字以上・英数字混在                  │
│                                         │
│  パスワード（確認）                     │
│  ┌───────────────────────────── [👁]┐  │
│  │  ••••••••                        │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ☐ 利用規約・プライバシーポリシーに同意 │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │       アカウントを作成           │   │
│  └─────────────────────────────────┘   │
│                                         │
│  既にアカウントをお持ちの方 → ログイン  │
└────────────────────────────────────────┘
```

### コンポーネント設計

| コンポーネント | ファイルパス | 役割 |
|--------------|-------------|------|
| `AuthCard` | `src/components/auth/AuthCard.tsx` | 共通カードラッパー |
| `AuthInput` | `src/components/auth/AuthInput.tsx` | 入力フィールド（バリデーション付き） |
| `AuthButton` | `src/components/auth/AuthButton.tsx` | 送信・ソーシャルボタン |
| `AlertBox` | `src/components/auth/AlertBox.tsx` | フォームレベルアラート |
| `PasswordStrengthMeter` | `src/components/auth/PasswordStrengthMeter.tsx` | パスワード強度メーター |

### エラー状態のUI

| レベル | トリガー | 表示箇所 |
|---|---|---|
| フィールドレベル | blur時 / フォーム送信時 | 入力欄直下（赤文字） |
| フォームレベル | APIエラー | フォーム最上部（赤いアラートボックス） |
| ネットワークエラー | fetch失敗 | フォーム最上部 |

**APIエラーメッセージ対応表：**

| HTTPステータス | 表示メッセージ |
|---|---|
| 401 | 「メールアドレスまたはパスワードが正しくありません」 |
| 409 | 「このメールアドレスはすでに登録されています」 |
| 429 | 「試行回数が上限に達しました。しばらく時間をおいて再試行してください」 |
| 500 | 「サーバーエラーが発生しました。時間をおいて再試行してください」 |

> 401系は「メールが存在しない」「パスワードが違う」を個別に表示しないこと（ユーザー存在有無の漏洩防止）。

### バリデーションタイミング

```
入力中（onChange）: パスワード強度メーターのみ更新（エラー表示しない）
フォーカスアウト（onBlur）: 入力済みフィールドのみバリデーション実行
フォーム送信（onSubmit）: 全フィールドを一括バリデーション → エラーがあればAPIコール中断
```

### レスポンシブ対応

| ブレークポイント | 幅 | 対応 |
|---|---|---|
| `sm` | 0〜479px | カードが画面幅いっぱい（左右16pxマージン） |
| `md` | 480〜767px | カード 420px固定 |
| `lg` | 768px〜 | カード 420px固定・垂直中央寄せ |

### アクセシビリティ（WCAG 2.1 AA）チェックリスト

- [ ] `<label>` と `<input>` を `htmlFor`/`id` で正しく紐付ける
- [ ] エラー状態を色だけでなくアイコンとテキストで伝える
- [ ] テキストコントラスト比 4.5:1 以上を確保
- [ ] すべての操作をキーボードのみで完結できる
- [ ] フォーカスインジケータを視覚的に明示する
- [ ] `<html lang="ja">` を設定する
- [ ] `aria-required`, `aria-invalid`, `aria-describedby` を適切に使用する

---

## 6. セキュリティ仕様

### 脅威モデル（OWASP Top 10 対応）

| 脅威 | OWASP分類 | リスク | 対策概要 |
|------|-----------|--------|---------|
| SQLインジェクション | A03:2021 | 高 | SQLAlchemy ORMのパラメータバインディング必須 |
| 認証情報の漏洩 | A07:2021 | 高 | bcryptハッシュ化・JWT署名検証 |
| ブルートフォース攻撃 | A07:2021 | 高 | レートリミット・アカウントロック |
| XSS | A03:2021 | 中 | トークンのhttpOnly Cookie保存 |
| JWT改ざん | A02:2021 | 高 | 署名検証の徹底・アルゴリズム固定 |
| セッションハイジャック | A07:2021 | 高 | リフレッシュトークンローテーション |
| 平文パスワード保存 | A02:2021 | 致命的 | bcrypt必須（MD5/SHA1禁止） |
| 情報漏洩（ユーザー存在確認） | A01:2021 | 中 | 統一エラーメッセージ |

### パスワード管理

| アルゴリズム | 採否 | 理由 |
|------------|------|------|
| bcrypt (rounds=12) | **採用** | GPU耐性あり、ソルト自動付与、広く実績あり |
| Argon2id | 将来移行候補 | メモリハード、より堅牢だが依存追加コスト大 |
| MD5 / SHA-1 / SHA-256 | **禁止** | レインボーテーブル・GPU攻撃に脆弱 |

**パスワードポリシー：** 8文字以上・英字1文字以上・数字1文字以上

### JWT設計

```
アクセストークン  : 有効期限 30分、HS256署名、メモリ保持
リフレッシュトークン: 有効期限 7日、DB保存（SHA-256ハッシュ化して保存）
```

**リフレッシュトークン戦略：**
1. refresh_token をハッシュ化してDBで検索
2. `is_revoked=False` かつ `expires_at > now` を確認
3. 旧トークンを `is_revoked=True` に更新（Rotation）
4. 新しい access_token + refresh_token を発行
5. 旧トークンで再利用を試みた場合 → 全セッション強制失効

### APIセキュリティ

**CORS設定：**
```python
allow_origins=["https://aisteps.com"],  # 本番では自ドメインのみ
allow_credentials=True,
allow_methods=["GET", "POST", "PUT", "DELETE"],
allow_headers=["Authorization", "Content-Type"],
```

**レートリミット（slowapi）：**
```python
@limiter.limit("10/minute")   # /api/auth/login
@limiter.limit("5/minute")    # /api/auth/register
```

### セキュリティヘッダー

```python
response.headers["X-Content-Type-Options"]    = "nosniff"
response.headers["X-Frame-Options"]           = "DENY"
response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
response.headers["Content-Security-Policy"]   = "default-src 'self'; ..."
response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
response.headers["Permissions-Policy"]        = "geolocation=(), microphone=()"
```

### ブルートフォース対策

- 5回連続失敗 → アカウント15分ロック
- ロック中はパスワード正否に関わらず429を返す
- 成功時はカウンターをリセット

### セキュアコーディングガイドライン

| ルール | 禁止例 | 推奨例 |
|--------|--------|--------|
| SQLは必ずORMで | `f"SELECT ... WHERE email='{email}'"` | `db.query(User).filter(User.email == email)` |
| SECRET_KEYは環境変数 | `SECRET_KEY = "mysecret"` | `SECRET_KEY = os.environ["JWT_SECRET_KEY"]` |
| エラーメッセージを統一 | `"パスワードが違います"` | `"メールアドレスまたはパスワードが正しくありません"` |
| ログにパスワード出力禁止 | `logger.info(f"login: {email} {password}")` | `logger.info(f"login attempt: {email}")` |
| アルゴリズム固定 | `jwt.decode(token, key)` | `jwt.decode(token, key, algorithms=["HS256"])` |

### セキュリティチェックリスト（リリース前）

**認証・認可**
- [ ] パスワードが bcrypt でハッシュ化されDBに保存されている
- [ ] JWT_SECRET_KEY が32文字以上のランダム文字列で環境変数に設定されている（`openssl rand -hex 32`）
- [ ] アクセストークンの有効期限が30分以内に設定されている
- [ ] リフレッシュトークンのローテーションが機能している
- [ ] 未認証リクエストが保護エンドポイントで401を返す

**API・通信**
- [ ] CORS の `allow_origins` が本番ドメインのみに設定されている
- [ ] HTTPSリダイレクトが有効になっている
- [ ] レートリミットが `/api/auth/*` に適用されている
- [ ] セキュリティヘッダーがレスポンスに含まれている

**データ**
- [ ] ログにパスワード・トークンが出力されていない
- [ ] エラーメッセージからユーザー存在有無が判断できない
- [ ] SQLクエリがすべてORMのパラメータバインディングを使用している

**インフラ（Railway）**
- [ ] 環境変数（JWT_SECRET_KEY, DATABASE_URL）が Railway の設定画面で管理されている
- [ ] `.env` ファイルが `.gitignore` に含まれている

### インシデント対応手順

```
1. 検知（ログ監視・ユーザー報告）
   ↓
2. 影響範囲の特定（対象ユーザー特定・アクセスログ保全）
   ↓
3. 即時対応（15分以内）
   → 該当ユーザーの refresh_tokens を全件 is_revoked=True に更新（強制ログアウト）
   ↓
4. 再発防止
   → JWT_SECRET_KEY のローテーション（全ユーザー強制ログアウト）
   → IPブロック
   ↓
5. 事後対応
   → ユーザーへの通知・パスワードリセット案内
```

**全ユーザー強制ログアウト用SQL（緊急時）：**
```sql
UPDATE refresh_tokens SET is_revoked = TRUE WHERE is_revoked = FALSE;
```
