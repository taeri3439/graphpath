from typing import Annotated, TypedDict


def append_to_list(existing: list, new: list) -> list:
    """기존 리스트에 새 항목을 누적한다 (reducer)."""
    return (existing or []) + (new or [])


class AgentState(TypedDict, total=False):
    """지능형 커리어 로드맵 생성·실행 추적 에이전트의 상태 정의."""

    user_info: str
    skills: list[str]
    # 구조화된 로드맵: RoadmapStep 의 dict 목록
    roadmap: list[dict]
    user_feedback: str
    # human_review 이후 분기를 결정하는 제어 신호: revise | replan | approve | finish
    action: str
    # 사용자가 로드맵을 승인했는지 여부
    approved: bool
    # 승인(실행 시작) 시점 ISO 타임스탬프 (진행 속도 계산용)
    started_at: str
    # 버전별 스냅샷 누적: {"timestamp", "reason", "steps"}
    revision_history: Annotated[list[dict], append_to_list]
