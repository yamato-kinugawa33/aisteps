const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export async function generateRoadmap(goal: string): Promise<RoadmapRecord> {
  const res = await fetch(`${BASE_URL}/api/roadmaps`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "生成に失敗しました");
  }
  return res.json();
}

export async function listRoadmaps(): Promise<RoadmapSummary[]> {
  const res = await fetch(`${BASE_URL}/api/roadmaps`);
  if (!res.ok) throw new Error("取得に失敗しました");
  return res.json();
}

export async function getRoadmap(id: number): Promise<RoadmapRecord> {
  const res = await fetch(`${BASE_URL}/api/roadmaps/${id}`);
  if (!res.ok) throw new Error("取得に失敗しました");
  return res.json();
}
