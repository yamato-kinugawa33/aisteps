# セキュリティ仕様書

**対象アプリ**: aisteps（キャリアロードマップ生成AIアプリ）  
**対象機能**: ログイン認証機能（将来実装）  
**バージョン**: 1.0  
**作成日**: 2026-04-15  
**参照基準**: OWASP Top 10 (2021)、NIST SP 800-63B

---

## 現状のセキュリティ課題

コードベース調査により、以下の現状を確認した。

| 項目 | 現状 |
|------|------|
| 認証機能 | **未実装**（全APIエンドポイントが認証なしで公開） |
| CORS | `ALLOWED_ORIGINS` 環境変数で制御済み（適切） |
| HTTPS強制 | Railway側でTLS終端（本番環境は適切） |
| レートリミット | **未実装** |
| セキュリティヘッダー | **未実装** |
| APIキー管理 | `GEMINI_API_KEY` を `.env` 管理（適切） |
| SQLインジェクション | SQLAlchemy ORM使用（パラメータバインド済み、適切） |
| 入力バリデーション | Pydantic v2 による型検証（基本的な検証のみ） |

現時点では `POST /api/roadmaps` が認証なしで誰でも呼び出せる状態であり、  
Gemini APIの無制限利用・コスト爆発・データ流出のリスクがある。

---

## 脅威モデル

### 認証機能に対する主要脅威（OWASP Top 10対応）

| ID | 脅威カテゴリ | 具体的な攻撃シナリオ | OWASP分類 | リスクレベル |
|----|-------------|---------------------|-----------|------------|
| T01 | SQLインジェクション | ログインフォームに `' OR 1=1--` を入力しDB認証をバイパス | A03:2021 | 高 |
| T02 | ブルートフォース攻撃 | ユーザーのパスワードを総当たりで試行 | A07:2021 | 高 |
| T03 | クレデンシャルスタッフィング | 漏洩済みID/PW組み合わせリストを使った自動ログイン試行 | A07:2021 | 高 |
| T04 | JWTの改ざん・漏洩 | `alg:none` 攻撃、署名検証スキップ、トークン窃取 | A07:2021 | 高 |
| T05 | XSS（クロスサイトスクリプティング） | LocalStorageのJWTを窃取するスクリプト注入 | A03:2021 | 高 |
| T06 | CSRF（クロスサイトリクエストフォージェリ） | 認証済みユーザーを騙した悪意あるリクエスト発行 | A01:2021 | 中 |
| T07 | セッション固定攻撃 | ログイン前後でセッションIDを維持させる攻撃 | A07:2021 | 中 |
| T08 | 権限昇格 | 一般ユーザーが管理者APIを呼び出す | A01:2021 | 高 |
| T09 | APIキー漏洩 | `GEMINI_API_KEY` / `DATABASE_URL` のGit誤コミット | A02:2021 | 高 |
| T10 | Gemini API乱用 | 認証なしで大量ロードマップ生成リクエストを送信しコスト爆発 | A05:2021 | 高 |
| T11 | 不適切なエラー開示 | スタックトレースや内部情報をレスポンスに含める | A05:2021 | 中 |
| T12 | ログインへのタイミング攻撃 | 存在するユーザーとしないユーザーでレスポンス時間が異なる | A07:2021 | 低 |

### 現状コードで確認された具体的なリスク

```python
# routers/roadmap.py: L24 - エラー詳細をそのまま返している（T11）
raise HTTPException(status_code=500, detail=f"AI生成エラー: {str(e)}")
# 本番では内部エラー情報を隠蔽すること

# schemas/roadmap.py: L7 - goalフィールドに長さ制限なし（T10）
class RoadmapRequest(BaseModel):
    goal: str  # max_length未設定のためGemini APIへの大量入力が可能
```

---

## パスワード管理

### ハッシュアルゴリズム選択

**選択: `bcrypt`（`passlib[bcrypt]`）**

```
pip install passlib[bcrypt]
```

| アルゴリズム | 推奨度 | 理由 |
|------------|--------|------|
| **bcrypt** | **採用** | コストファクター調整可能、広く実績あり、Python生態系での標準 |
| Argon2id | 代替案 | メモリハード関数でGPU攻撃に最強。将来移行を検討 |
| scrypt | 代替案 | Argon2と同等だがAPIが複雑 |
| PBKDF2-SHA256 | 非推奨 | GPU攻撃に脆弱。FIPSコンプライアンス要件がある場合のみ |
| MD5 / SHA-1 | **禁止** | リバーサルが容易、使用禁止 |

