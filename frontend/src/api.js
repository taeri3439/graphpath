// 백엔드(FastAPI) 연동 모듈. vite proxy 를 통해 /api -> http://localhost:8000 로 전달된다.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = `요청 실패 (${res.status})`;
    try {
      const body = await res.json();
      detail = body.error || body.detail || JSON.stringify(body);
    } catch {
      // JSON 파싱 실패 시 기본 메시지 유지
    }
    throw new Error(detail);
  }

  return res.json();
}

// 이력서 텍스트로 에이전트를 시작한다. (analyzer -> planner -> interrupt)
export function startAgent(resumeText) {
  return request("/start", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

// 이력서 파일(PDF/DOCX/TXT/MD)을 업로드해 에이전트를 시작한다.
export async function startAgentFromFile(file) {
  const form = new FormData();
  form.append("file", file);
  // FormData 전송 시 Content-Type 은 브라우저가 boundary 와 함께 자동 설정한다.
  const res = await fetch(`${BASE}/start/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = `업로드 실패 (${res.status})`;
    try {
      const body = await res.json();
      detail = body.error || body.detail || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

// 사용자 피드백으로 그래프를 재개한다. ('approve' 또는 수정 요청 텍스트)
export function sendFeedback(threadId, feedback) {
  return request("/feedback", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId, feedback }),
  });
}

// 특정 단계의 완료 여부를 갱신한다. (status: "done" | "todo")
export function updateProgress(threadId, stepId, status) {
  return request("/progress", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId, step_id: stepId, status }),
  });
}

// 진행 속도/트렌드를 반영해 남은 단계를 재조정한다.
export function replan(threadId) {
  return request("/replan", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId }),
  });
}

// 현재 구조화 로드맵과 진행률을 조회한다.
export function getRoadmap(threadId) {
  return request(`/roadmap/${threadId}`);
}

// 특정 세션의 로드맵 수정 이력을 조회한다.
export function getHistory(threadId) {
  return request(`/history/${threadId}`);
}
