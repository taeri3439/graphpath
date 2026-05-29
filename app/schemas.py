"""구조화된 로드맵 데이터 스키마.

LLM structured output 생성과 API 응답 직렬화에 함께 사용한다.
"""

from pydantic import BaseModel, Field


class Resource(BaseModel):
    """학습 단계에 첨부되는 추천 리소스(강의/문서 등)."""

    title: str = Field(description="리소스 제목")
    url: str = Field(description="리소스 URL (공식 문서/강의 등)")


class RoadmapStep(BaseModel):
    """로드맵을 구성하는 실행 가능한 학습 단계."""

    id: str = Field(default="", description="단계 식별자 (서버에서 부여)")
    title: str = Field(description="단계 제목")
    description: str = Field(description="이 단계에서 무엇을, 왜 배우는지 설명")
    duration_weeks: int = Field(description="예상 소요 기간(주 단위)")
    skills: list[str] = Field(default_factory=list, description="이 단계에서 습득할 기술")
    resources: list[Resource] = Field(
        default_factory=list, description="추천 학습 리소스 2~3개"
    )
    project: str = Field(default="", description="이 단계에 추천하는 토이 프로젝트")
    status: str = Field(default="todo", description="진행 상태: todo | done")


class Roadmap(BaseModel):
    """LLM이 생성하는 단계 묶음."""

    steps: list[RoadmapStep] = Field(description="순서대로 정렬된 학습 단계 목록")


def assign_step_ids(steps: list[dict]) -> list[dict]:
    """단계 리스트에 step-1, step-2 ... 형태의 안정적인 id 를 부여한다."""
    for idx, step in enumerate(steps, start=1):
        step["id"] = f"step-{idx}"
        step.setdefault("status", "todo")
    return steps


def reconcile_status(old_steps: list[dict], new_steps: list[dict]) -> list[dict]:
    """재생성된 단계에 기존 완료(done) 상태를 보존한다.

    제목이 동일한 단계는 이전 상태를 그대로 유지하여
    수정/재조정 시 이미 완료한 단계가 미완료로 되돌아가지 않게 한다.
    """
    done_titles = {
        s.get("title", "").strip()
        for s in old_steps
        if s.get("status") == "done"
    }
    for step in new_steps:
        if step.get("title", "").strip() in done_titles:
            step["status"] = "done"
    return new_steps