### 実装仕様

```python
from passlib.context import CryptContext

# コストファクター12（ログイン1回あたり約0.3秒、ブルートフォース耐性と利便性のバランス）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### ソルト

- bcryptは内部的に**ランダム128bitソルト**を自動生成・ハッシュ値に埋め込む
- 開発者がソルトを別途管理する必要はない
- レインボーテーブル攻撃を無効化

### パスワードポリシー

| 要件 | 値 |
|------|-----|
| 最小文字数 | 12文字 |
| 最大文字数 | 128文字（bcryptの72バイト制限に注意） |
| 文字種要件 | 大文字・小文字・数字・記号のうち3種以上 |
| 一般的なパスワードの禁止 | HaveIBeenPwned API or ローカルNGリストでチェック |
| パスワード再利用禁止 | 直近5世代 |

```python
# schemas/auth.py での実装例
from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("パスワードは12文字以上必要です")
        if len(v) > 128:
            raise ValueError("パスワードは128文字以内にしてください")
        return v
```

---

## JWT設計

### アルゴリズム選択

**選択: `RS256`（RSA + SHA-256）**

| アルゴリズム | 用途 | 推奨度 |
|------------|------|--------|
| **RS256** | **採用**（非対称鍵）| 署名鍵と検証鍵を分離できる。マイクロサービス化時にも適切 |
| HS256 | 対称鍵（HMAC） | 単一サービスなら可。鍵漏洩で全トークン偽造可能なため非推奨 |
| `alg: none` | **絶対禁止** | 署名検証をスキップする攻撃に悪用される |

**最小実装での妥協案**: 将来のマイクロサービス化予定がなければ `HS256` + 十分な長さの秘密鍵（最低256bit）も許容。

### 有効期限設計

```python
# config.py
ACCESS_TOKEN_EXPIRE_MINUTES = 30      # アクセストークン: 30分
REFRESH_TOKEN_EXPIRE_DAYS = 7         # リフレッシュトークン: 7日
REFRESH_TOKEN_ABSOLUTE_EXPIRE_DAYS = 30  # リフレッシュトークン絶対期限: 30日
```

| トークン種別 | 有効期限 | 保存場所 | 理由 |
|------------|---------|---------|------|
| アクセストークン | 30分 | メモリ（Reactステート）| 短命でXSS被害を最小化 |
| リフレッシュトークン | 7日（最長30日） | HttpOnly Cookie | XSSからの窃取を防止 |

### リフレッシュトークン戦略

**ローテーション方式（Refresh Token Rotation）を採用する**

```
1. リフレッシュトークンを使用してアクセストークンを更新
2. 古いリフレッシュトークンを無効化
3. 新しいリフレッシュトークンを発行
4. 再使用（リプレイ攻撃）を検知したら全セッションを強制失効
```

```python
# services/auth.py での実装イメージ
import secrets
from datetime import datetime, timedelta, timezone

def create_refresh_token() -> str:
    # JWTではなくランダム不透明トークンを推奨（失効管理をDBで行うため）
    return secrets.token_urlsafe(32)

def rotate_refresh_token(old_token: str, db: Session) -> tuple[str, str]:
    record = db.query(RefreshToken).filter_by(token=old_token).first()
    if not record or record.revoked:
        # リプレイ攻撃の可能性 → そのユーザーの全トークンを失効
        revoke_all_tokens_for_user(record.user_id, db)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    record.revoked = True
    new_token = create_refresh_token()
    # 新トークンをDBに保存
    ...
    return new_access_token, new_token
