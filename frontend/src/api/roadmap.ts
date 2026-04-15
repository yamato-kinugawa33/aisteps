/**
 * api/roadmap.ts
 *
 * ロードマップ関連のAPIクライアント関数をまとめたファイルです。
 *
 * 【変更点】
 * - 認証が必要になったため、各関数に accessToken 引数を追加しました。
 *   バックエンドが Bearer トークンを要求するようになったためです。
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────

export interface RoadmapStep {
  order: number;
  title: string;
  description: string;
  skills: string[];
  duration: string;
}

export interface RoadmapJson {
  goal: string;
  steps: RoadmapStep[];
}

export interface RoadmapRecord {
  id: number;
  user_input: string;
  initial_json: RoadmapJson | null;
  critique: string | null;
  final_text: string | null;
  final_json: RoadmapJson | null;
  created_at: string;
}

export interface RoadmapSummary {
  id: number;
  user_input: string;
  created_at: string;
}

// ─────────────────────────────────────────────
// API関数
// ─────────────────────────────────────────────

/**
 * 認証ヘッダーを生成するヘルパー関数。
 * アクセストークンが提供された場合に Authorization ヘッダーを付与します。
 *
 * @param accessToken - JWTアクセストークン
 */
function buildHeaders(accessToken: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    // "Bearer <token>" 形式でヘッダーに付与する
    Authorization: `Bearer ${accessToken}`,
  };
}

/**
 * ロードマップを生成するAPIを呼び出します。
 * 認証が必要なエンドポイントのため、アクセストークンを引数に追加しました。
 *
 * @param goal - キャリア目標のテキスト
 * @param accessToken - 有効なアクセストークン
 * @returns 生成されたロードマップデータ
 * @throws {Error} 生成失敗時やサーバーエラー時
 */
export async function generateRoadmap(
  goal: string,
  accessToken: string
): Promise<RoadmapRecord> {
  const res = await fetch(`${BASE_URL}/api/roadmaps`, {
    method: "POST",
    headers: buildHeaders(accessToken),
    body: JSON.stringify({ goal }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "生成に失敗しました");
  }
  return res.json();
}

/**
 * ロードマップ一覧を取得するAPIを呼び出します。
 *
 * @param accessToken - 有効なアクセストークン
 * @returns ロードマップのサマリー一覧
 * @throws {Error} 取得失敗時
 */
export async function listRoadmaps(
  accessToken: string
): Promise<RoadmapSummary[]> {
  const res = await fetch(`${BASE_URL}/api/roadmaps`, {
    headers: buildHeaders(accessToken),
  });
  if (!res.ok) throw new Error("取得に失敗しました");
  return res.json();
}

/**
 * 指定IDのロードマップを取得するAPIを呼び出します。
 *
 * @param id - 取得するロードマップのID
 * @param accessToken - 有効なアクセストークン
 * @returns ロードマップの詳細データ
 * @throws {Error} 取得失敗時
 */
export async function getRoadmap(
  id: number,
  accessToken: string
): Promise<RoadmapRecord> {
  const res = await fetch(`${BASE_URL}/api/roadmaps/${id}`, {
    headers: buildHeaders(accessToken),
  });
  if (!res.ok) throw new Error("取得に失敗しました");
  return res.json();
}
