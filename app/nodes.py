from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.state import AgentState


@lru_cache(maxsize=1)
def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


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
    """부족한 기술 스택을 분석하고 학습 로드맵 초안을 생성한다."""
    skills = state["skills"]
    skills_text = ", ".join(skills)

    response = await _get_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 주니어 개발자를 위한 커리어 코치입니다. "
                    "현재 보유 스택을 기반으로 부족한 기술을 분석하고, "
                    "3~6개월 단위의 학습 로드맵을 마크다운 형식으로 작성하세요. "
                    "각 단계에 구체적인 학습 자료와 프로젝트 아이디어를 포함하세요."
                ),
            },
            {
                "role": "user",
                "content": f"현재 보유 기술: {skills_text}",
            },
        ]
    )

    return {"roadmap_draft": response.content}


async def human_review(state: AgentState) -> AgentState:
    """사용자 피드백을 상태에 반영한다. (interrupt_before로 진입 전에 멈춤)"""
    return state


async def reviser(state: AgentState) -> AgentState:
    """사용자 피드백을 반영해 로드맵을 수정한다. 수정 전 버전은 이력에 보존."""
    previous_draft = state["roadmap_draft"]

    response = await _get_llm().ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "당신은 커리어 코치입니다. "
                    "기존 로드맵과 사용자 피드백을 바탕으로 "
                    "로드맵을 수정하세요. 마크다운 형식을 유지하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## 기존 로드맵\n{previous_draft}\n\n"
                    f"## 사용자 피드백\n{state['user_feedback']}"
                ),
            },
        ]
    )

    return {
        "roadmap_draft": response.content,
        "revision_history": [previous_draft],
    }