```

### 失効管理

| シナリオ | 対応 |
|---------|------|
| ユーザーのログアウト | リフレッシュトークンをDBで `revoked=True` に更新 |
| パスワード変更 | そのユーザーの全リフレッシュトークンを失効 |
| 不正アクセス検知 | 該当ユーザーの全セッションを強制失効 |
| アクセストークンの即時失効 | JWTは基本的にステートレスなため30分の期限切れを待つ（必要なら短縮） |

### JWTペイロード設計

```python
# アクセストークンのペイロード（最小限に抑える）
{
    "sub": "user_id_string",   # ユーザーID（メールアドレスは含めない）
    "iat": 1713123456,          # 発行時刻
    "exp": 1713125256,          # 有効期限
    "jti": "unique-token-id"    # JWT ID（オプション）
}
# NOTE: パスワードハッシュ、メール、個人情報はペイロードに含めない
```

---

## API セキュリティ

### レートリミット

**`slowapi`（`limits`ベース）を使用**

```python
# main.py への追加
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

| エンドポイント | 制限値 | 理由 |
|-------------|-------|------|
| `POST /api/auth/login` | 5回/分/IP | ブルートフォース対策 |
| `POST /api/auth/register` | 3回/時/IP | アカウント大量作成対策 |
| `POST /api/roadmaps` | 10回/時/ユーザー | Gemini APIコスト制御 |
| `POST /api/auth/refresh` | 20回/時/IP | リフレッシュ乱用対策 |

```python
# routers/auth.py での使用例
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

### CORS設定（現状の改善）

現状の `allow_methods=["*"]` を絞り込む。

```python
# main.py（推奨設定）
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # 環境変数で本番ドメインのみ指定（現状維持）
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # "*" から必要なメソッドのみに限定
    allow_headers=["Authorization", "Content-Type"],  # "*" から限定
)
```

**本番環境の `ALLOWED_ORIGINS` 設定例:**
```
ALLOWED_ORIGINS=https://aisteps.up.railway.app
```
ワイルドカード（`*`）の使用は禁止。

### HTTPS強制

- Railway環境では自動的にTLS終端される（適切）
- `--reload` フラグは**本番では削除必須**（現状の `dockerfile` で使用中）

```dockerfile
# dockerfile の修正
# 現状（開発用）
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 本番用（--reload を削除）
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## セキュリティヘッダー

`starlette-security-headers` または手動ミドルウェアで実装。

```python
# middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://aisteps.up.railway.app; "
            "frame-ancestors 'none';"
        )
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # NOTE: Server ヘッダーを削除（uvicornがデフォルトで送出する情報を隠蔽）
        response.headers.pop("server", None)
        return response

# main.py に追加
app.add_middleware(SecurityHeadersMiddleware)
```

### 実装すべきHTTPセキュリティヘッダー一覧

| ヘッダー | 設定値 | 目的 |
|---------|-------|------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | HTTPS強制（HSTS） |
| `X-Content-Type-Options` | `nosniff` | MIMEスニッフィング防止 |
| `X-Frame-Options` | `DENY` | クリックジャッキング防止 |
| `X-XSS-Protection` | `1; mode=block` | 旧ブラウザのXSSフィルター有効化 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | リファラー情報漏洩防止 |
| `Content-Security-Policy` | 上記参照 | XSS・インジェクション全般の緩和 |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | 不要なブラウザAPIへのアクセス禁止 |
| `Cache-Control`（API） | `no-store` | 認証レスポンスのキャッシュ禁止 |

---

## ブルートフォース対策

### アカウントロック戦略

**推奨: タイムベースのプログレッシブ遅延（アカウントロックアウトより優先）**

アカウントロックアウトはDoS（サービス拒否）攻撃に悪用される恐れがあるため、  
完全ロックではなくプログレッシブ遅延を基本とする。

```python
# services/auth.py
LOGIN_ATTEMPT_LIMITS = {
    3: 30,    # 3回失敗: 30秒待機
    5: 300,   # 5回失敗: 5分待機
    10: 3600, # 10回失敗: 1時間待機
}

# Redisで失敗回数を管理（またはDBのlogin_attemptsテーブル）
async def check_login_attempts(user_id: str, redis_client) -> None:
    key = f"login_fail:{user_id}"
    attempts = int(await redis_client.get(key) or 0)
    for threshold, delay in sorted(LOGIN_ATTEMPT_LIMITS.items()):
        if attempts >= threshold:
            wait = delay
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"ログイン試行回数が多すぎます。{wait}秒後に再試行してください"
        )
```

### CAPTCHA

