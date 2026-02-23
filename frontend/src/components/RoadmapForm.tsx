import { useState } from "react";

interface Props {
  onSubmit: (goal: string) => void;
  loading: boolean;
}

export default function RoadmapForm({ onSubmit, loading }: Props) {
  const [goal, setGoal] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (goal.trim()) onSubmit(goal.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="form">
      <label htmlFor="goal" className="label">
        やりたいことを入力してください
      </label>
      <textarea
        id="goal"
        className="textarea"
        rows={3}
        placeholder="例: Webエンジニアとして転職したい"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        disabled={loading}
      />
      <button type="submit" className="btn-primary" disabled={loading || !goal.trim()}>
        {loading ? "生成中..." : "ロードマップを生成"}
      </button>
    </form>
  );
}
