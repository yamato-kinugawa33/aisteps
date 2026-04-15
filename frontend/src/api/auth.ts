/**
 * auth.ts
 *
 * 認証関連のAPIクライアント関数をまとめたファイルです。
 * バックエンドの /api/auth/* エンドポイントへのHTTPリクエストを担当します。
 *
 * 各関数はエラー時にバックエンドのエラーメッセージ（detail フィールド）を
 * Errorとしてthrowします。呼び出し元でtry/catchして処理してください。
 *
 * 【credentials: 'include' について】
 * リフレッシュトークンはバックエンドから HttpOnly Cookie で発行されます。
 * Cookie を自動的に送受信するために、全リクエストに credentials: 'include' を設定します。
 * これにより：
 *   - ブラウザが Set-Cookie を受け取って自動保存する
 *   - 次のリクエスト時にブラウザが自動でCookieを付与する
 *   - JavaScriptからCookieの値は読めないのでXSS攻撃でも漏れない
 */

// バックエンドのベースURL（環境変数 VITE_API_URL が未設定の場合はlocalhost:8000を使用）
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────

/**
 * ログイン・登録・トークンリフレッシュ時のレスポンス型
 * リフレッシュトークンは HttpOnly Cookie で管理するためボディには含まれません。
 */
export interface TokenResponse {
  /** APIアクセスに使う短命なトークン（メモリのみで管理・localStorageには保存しない） */
  access_token: string;
  /** トークンの種類（通常は "bearer"） */
  token_type: string;
}

/**
 * ログイン中のユーザー情報の型（GET /api/auth/me のレスポンス）
 */
export interface MeResponse {
  /** ユーザーのID */
  id: number;
  /** ユーザーのメールアドレス */
  email: string;
  /** アカウントが有効かどうか */
  is_active: boolean;
  /** アカウントの作成日時（ISO 8601形式の文字列） */
  created_at: string;
}

// ─────────────────────────────────────────────
// ヘルパー関数
// ─────────────────────────────────────────────

/**
 * レスポンスがエラーの場合、バックエンドのエラーメッセージをErrorとしてthrowします。
 *
 * @param res - fetchのレスポンスオブジェクト
 * @param fallbackMessage - バックエンドからdetailが取得できなかった場合のデフォルトメッセージ
 * @throws {Error} バックエンドのdetailメッセージ、またはfallbackMessage
 */
async function throwIfError(res: Response, fallbackMessage: string): Promise<void> {
  if (!res.ok) {
    // レスポンスボディをJSONとして読み込み、detailフィールドを取り出す
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || fallbackMessage);
  }
}

// ─────────────────────────────────────────────
// 認証API関数
// ─────────────────────────────────────────────

/**
 * ログインAPIを呼び出します。
 * 成功するとアクセストークンをレスポンスで、リフレッシュトークンをHttpOnly Cookieで受け取ります。
 *
 * @param email - ユーザーのメールアドレス
 * @param password - パスワード
 * @returns トークン情報（access_token, token_type）
 * @throws {Error} 認証失敗時やサーバーエラー時
 *
 * @example
 * const tokens = await loginApi("user@example.com", "password123");
 * console.log(tokens.access_token);
 */
export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // credentials: 'include' でブラウザが Set-Cookie を受け取り自動保存する
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  await throwIfError(res, "ログインに失敗しました");
  return res.json();
}

/**
 * 新規ユーザー登録APIを呼び出します。
 * 成功するとアクセストークンをレスポンスで、リフレッシュトークンをHttpOnly Cookieで受け取ります。
 *
 * @param email - 登録するメールアドレス
 * @param password - 設定するパスワード
 * @returns トークン情報（access_token, token_type）
 * @throws {Error} メールアドレス重複時やサーバーエラー時
 *
 * @example
 * const tokens = await registerApi("newuser@example.com", "password123");
 */
export async function registerApi(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  await throwIfError(res, "登録に失敗しました");
  return res.json();
}

/**
 * ログアウトAPIを呼び出します。
 * バックエンド側でリフレッシュトークンをDB失効させ、Cookie を削除します。
 *
 * @param accessToken - 現在のアクセストークン（認証ヘッダーに使用）
 * @throws {Error} サーバーエラー時
 *
 * @example
 * await logoutApi(state.accessToken);
 */
export async function logoutApi(accessToken: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Bearerトークン認証ヘッダーを付与
      Authorization: `Bearer ${accessToken}`,
    },
    // ブラウザがリフレッシュトークンのCookieを自動送信する
    credentials: "include",
  });
  await throwIfError(res, "ログアウトに失敗しました");
}

/**
 * Cookieのリフレッシュトークンでアクセストークンをリフレッシュします。
 * リフレッシュトークンはCookieに入っているためパラメーターは不要です。
 * ブラウザが自動的にCookieを送信します。
 *
 * @returns 新しいトークン情報（access_token, token_type）
 * @throws {Error} リフレッシュトークンが無効・期限切れの場合
 *
 * @example
 * const newTokens = await refreshTokenApi();
 */
export async function refreshTokenApi(): Promise<TokenResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // ブラウザがリフレッシュトークンのCookieを自動送信する
    credentials: "include",
  });
  await throwIfError(res, "トークンの更新に失敗しました");
  return res.json();
}

/**
 * 現在ログイン中のユーザー情報を取得します。
 *
 * @param accessToken - 有効なアクセストークン
 * @returns ユーザー情報（id, email, is_active, created_at）
 * @throws {Error} トークンが無効な場合やサーバーエラー時
 *
 * @example
 * const me = await getMeApi(state.accessToken);
 * console.log(me.email);
 */
export async function getMeApi(accessToken: string): Promise<MeResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/me`, {
    method: "GET",
    headers: {
      // Bearerトークン認証ヘッダーを付与
      Authorization: `Bearer ${accessToken}`,
    },
    credentials: "include",
  });
  await throwIfError(res, "ユーザー情報の取得に失敗しました");
  return res.json();
}
