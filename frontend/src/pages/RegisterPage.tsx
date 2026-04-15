/**
 * RegisterPage.tsx
 *
 * 新規ユーザー登録画面のコンポーネントです。
 *
 * 【このファイルの役割】
 * - メールアドレスとパスワードを入力して新規登録するフォームを表示します。
 * - useAuth() フックから register 関数を取得して使用します。
 * - 登録成功後は自動ログイン状態になり、ホーム画面（/）にリダイレクトします。
 *
 * 【バリデーション】
 * - メールアドレス: 簡易的な形式チェック（@ が含まれているか）
 * - パスワード: 8文字以上（バックエンドのバリデーションと同じ条件）
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

/**
 * 新規登録ページコンポーネント
 *
 * React Router の <Route path="/register"> に対応します。
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * クライアント側のバリデーションを実行します。
   * エラーがあればエラーメッセージを返し、なければ null を返します。
   */
  const validate = (): string | null => {
    if (!email.trim()) {
      return "メールアドレスを入力してください";
    }
    // 簡易メールアドレス形式チェック（@が含まれているか）
    if (!email.includes("@")) {
      return "有効なメールアドレスを入力してください";
    }
    if (password.length < 8) {
      return "パスワードは8文字以上で入力してください";
    }
    return null;
  };

  /**
   * フォーム送信ハンドラー。
   * バリデーション → register() 呼び出し → リダイレクトの順で処理します。
   */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // クライアント側バリデーション
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // AuthContext の register 関数を呼び出す
      // → registerApi() でトークンを取得 → getMeApi() でユーザー情報を取得
      // 登録後は自動でログイン状態になる
      await register(email, password);

      // 登録成功 → ホーム画面へリダイレクト
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登録に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* ブランドヘッダー */}
        <div className="auth-brand">
          <h1 className="auth-brand-name">aisteps</h1>
          <p className="auth-brand-tagline">AIがあなたのキャリアをナビゲート</p>
        </div>

        <h2 className="auth-title">新規登録</h2>

        {/* エラーメッセージ */}
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
              placeholder="8文字以上のパスワード"
              disabled={isLoading}
              autoComplete="new-password"
            />
            {/* パスワード要件のヒント */}
            <small className="form-hint">8文字以上で入力してください</small>
          </div>

          {/* 登録ボタン */}
          <button
            type="submit"
            className="auth-button"
            disabled={isLoading}
          >
            {isLoading ? "登録中..." : "アカウントを作成"}
          </button>
        </form>

        {/* ログインページへのリンク */}
        <p className="auth-link">
          既にアカウントをお持ちの方は{" "}
          <Link to="/login">こちらからログイン</Link>
        </p>
      </div>
    </div>
  );
}
