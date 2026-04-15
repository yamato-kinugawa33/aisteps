/**
 * components/auth/AuthGuard.tsx
 *
 * 認証が必要なページを保護するガードコンポーネントです。
 *
 * 【このファイルの役割】
 * - 未認証ユーザーがアクセスしようとしたとき、ログインページへリダイレクトします。
 * - 認証チェック中（isLoading）はローディング表示をします。
 * - 認証済みであれば、子コンポーネント（children）をそのまま表示します。
 *
 * 【使い方】
 * 保護したいルートを <AuthGuard> で囲むだけです。
 *
 * @example
 * // App.tsx での使い方
 * <Route
 *   path="/"
 *   element={
 *     <AuthGuard>
 *       <MainPage />   ← ログイン済みのみアクセス可能
 *     </AuthGuard>
 *   }
 * />
 */

import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

/**
 * AuthGuard コンポーネントの Props 型
 */
interface AuthGuardProps {
  /** 認証済みのときに表示する子コンポーネント */
  children: ReactNode;
}

/**
 * 認証ガードコンポーネント。
 * 認証状態によって表示内容を切り替えます。
 *
 * - 認証チェック中: ローディング表示
 * - 未認証: /login へリダイレクト
 * - 認証済み: children を表示
 */
export default function AuthGuard({ children }: AuthGuardProps) {
  // useAuth: AuthContext から現在の認証状態を取得
  const { state } = useAuth();

  // アプリ起動時の認証チェック中（localStorageのトークンを検証している間）
  if (state.isLoading) {
    return (
      <div className="auth-loading">
        <p>読み込み中...</p>
      </div>
    );
  }

  // 未認証: ログインページへリダイレクト
  // <Navigate> は React Router のコンポーネントで、指定したパスへ自動遷移します
  // replace=true: ブラウザの履歴に /login を「置き換え」として記録
  //   → バックボタンを押したときに認証前のページに戻れなくする
  if (!state.user) {
    return <Navigate to="/login" replace />;
  }

  // 認証済み: 子コンポーネントをそのまま表示
  return <>{children}</>;
}
