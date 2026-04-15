/**
 * LoginPage.tsx
 *
 * ログイン画面のコンポーネントです。
 *
 * 【このファイルの役割】
 * - メールアドレスとパスワードを入力してログインするフォームを表示します。
 * - useAuth() フックから login 関数を取得して使用します。
 * - ログイン成功後はホーム画面（/）にリダイレクトします。
 *
 * 【認証フロー】
 *   1. ユーザーがフォームに入力して「ログイン」ボタンを押す
 *   2. useAuth().login() を呼び出す
 *   3. login() の内部で loginApi() → getMeApi() が実行される
 *   4. AuthContext の状態が更新される（ユーザー情報・アクセストークンがセットされる）
 *   5. useNavigate() でホーム画面へリダイレクト
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * ログインページコンポーネント
 *
 * React Router の <Route path="/login"> に対応します。
 */
export default function LoginPage() {
  // useNavigate: プログラム的にページ遷移するためのフック（react-router-dom）
  const navigate = useNavigate();

  // useAuth: AuthContext から認証操作（login等）を取得するカスタムフック
  const { state, login } = useAuth();

  // すでに認証済みの場合はホーム画面へリダイレクト（ログイン画面を見せない）
  if (!state.isLoading && state.user) {
    return <Navigate to="/" replace />;
  }

  // フォームの入力値を管理するstate
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // APIリクエスト中かどうかを管理するstate（ローディング中はボタンを無効化する）
  const [isLoading, setIsLoading] = useState(false);

  // エラーメッセージを管理するstate（バックエンドから返ってきたエラーを表示する）
  const [error, setError] = useState<string | null>(null);

  /**
   * フォーム送信ハンドラー。
   * バリデーション → login() 呼び出し → リダイレクトの順で処理します。
   *
   * @param e - フォームのsubmitイベント
   */
  const handleSubmit = async (e: FormEvent) => {
    // デフォルトの送信動作（ページリロード）をキャンセル
    e.preventDefault();

    // クライアント側の簡易バリデーション
    if (!email.trim() || !password.trim()) {
      setError("メールアドレスとパスワードを入力してください");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // AuthContext の login 関数を呼び出す
      // → loginApi() でトークンを取得 → getMeApi() でユーザー情報を取得
      await login(email, password);

      // ログイン成功 → ホーム画面へリダイレクト
      navigate("/");
    } catch (err) {
      // ログイン失敗時にエラーメッセージを表示
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      // 成功・失敗に関わらずローディング状態を解除
      setIsLoading(false);
    }
  };

  return (
    // auth-page: フルスクリーンの背景（App.cssで定義）
    <div className="auth-page">
      <div className="auth-card">
        {/* ブランドヘッダー */}
        <div className="auth-brand">
          <h1 className="auth-brand-name">aisteps</h1>
          <p className="auth-brand-tagline">AIがあなたのキャリアをナビゲート</p>
        </div>

        {/* ログインフォーム */}
        <h2 className="auth-title">ログイン</h2>

        {/* エラーメッセージ（エラーがある場合のみ表示） */}
        {error && (
          <div className="auth-error" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {/* メールアドレス入力 */}
          <div className="form-group">
            <label htmlFor="email">メールアドレス</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          {/* パスワード入力 */}
          <div className="form-group">
            <label htmlFor="password">パスワード</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="パスワードを入力"
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          {/* ログインボタン（ローディング中は無効化） */}
          <button
            type="submit"
            className="auth-button"
            disabled={isLoading}
          >
            {isLoading ? "ログイン中..." : "ログイン"}
          </button>
        </form>

        {/* 新規登録ページへのリンク */}
        <p className="auth-link">
          アカウントをお持ちでない方は{" "}
          <Link to="/register">こちらから登録</Link>
        </p>
      </div>
    </div>
  );
}