| トリガー条件 | 対応 |
|------------|------|
| 同一IPからの3回連続失敗 | reCAPTCHA v3 を表示 |
| 異なるIPからの同一アカウントへの5回失敗 | reCAPTCHA v2（チェックボックス）に格上げ |
| 大量アカウント登録（同一IP） | 登録フォームにCAPTCHA必須 |

**実装**: Google reCAPTCHA v3 または hCaptcha（プライバシー重視）を推奨。

### IP制限

```python
# Railwayの場合: リバースプロキシ経由でX-Forwarded-Forヘッダーを使用
from fastapi import Request

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host

# ログイン失敗時のIPブロック（Redisで管理）
IP_BLOCK_THRESHOLD = 20  # 同一IPから20回失敗でブロック
IP_BLOCK_DURATION = 86400  # 24時間ブロック
```

---

## セキュアコーディングガイドライン

### FastAPI実装における注意事項

#### 1. 依存性注入による認証ガード

```python
# dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError
    except (jwt.JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが存在しません")
    return user

# routers/roadmap.py への適用
@router.post("", response_model=RoadmapResponse)
def create_roadmap(
    req: RoadmapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # 認証必須
):
    ...
```

#### 2. 入力バリデーションの強化（現状コードの改善）

```python
# schemas/roadmap.py の改善
from pydantic import BaseModel, Field

class RoadmapRequest(BaseModel):
    goal: str = Field(
        min_length=10,
        max_length=500,  # Gemini APIへの過大入力を防止
        description="キャリア目標（10〜500文字）"
    )
```

#### 3. エラーレスポンスの正規化（現状コードの改善）

```python
# routers/roadmap.py の改善
import logging
logger = logging.getLogger(__name__)

@router.post("", response_model=RoadmapResponse)
def create_roadmap(req: RoadmapRequest, db: Session = Depends(get_db)):
    try:
        ...
    except Exception as e:
        logger.error("AI pipeline error: %s", e, exc_info=True)  # サーバーログに詳細を記録
        raise HTTPException(status_code=500, detail="ロードマップ生成中にエラーが発生しました")
        # 内部エラー情報（str(e)）をレスポンスに含めない
```

#### 4. タイミング攻撃への対策

```python
# services/auth.py
import hmac

def verify_password_timing_safe(plain: str, hashed: str) -> bool:
    # passlib は内部的に定数時間比較を使用しているが、
    # ユーザー存在確認とパスワード検証を分けないことも重要
    result = pwd_context.verify(plain, hashed)
    return result

async def authenticate_user(email: str, password: str, db: Session):
    user = db.query(User).filter_by(email=email).first()
    # ユーザーが存在しない場合もダミーハッシュで検証（タイミング攻撃対策）
    dummy_hash = "$2b$12$dummyhashfortimingreasons......"
    if not user:
        pwd_context.verify(password, dummy_hash)  # 時間を消費
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが違います")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが違います")
    return user
```

#### 5. 環境変数・シークレット管理

```
# .env（ローカル開発のみ）
# 絶対に Git にコミットしない

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/roadmap_db
GEMINI_API_KEY=your_key_here
JWT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...
SECRET_KEY=32文字以上のランダム文字列
ALLOWED_ORIGINS=http://localhost:5173
```

```bash
# .gitignore に必ず追加
backend/.env
*.pem
*.key
```

---

## セキュリティチェックリスト

### リリース前確認項目

#### 認証・認可
- [ ] 全APIエンドポイントに認証ガードが実装されている
- [ ] `/health` エンドポイントはパブリックアクセス可（現状適切）
- [ ] ロールベースアクセス制御（RBAC）が必要な場合に実装されている
- [ ] JWT の `alg` フィールドが `none` を受け付けない実装になっている
- [ ] リフレッシュトークンのローテーションが実装されている

#### パスワード管理
- [ ] パスワードを平文でDBに保存していない
- [ ] bcrypt のコストファクターが12以上に設定されている
- [ ] パスワードポリシー（12文字以上）がフロント・バック両方で検証されている
- [ ] パスワードリセットトークンが使い捨て（1回使用後に失効）になっている

#### 入力検証・出力エスケープ
- [ ] 全Pydanticスキーマに `max_length` が設定されている（T10対策）
- [ ] `goal` フィールドに500文字制限が設定されている
- [ ] エラーレスポンスに内部情報（スタックトレース等）が含まれていない
- [ ] SQLはすべてORMパラメータバインドで実行している（生SQLなし）

