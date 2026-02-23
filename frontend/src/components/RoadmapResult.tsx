import type { RoadmapRecord } from "../api/roadmap";

interface Props {
  record: RoadmapRecord;
}

export default function RoadmapResult({ record }: Props) {
  const roadmap = record.final_json || record.initial_json;

  return (
    <div className="result">
      <h2 className="result-goal">目標: {roadmap?.goal}</h2>

      {record.critique && (
        <details className="critique-section">
          <summary>AIの批評を見る</summary>
          <pre className="critique-text">{record.critique}</pre>
        </details>
      )}

      <div className="steps-grid">
        {roadmap?.steps.map((step) => (
          <div key={step.order} className="step-card">
            <div className="step-header">
              <span className="step-order">STEP {step.order}</span>
              <span className="step-duration">{step.duration}</span>
            </div>
            <h3 className="step-title">{step.title}</h3>
            <p className="step-description">{step.description}</p>
            <div className="skills">
              {step.skills.map((skill) => (
                <span key={skill} className="skill-badge">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
