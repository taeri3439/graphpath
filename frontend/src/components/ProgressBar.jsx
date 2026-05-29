// 로드맵 진행률 표시 바.
export default function ProgressBar({ progress }) {
  if (!progress) return null;
  const { done, total, percent } = progress;
  return (
    <div className="progress">
      <div className="progress__head">
        <span>학습 진행률</span>
        <strong>
          {done} / {total} 단계 ({percent}%)
        </strong>
      </div>
      <div className="progress__track">
        <div className="progress__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