#### ネットワーク・インフラ
- [ ] `ALLOWED_ORIGINS` に本番ドメインのみが設定されている
- [ ] `allow_methods` が必要なHTTPメソッドのみに限定されている
- [ ] セキュリティヘッダーミドルウェアが有効になっている
- [ ] `--reload` フラグが本番dockerfileから削除されている
- [ ] レートリミットが全認証エンドポイントに設定されている

#### シークレット管理
- [ ] `.env` ファイルが `.gitignore` に含まれている
- [ ] `git log` でシークレットが過去コミットに含まれていないか確認した
- [ ] `DATABASE_URL` に本番用の強いパスワードが設定されている
- [ ] docker-compose.yml の `POSTGRES_PASSWORD: postgres` が変更されている

#### 依存関係
- [ ] `uv lock` で依存関係がロックされている（現状適切）
- [ ] `pip audit` または `safety check` で既知脆弱性がないか確認した
- [ ] Dockerベースイメージ（`python:3.12-slim`）が最新パッチ適用済みである

#### フロントエンド
- [ ] JWTアクセストークンをLocalStorageではなくメモリ（Reactステート）に保存している
- [ ] リフレッシュトークンが HttpOnly Cookie で送受信されている
- [ ] `Content-Security-Policy` ヘッダーが設定されている

---

## インシデント対応

### 不正アクセス検知時の対応手順

#### 検知トリガー（自動アラート対象）

| 検知条件 | アラートレベル |
|---------|-------------|
| 同一IPからのログイン失敗が5分間で10回超 | WARNING |
| 同一アカウントへのログイン失敗が1時間で20回超 | CRITICAL |
| 異常な時間帯（深夜）からの大量リクエスト | WARNING |
| リフレッシュトークンの再使用（リプレイ攻撃） | CRITICAL |
| Gemini APIコストが1日の上限を超過 | CRITICAL |
| DBから大量データの読み取り（全件取得の異常な頻度） | WARNING |

#### 対応フロー

```
[検知]
  ↓
[Step 1: 初動確認（15分以内）]
  - Railwayのアクセスログ・アプリケーションログを確認
  - 攻撃元IPアドレスと攻撃パターンを特定
  - 影響を受けたユーザーアカウントの特定

[Step 2: 封じ込め（30分以内）]
  - 攻撃元IPをアプリケーションレベルでブロック
  - 影響を受けたユーザーの全セッションを強制失効
    → DBの refresh_tokens テーブルを全件 revoked=True に更新
  - 必要に応じてRailwayでサービスを一時停止

[Step 3: 被害調査（2時間以内）]
  - 不正にアクセスされたデータの範囲を特定
  - DBの audit_log（要実装）で操作履歴を確認
  - Gemini APIの使用量を確認（不正生成の有無）

[Step 4: 復旧]
  - 漏洩したシークレット（GEMINI_API_KEY等）をRailwayで即座にローテーション
  - パスワードハッシュ漏洩の可能性があれば、影響ユーザー全員にパスワードリセットを強制
  - JWTの秘密鍵が漏洩した場合は新鍵ペアを生成し全ユーザーを再ログイン要求

[Step 5: 通知・報告]
  - 影響ユーザーへのメール通知（個人情報漏洩の有無を明記）
  - 再発防止策の策定と実装スケジュール作成
```

#### 緊急時のセッション全失効コマンド

```sql
-- 緊急時: 全リフレッシュトークンを即座に失効
UPDATE refresh_tokens SET revoked = TRUE WHERE revoked = FALSE;

-- 特定ユーザーのみ失効
UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = '<target_user_id>';
```

#### ログ収集方針

```python
# セキュリティ関連ログは必ず構造化して記録
import logging
import json
from datetime import datetime, timezone

security_logger = logging.getLogger("security")

def log_login_attempt(
    ip: str, email: str, success: bool, reason: str = ""
):
    security_logger.info(json.dumps({
        "event": "login_attempt",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "email_hash": hashlib.sha256(email.encode()).hexdigest()[:8],  # 個人情報は部分マスク
        "success": success,
        "reason": reason,
    }))
```

---

## 参考資料

- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [NIST SP 800-63B Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [passlib Documentation](https://passlib.readthedocs.io/)
