import { useRef, useState } from "react";
import {
  startAgent,
  startAgentFromFile,
  sendFeedback,
  updateProgress,
  replan,
  getHistory,
} from "./api";
import StatusStepper from "./components/StatusStepper.jsx";
import StepCard from "./components/StepCard.jsx";
import ProgressBar from "./components/ProgressBar.jsx";

const SAMPLE_RESUME =
  "Python, Django 2년 경력. PostgreSQL, Git 사용 가능. AWS EC2 배포 경험. " +
  "REST API 설계 및 단위 테스트 작성 경험이 있습니다.";

function computeProgress(roadmap) {
  const total = roadmap.length;
  const done = roadmap.filter((s) => s.status === "done").length;
  const percent = total ? Math.round((done / total) * 100) : 0;
  return { total, done, percent };
}

export default function App() {
  // phase: input | loading | review | active
  const [phase, setPhase] = useState("input");
  const [working, setWorking] = useState(""); // "" | "revising" | "replanning"
  const [resumeText, setResumeText] = useState(SAMPLE_RESUME);
  const [threadId, setThreadId] = useState(null);
  const [skills, setSkills] = useState([]);
  const [roadmap, setRoadmap] = useState([]);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [paceNote, setPaceNote] = useState("");
  const [history, setHistory] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);

  const approved = phase === "active";
  const progress = computeProgress(roadmap);

  function handleFileChange(e) {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    if (selected) setError("");
  }

  function clearFile() {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleStart() {
    if (!file && !resumeText.trim()) {
      setError("이력서 내용을 입력하거나 파일을 업로드해주세요.");
      return;
    }
    setError("");
    setPhase("loading");
    try {
      const data = file
        ? await startAgentFromFile(file)
        : await startAgent(resumeText);
      setThreadId(data.thread_id);
      setSkills(data.skills || []);
      setRoadmap(data.roadmap || []);
      setPhase("review");
    } catch (e) {
      setError(e.message);
      setPhase("input");
    }
  }

  async function handleApprove() {
    setError("");
    setWorking("revising");
    try {
      const data = await sendFeedback(threadId, "approve");
      if (data.roadmap) setRoadmap(data.roadmap);
      setPhase("active");
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking("");
    }
  }

  async function handleRevise() {
    if (!feedback.trim()) {
      setError("수정 요청 내용을 입력해주세요.");
      return;
    }
    setError("");
    setWorking("revising");
    try {
      const data = await sendFeedback(threadId, feedback);
      if (data.roadmap) setRoadmap(data.roadmap);
      setFeedback("");
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking("");
    }
  }

  async function handleToggle(step, status) {
    setError("");
    try {
      const data = await updateProgress(threadId, step.id, status);
      setRoadmap(data.roadmap);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleReplan() {
    setError("");
    setPaceNote("");
    setWorking("replanning");
    try {
      const data = await replan(threadId);
      setRoadmap(data.roadmap);
      const label =
        data.pace === "ahead"
          ? "예상보다 빠른 진행! 난이도를 높여 재조정했어요."
          : data.pace === "behind"
            ? "진행이 다소 느려 보강 위주로 재조정했어요."
            : "현재 속도에 맞춰 재조정했어요.";
      setPaceNote(label);
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking("");
    }
  }

  async function toggleHistory() {
    if (historyOpen) {
      setHistoryOpen(false);
      return;
    }
    try {
      const data = await getHistory(threadId);
      setHistory(data);
      setHistoryOpen(true);
    } catch (e) {
      setError(e.message);
    }
  }

  function handleReset() {
    setPhase("input");
    setWorking("");
    setThreadId(null);
    setSkills([]);
    setRoadmap([]);
    setFeedback("");
    setError("");
    setPaceNote("");
    setHistory(null);
    setHistoryOpen(false);
    clearFile();
  }

  const showRoadmap = phase === "review" || phase === "active";

  return (
    <div className="app">
      <header className="app__header">
        <h1>Career Roadmap Agent</h1>
        <p className="app__subtitle">
          주니어 개발자와 함께 성장하는 실행형 커리어 로드맵 · Human-in-the-loop
        </p>
        <StatusStepper phase={working ? "revising" : phase} />
      </header>

      <main className="app__main">
        {error && <div className="alert alert--error">{error}</div>}

        {phase === "input" && (
          <section className="card">
            <h2 className="card__title">이력서 입력</h2>
            <p className="card__hint">
              보유 기술, 경력, 프로젝트 경험을 작성하거나 이력서 파일을
              업로드하면 에이전트가 실행 가능한 학습 로드맵을 설계합니다.
            </p>
            <textarea
              className="textarea"
              rows={8}
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              disabled={!!file}
              placeholder="예) Python, Django 2년 경력. PostgreSQL, Git 사용 가능..."
            />

            <div className="divider">
              <span>또는 이력서 파일 업로드</span>
            </div>

            <div className="upload">
              <input
                ref={fileInputRef}
                type="file"
                id="resume-file"
                className="upload__input"
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileChange}
              />
              <label htmlFor="resume-file" className="upload__label">
                파일 선택
              </label>
              {file ? (
                <span className="upload__file">
                  {file.name}
                  <button
                    className="upload__clear"
                    onClick={clearFile}
                    aria-label="파일 제거"
                  >
                    ✕
                  </button>
                </span>
              ) : (
                <span className="upload__hint">
                  PDF · DOCX · TXT · MD (최대 5MB)
                </span>
              )}
            </div>

            <button className="btn btn--primary" onClick={handleStart}>
              {file ? "파일로 로드맵 생성 시작" : "로드맵 생성 시작"}
            </button>
          </section>
        )}

        {phase === "loading" && (
          <section className="card card--center">
            <div className="spinner" />
            <p>이력서를 분석하고 실행 가능한 로드맵을 설계하는 중입니다...</p>
          </section>
        )}

        {showRoadmap && (
          <>
            {skills.length > 0 && (
              <section className="card">
                <h2 className="card__title">추출된 기술 스택</h2>
                <div className="tags">
                  {skills.map((s) => (
                    <span key={s} className="tag">
                      {s}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {approved && (
              <section className="card">
                <ProgressBar progress={progress} />
                {paceNote && <p className="pace-note">{paceNote}</p>}
                <div className="btn-row">
                  <button
                    className="btn btn--primary"
                    onClick={handleReplan}
                    disabled={!!working}
                  >
                    {working === "replanning"
                      ? "재조정 중..."
                      : "진행 상황 기반 재조정"}
                  </button>
                  <button className="btn btn--ghost" onClick={toggleHistory}>
                    {historyOpen ? "이력 닫기" : "수정 이력 보기"}
                  </button>
                </div>
              </section>
            )}

            <section className="card">
              <div className="card__head">
                <h2 className="card__title">
                  {approved ? "나의 학습 로드맵" : "로드맵 초안"}
                </h2>
                {!approved && (
                  <button className="btn btn--ghost" onClick={toggleHistory}>
                    {historyOpen ? "이력 닫기" : "수정 이력 보기"}
                  </button>
                )}
              </div>

              {historyOpen && history && (
                <div className="history">
                  <p className="history__count">
                    총 변경 횟수: <strong>{history.revision_count}</strong>
                  </p>
                  {history.revision_history.length === 0 ? (
                    <p className="card__hint">아직 변경 이력이 없습니다.</p>
                  ) : (
                    history.revision_history.map((ver, i) => (
                      <details key={i} className="history__item">
                        <summary>
                          버전 {i + 1} · {ver.reason === "replan" ? "재조정" : "수정"}{" "}
                          ({(ver.steps || []).length}단계)
                        </summary>
                        <ul className="history__steps">
                          {(ver.steps || []).map((s, j) => (
                            <li key={j}>{s.title}</li>
                          ))}
                        </ul>
                      </details>
                    ))
                  )}
                </div>
              )}

              {working ? (
                <div className="card--center">
                  <div className="spinner" />
                  <p>
                    {working === "replanning"
                      ? "진행 상황과 트렌드를 반영해 재조정하는 중입니다..."
                      : "로드맵을 갱신하는 중입니다..."}
                  </p>
                </div>
              ) : (
                <div className="steps">
                  {roadmap.map((step, i) => (
                    <StepCard
                      key={step.id}
                      step={step}
                      index={i}
                      interactive={approved}
                      busy={!!working}
                      onToggle={handleToggle}
                    />
                  ))}
                </div>
              )}
            </section>

            {phase === "review" && !working && (
              <section className="card">
                <h2 className="card__title">검토</h2>
                <p className="card__hint">
                  로드맵이 만족스러우면 승인하고, 수정이 필요하면 요청 내용을
                  입력하세요. (예: "프론트엔드 심화 단계를 추가해주세요")
                </p>
                <textarea
                  className="textarea"
                  rows={3}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="수정 요청 내용을 입력하세요..."
                />
                <div className="btn-row">
                  <button className="btn btn--primary" onClick={handleRevise}>
                    수정 요청
                  </button>
                  <button className="btn btn--success" onClick={handleApprove}>
                    승인하고 시작하기
                  </button>
                </div>
              </section>
            )}

            {approved && (
              <section className="card card--center">
                <button className="btn btn--ghost" onClick={handleReset}>
                  새 로드맵 만들기
                </button>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
