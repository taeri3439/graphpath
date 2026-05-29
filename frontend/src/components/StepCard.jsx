// 실행 가능한 학습 단계 카드. 체크박스로 완료 여부를 토글한다.
export default function StepCard({ step, index, interactive, busy, onToggle }) {
  const done = step.status === "done";

  return (
    <div className={`step-card ${done ? "step-card--done" : ""}`}>
      <div className="step-card__head">
        <label className="step-card__check">
          <input
            type="checkbox"
            checked={done}
            disabled={!interactive || busy}
            onChange={() => onToggle(step, done ? "todo" : "done")}
          />
          <span className="step-card__index">{index + 1}</span>
        </label>
        <div className="step-card__titlewrap">
          <h3 className="step-card__title">{step.title}</h3>
          <span className="step-card__duration">{step.duration_weeks}주</span>
        </div>
      </div>

      <p className="step-card__desc">{step.description}</p>

      {step.skills?.length > 0 && (
        <div className="tags tags--sm">
          {step.skills.map((s) => (
            <span key={s} className="tag">
              {s}
            </span>
          ))}
        </div>
      )}

      {step.resources?.length > 0 && (
        <div className="step-card__section">
          <span className="step-card__label">추천 리소스</span>
          <ul className="step-card__resources">
            {step.resources.map((r, i) => (
              <li key={i}>
                <a href={r.url} target="_blank" rel="noreferrer">
                  {r.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {step.project && (
        <div className="step-card__section">
          <span className="step-card__label">추천 프로젝트</span>
          <p className="step-card__project">{step.project}</p>
        </div>
      )}
    </div>
  );
}
