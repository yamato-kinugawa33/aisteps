"""
middleware/security_headers.py

HTTPセキュリティヘッダーを全レスポンスに自動付与するミドルウェアです。

【このファイルの役割】
- ブラウザのセキュリティ機能を有効化するHTTPヘッダーを設定します。
- main.py に `app.add_middleware(SecurityHeadersMiddleware)` を追加することで適用されます。

【各ヘッダーの説明】
- Strict-Transport-Security: HTTPSを強制する（HSTS）
- X-Content-Type-Options: MIMEタイプの推測を防ぐ（XSS対策）
- X-Frame-Options: iframeへの埋め込みを禁止（クリックジャッキング対策）
- X-XSS-Protection: ブラウザのXSSフィルターを有効化
- Referrer-Policy: リファラー情報の漏洩を防ぐ
- Content-Security-Policy: スクリプト・スタイルの読み込み元を制限（XSS対策）
- Permissions-Policy: カメラ・マイクなど不要なブラウザAPIを無効化
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    全レスポンスにセキュリティヘッダーを自動で付与するミドルウェアクラス。

    BaseHTTPMiddlewareを継承することで、
    FastAPIアプリの全リクエスト・レスポンスをインターセプトできます。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        リクエストを処理してレスポンスにセキュリティヘッダーを付与します。

        Args:
            request: 受信したHTTPリクエスト
            call_next: 次のミドルウェアまたはルーターに処理を渡す関数

        Returns:
            セキュリティヘッダーが付与されたHTTPレスポンス
        """
        # まずリクエストを実際のエンドポイントで処理する
        response = await call_next(request)

        # --- セキュリティヘッダーを付与 ---

        # HTTPSを2年間強制。プリロードリストへの登録も許可
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )

        # ブラウザが Content-Type を推測するのを防ぐ（スクリプトとして実行されるリスクを防ぐ）
        response.headers["X-Content-Type-Options"] = "nosniff"

        # このサイトをiframeに埋め込むことを禁止（クリックジャッキング防止）
        response.headers["X-Frame-Options"] = "DENY"

        # 古いブラウザのXSSフィルターを有効化（最新ブラウザでは不要だが互換性のため）
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # リファラー情報: 同一オリジンへは詳細を送り、外部サイトへはオリジンのみ送る
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # コンテンツセキュリティポリシー: スクリプト・スタイルの読み込み元を制限
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # CSS-in-JSのために unsafe-inline を許可
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"  # iframe埋め込みを禁止
        )

        # 不要なブラウザAPIを無効化（プライバシー・セキュリティのため）
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # 認証関連のAPIレスポンスはキャッシュしない（トークン情報を保護）
        if "/api/auth/" in request.url.path:
            response.headers["Cache-Control"] = "no-store"

        # サーバー情報（uvicornのバージョン等）を隠蔽
        if "server" in response.headers:
            del response.headers["server"]

        return response
