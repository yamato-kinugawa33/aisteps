interface Step {
  label: string;
  done: boolean;
  active: boolean;
}

interface Props {
  currentStep: number; // 1: 初回生成, 2: 批評, 3: 改善生成
}

export default function ProgressSteps({ currentStep }: Props) {
  const steps: Step[] = [
    { label: "ロードマップ生成中", done: currentStep > 1, active: currentStep === 1 },
    { label: "AI批評中", done: currentStep > 2, active: currentStep === 2 },
    { label: "改善版を生成中", done: currentStep > 3, active: currentStep === 3 },
  ];

  return (
    <div className="progress-steps">
      {steps.map((step, i) => (
        <div
          key={i}
          className={`progress-step ${step.done ? "done" : ""} ${step.active ? "active" : ""}`}
        >
          <div className="step-icon">
            {step.done ? "✓" : step.active ? <span className="spinner" /> : i + 1}
          </div>
          <span className="step-label">{step.label}</span>
        </div>
      ))}
    </div>
  );
}
