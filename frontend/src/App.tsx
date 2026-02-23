import { useState } from "react";
import RoadmapForm from "./components/RoadmapForm";
import ProgressSteps from "./components/ProgressSteps";
import RoadmapResult from "./components/RoadmapResult";
import type { RoadmapRecord } from "./api/roadmap";
import { generateRoadmap } from "./api/roadmap";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [result, setResult] = useState<RoadmapRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (goal: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgressStep(1);

    const timer1 = setTimeout(() => setProgressStep(2), 4000);
    const timer2 = setTimeout(() => setProgressStep(3), 10000);

    try {
      const record = await generateRoadmap(goal);
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

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">キャリアロードマップ生成ツール</h1>
        <p className="subtitle">AIがあなたのキャリア目標へのステップを設計します</p>
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
