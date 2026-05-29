// 에이전트의 현재 단계를 시각화하는 스텝 표시줄.
// phase: "input" | "loading" | "review" | "revising" | "approved"

const STEPS = [
  { key: "analyze", label: "이력서 분석" },
  { key: "plan", label: "로드맵 설계" },
  { key: "review", label: "피드백 대기" },
  { key: "approved", label: "최종 승인" },
];

function activeIndex(phase) {
  switch (phase) {
    case "input":
      return -1;
    case "loading":
      return 1; // 분석~설계 진행 중
    case "review":
      return 2;
    case "revising":
      return 2;
    case "approved":
      return 3;
    default:
      return -1;
  }
}

export default function StatusStepper({ phase }) {
  const current = activeIndex(phase);
  const busy = phase === "loading" || phase === "revising";

  return (
    <div className="stepper">
      {STEPS.map((step, idx) => {
        const done = idx < current || phase === "approved";
        const isCurrent = idx === current && phase !== "approved";
        const cls = [
          "step",
          done ? "step--done" : "",
          isCurrent ? "step--current" : "",
          isCurrent && busy ? "step--busy" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <div key={step.key} className={cls}>
            <span className="step__dot">{done ? "✓" : idx + 1}</span>
            <span className="step__label">{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}
