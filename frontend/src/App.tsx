/**
 * App.tsx
 *
 * アプリケーションのルートコンポーネントです。
 *
 * 【変更内容】
 * - React Router を使ったページ遷移（ルーティング）を追加しました。
 * - AuthProvider で全体をラップし、認証状態をグローバルに管理します。
 * - AuthGuard で保護されたルート（/）は認証済みユーザーのみアクセス可能です。
 *
 * 【ルート構造】
 *   /          → ホーム画面（認証必須、AuthGuardで保護）
 *   /login     → ログイン画面
 *   /register  → 新規登録画面
 *   *          → ホーム画面へリダイレクト（存在しないパスの処理）
 */

import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/AuthContext";
import AuthGuard from "./components/auth/AuthGuard";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import RoadmapForm from "./components/RoadmapForm";
import ProgressSteps from "./components/ProgressSteps";
import RoadmapResult from "./components/RoadmapResult";
import type { RoadmapRecord } from "./api/roadmap";
import { generateRoadmap } from "./api/roadmap";
import "./App.css";

/**
 * ホーム画面コンポーネント。
 * ロードマップの生成・表示を担当します。
 * AuthGuard によって保護されており、ログイン済みユーザーのみアクセスできます。
 */
function HomePage() {
  // useAuth: 認証状態（ユーザー情報・アクセストークン）と logout 関数を取得
  const { state, logout } = useAuth();

  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [result, setResult] = useState<RoadmapRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * ロードマップ生成を実行するハンドラー。
   * アクセストークンを付与してAPIを呼び出します。
   *
   * @param goal - ユーザーが入力したキャリア目標
   */
  const handleSubmit = async (goal: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgressStep(1);

    const timer1 = setTimeout(() => setProgressStep(2), 4000);
    const timer2 = setTimeout(() => setProgressStep(3), 10000);

    try {
      // アクセストークンが必要なAPIを呼び出す
      // state.accessToken がnullのケースは AuthGuard が事前に防いでいるため、
      // ここでは非nullアサーション(!)を使用
      const record = await generateRoadmap(goal, state.accessToken!);
      setResult(record);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      setLoading(false);
      setProgressStep(0);
    }
  };

  /**
   * ログアウトボタンのクリックハンドラー。
   * バックエンドのトークンを無効化してからクライアント側もクリアします。
   */
  const handleLogout = async () => {
    await logout();
    // ログアウト後はAuthGuardが/loginへリダイレクトしてくれるため、ここでは不要
  };

  return (
    <div className="container">
      {/* ヘッダー: タイトルとログアウトボタン */}
      <header className="header">
        <div className="header-content">
          <div>
            <h1 className="title">キャリアロードマップ生成ツール</h1>
            <p className="subtitle">AIがあなたのキャリア目標へのステップを設計します</p>
          </div>
          {/* ログイン済みユーザー情報とログアウトボタン */}
          <div className="header-user">
            <span className="header-email">{state.user?.email}</span>
            <button
              className="logout-button"
              onClick={handleLogout}
              title="ログアウト"
            >
              ログアウト
            </button>
          </div>
        </div>
      </header>

      <main className="main">
        <RoadmapForm onSubmit={handleSubmit} loading={loading} />

        {loading && <ProgressSteps currentStep={progressStep} />}

        {error && (
          <div className="error-box">
            <strong>エラー:</strong> {error}
          </div>
        )}

        {result && <RoadmapResult record={result} />}
      </main>
    </div>
  );
}

/**
 * アプリケーションのルートコンポーネント。
 * ルーティングと認証状態の提供を担当します。
 */
export default function App() {
  return (
    // BrowserRouter: React Router のルーティング機能を提供するコンテキスト
    <BrowserRouter>
      {/*
        AuthProvider: 認証状態（ユーザー情報・アクセストークン）を
        アプリ全体で共有するためのコンテキストプロバイダー
      */}
      <AuthProvider>
        <Routes>
          {/* ログインページ（認証不要） */}
          <Route path="/login" element={<LoginPage />} />

          {/* 新規登録ページ（認証不要） */}
          <Route path="/register" element={<RegisterPage />} />

          {/* ホームページ（認証必須: AuthGuardで保護） */}
          <Route
            path="/"
            element={
              <AuthGuard>
                <HomePage />
              </AuthGuard>
            }
          />

          {/* 未定義のパスはホームへリダイレクト */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
