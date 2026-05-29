from datetime import datetime, timezone
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.schemas import Roadmap, assign_step_ids, reconcile_status
from app.state import AgentState


@lru_cache(maxsize=1)
def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


@lru_cache(maxsize=1)
def _get_roadmap_llm():
    """구조화된 Roadmap 스키마로 응답하는 LLM 러너."""
    return _get_llm().with_structured_output(Roadmap)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot(steps: list[dict], reason: str) -> dict:
    return {"timestamp": _now_iso(), "reason": reason, "steps": steps}


async def analyzer(state: AgentState) -> AgentState:
    """사용자의 이력서 텍스트를 분석해 현재 보유 기술 스택을 추출한다."""
    resume_text = state["user_info"]

    response = await _get_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 시니어 테크 리크루터입니다. "
                    "주어진 이력서에서 프로그래밍 언어, 프레임워크, 도구, "
                    "클라우드 서비스 등 기술 스택을 추출하세요. "
                    "쉼표로 구분된 목록만 반환하세요."
                ),
            },
            {"role": "user", "content": resume_text},
        ]
    )

    skills = [s.strip() for s in response.content.split(",") if s.strip()]
    return {"skills": skills}


async def planner(state: AgentState) -> AgentState:
    """부족한 기술을 분석하고 실행 가능한 구조화 로드맵을 생성한다."""
    skills_text = ", ".join(state.get("skills", []))

    roadmap: Roadmap = await _get_roadmap_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 주니어 개발자를 위한 커리어 코치입니다. "
                    "현재 보유 스택을 기반으로 부족한 기술을 분석하고, "
                    "4~6개의 '실행 가능한 학습 단계'로 구성된 로드맵을 설계하세요. "
                    "각 단계에는 제목, 설명, 예상 소요 기간(주), 습득 기술, "
                    "추천 학습 리소스 2~3개(실제 존재하는 공식 문서/유명 강의의 제목과 URL), "
                    "그리고 구체적인 토이 프로젝트 아이디어를 포함하세요. "
                    "단계는 난이도 순으로 정렬하세요."
                ),
            },
            {"role": "user", "content": f"현재 보유 기술: {skills_text}"},
        ]
    )

    steps = assign_step_ids([s.model_dump() for s in roadmap.steps])
    return {"roadmap": steps}


async def human_review(state: AgentState) -> AgentState:
    """사용자 개입 지점. interrupt_before 로 진입 전에 멈춘다."""
    return state


async def reviser(state: AgentState) -> AgentState:
    """사용자 피드백을 반영해 로드맵을 수정한다. 완료 단계는 보존."""
    previous = state.get("roadmap", [])

    roadmap: Roadmap = await _get_roadmap_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 커리어 코치입니다. 기존 구조화 로드맵과 사용자 피드백을 "
                    "바탕으로 로드맵을 수정하세요. 이미 완료(done)된 단계는 변경하지 말고 "
                    "그대로 유지하고, 나머지 단계를 피드백에 맞게 조정하세요. "
                    "각 단계 형식(제목/설명/기간/기술/리소스/프로젝트)을 유지하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 기존 로드맵(JSON)\n{previous}\n\n"
                    f"## 사용자 피드백\n{state.get('user_feedback', '')}"
                ),
            },
        ]
    )

    new_steps = assign_step_ids(
        reconcile_status(previous, [s.model_dump() for s in roadmap.steps])
    )
    return {
        "roadmap": new_steps,
        "revision_history": [_snapshot(previous, "revise")],
    }


async def replanner(state: AgentState) -> AgentState:
    """진행 속도와 시장 트렌드를 반영해 남은 단계를 재조정한다."""
    previous = state.get("roadmap", [])
    pace_note = state.get("user_feedback", "")

    roadmap: Roadmap = await _get_roadmap_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 주니어 개발자의 성장을 지속적으로 돕는 커리어 코치입니다. "
                    "사용자의 학습 진행 속도와 최신 시장 트렌드를 함께 고려해 "
                    "로드맵을 재조정하세요. 규칙:\n"
                    "1) 이미 완료(done)된 단계는 절대 변경하지 말고 그대로 유지합니다.\n"
                    "2) 진행이 예상보다 빠르면 남은/추가 단계의 난이도를 높이거나 심화 주제를 추가합니다.\n"
                    "3) 진행이 느리면 보강 단계를 추가하거나 범위를 현실적으로 줄입니다.\n"
                    "4) 시장에서 더 각광받는 기술이 있으면 남은 단계에 반영하고 그 이유를 설명에 적습니다.\n"
                    "각 단계 형식(제목/설명/기간/기술/리소스/프로젝트)을 유지하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 현재 로드맵(JSON, status 포함)\n{previous}\n\n"
                    f"## 진행 상황 분석\n{pace_note}"
                ),
            },
        ]
    )

    new_steps = assign_step_ids(
        reconcile_status(previous, [s.model_dump() for s in roadmap.steps])
    )
    return {
        "roadmap": new_steps,
        "revision_history": [_snapshot(previous, "replan")],
    }
