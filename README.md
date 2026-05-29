# Career Roadmap Agent

주니어 개발자를 위한 **지능형 커리어 로드맵 생성 에이전트**입니다.
LangGraph의 Human-in-the-loop 패턴과 FastAPI를 결합하여, 이력서 분석 → 로드맵 생성 → 사용자 피드백 반영 사이클을 제공합니다.

## 아키텍처

```
analyzer → planner → human_review ──(approve)──→ END
                          ↑                │
                          └── reviser ←────┘ (수정 요청)
```

| 노드 | 역할 |
|------|------|
| `analyzer` | 이력서에서 현재 기술 스택 추출 |
| `planner` | 부족한 기술 분석 및 학습 로드맵 초안 생성 |
| `human_review` | 사용자 피드백 대기 (`interrupt`) |
| `reviser` | 피드백 반영하여 로드맵 수정 |

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 실제 OpenAI API Key를 입력하세요
```

### 3. 서버 실행

# 가상환경 실행
source .venv/bin/activate

```bash
uvicorn app.main:app --reload
```

## API 사용법

### POST /start — 에이전트 시작

```bash
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Python, Django 2년 경력. PostgreSQL, Git 사용 가능. AWS EC2 배포 경험."}'
```

**응답 예시:**
```json
{
  "thread_id": "a1b2c3d4...",
  "roadmap_draft": "## 6개월 학습 로드맵\n...",
  "message": "로드맵을 검토해주세요. 승인하려면 'approve'를, 수정이 필요하면 수정 요청 내용을 입력해주세요."
}
```

### POST /feedback — 피드백 전송

**승인:**
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "a1b2c3d4...", "feedback": "approve"}'
```

**수정 요청:**
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "a1b2c3d4...", "feedback": "프론트엔드 관련 내용을 더 추가해주세요. React보다 Vue.js를 선호합니다."}'
```



