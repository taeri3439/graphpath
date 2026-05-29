# 프로젝트: 주니어 개발자 맞춤형 지능형 커리어 로드맵 생성 에이전트

> **LangGraph의 Human-in-the-loop 구조**를 활용하여, 주니어 개발자의 현재 역량을 분석하고 시장 트렌드에 맞는 맞춤형 학습 로드맵을 사용자와 협업해 설계하는 AI 에이전트.

---

## 1. 프로젝트 개요

### 문제 정의
- 기존 채용 플랫폼: 단순 공고 나열에 그침
- 일반 LLM: 구체적 실행 계획 제시 불가
- 주니어 개발자는 자신의 기술 격차 파악 및 학습 우선순위 설정에 어려움

### 해결 방안
- **LangGraph의 Stateful 그래프** + **사용자 피드백 루프** 결합
- 멀티 에이전트가 협업해 이력서 분석 → 시장 트렌드 수집 → 로드맵 설계
- 사용자가 중간 단계에서 개입(HITL)하여 AI 결정을 검토·수정

### 기대 효과
- 객관적 데이터 기반 성장 가이드라인 제공
- HITL 구조로 AI 할루시네이션 방지 및 사용자 수용성 향상
- 상태 기반 에이전트 아키텍처 설계 역량 강화

---

## 2. 기술 스택

| 영역 | 사용 기술 |
|------|-----------|
| Language | Python 3.10+ |
| Backend Framework | FastAPI (비동기) |
| Orchestration | LangGraph, LangChain |
| LLM | OpenAI GPT-4o |
| Observability | LangSmith (추론 추적·최적화) |
| Persistence | SQLite (`checkpoints.db`) |
| Frontend | React, CSS |
| Tools | Cursor AI, Poetry, Git |

---

## 3. 핵심 기능

### 3-1. 멀티 에이전트 오케스트레이션
LangGraph DAG 기반 협업 구조:
- **Analyzer 노드**: 이력서 분석 → 현재 기술 스택 추출
- **Market-Watcher 노드**: 실시간 채용 트렌드 수집
- **Planner 노드**: 로드맵 초안 생성
- **Reviser 노드**: 사용자 피드백 반영 → 로드맵 수정

### 3-2. Human-in-the-loop (HITL)
- `LangGraph interrupt` 기능으로 Planner가 초안 생성 후 **중간 승인 대기**
- 사용자가 선호 기술, 가용 시간 등 반영하여 계획 수정 가능
- 'Check-and-Balance' 시스템

### 3-3. 기술 격차(Skill Gap) 시각화
- 사용자 현재 스택 vs 목표 직무 요구 스택 정량 비교
- 학습의 당위성 제공

### 3-4. 상태 기반 반복 수정 (Iterative Refinement)
- `LangGraph Checkpointer` 활용 → 이전 상태 유지
- 사용자가 특정 단계 거부 시 유연한 재구성
- 향후 **Time-travel 기능**(로드맵 버전 비교·롤백)의 기반

---

## 4. 백엔드 아키텍처

### 4-1. 핵심 설계 원칙
- **Stateful Thread 관리**: `uuid` 기반 `thread_id`로 사용자별 독립 세션
- **체크포인트 영속화**: `AsyncSqliteSaver` 사용 → 서버 재시작에도 세션 유지 (기존 `MemorySaver` 휘발성 한계 해결)
- **비동기 일관성**: `ainvoke` / `aget_state` 패턴으로 LLM 대기 중에도 다른 요청 동시 처리

### 4-2. API 엔드포인트

#### `POST /start`
- **입력**: 사용자 이력서
- **동작**: `career_agent.ainvoke()` → 분석 + 계획 노드 실행 → `interrupt` 지점에서 정지
- **출력**: `roadmap_draft` (초안)

#### `POST /feedback`
- **입력**: 사용자 피드백 (`{ thread_id, feedback }`)
- **동작**: `Command(resume=req.feedback)`로 에이전트 재개
  - `revision_requested` → 로드맵 수정
  - `approved` → 최종 승인
- **상태 판단**: `aget_state()` 스냅샷 분석으로 종료/대기 자동 판단

#### `GET /history/{thread_id}`
- **출력**: JSON
  - `current_roadmap`: 현재 로드맵
  - `revision_count`: 총 수정 횟수
  - `revision_history`: 버전별 이전 로드맵 목록
- **구현**: `AgentState`에 `revision_history` 필드 + LangGraph **Annotated Reducer 패턴** → reviser 실행 시마다 자동 누적

### 4-3. Swagger UI
- API 설계 단계부터 활용
- State 값 전달 및 HITL 피드백 엔드포인트 시각적 문서화·테스트

---

## 5. 프론트엔드 설계 (React)

### 5-1. Interactive Roadmap UI
- 에이전트가 반환한 JSON 로드맵 → 동적 **타임라인 형태** 렌더링

### 5-2. HITL 인터랙션
- 사용자가 특정 학습 카드(Node) 클릭 → 수정 사항 입력
- `/feedback` 엔드포인트로 전송 → 해당 부분만 다시 그림

### 5-3. State 시각화
- 에이전트의 현재 단계(분석 중 / 계획 중 / 피드백 대기 중) 실시간 표시

---


---

## 6. 개발 진행 상황

### ✅ 완료
- LangGraph 기반 상태 관리 및 피드백 순환 로직
- FastAPI 에이전트 컨트롤러 및 HITL 인터럽트 엔드포인트 구현
- SQLite 체크포인트 영속화 (`AsyncSqliteSaver`)
- `/start`, `/feedback`, `/history` 엔드포인트

### 🔄 진행 중
- 사용자 기술 스택 분석 데이터 보존을 위한 DB 연동 작업

### 📌 향후 계획
| 기한 | 작업 |
|------|------|
| ~5/10 | React 기반 대시보드 UI 개발 (에이전트 추론 과정 시각화) |
| ~5/20 | Time-travel 기능 고도화 (LangGraph Checkpointer 활용) |
| ~5/31 | 주니어 개발자 대상 사용성 평가 및 최종 제출 |

---

## 7. 코딩 시 우선순위 / 주의사항

1. **비동기 일관성 유지**: 모든 LangGraph 호출은 `ainvoke`, `aget_state` 등 비동기 패턴 사용
2. **State 불변성**: AgentState 수정 시 Annotated Reducer 패턴 활용
3. **thread_id 검증**: 모든 엔드포인트에서 세션 ID 유효성 확인
4. **interrupt 처리**: `Command(resume=...)`로만 재개, 직접 상태 조작 금지
5. **체크포인트 무결성**: `checkpoints.db` 동시성 이슈 주의 (`AsyncSqliteSaver` 사용)

---

## 작품명 (제출용)

**LangGraph의 Human-in-the-loop 구조를 활용한 주니어 개발자 맞춤형 지능형 커리어 로드맵 생성 에이전트**

