from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


def append_to_list(existing: list[str], new: list[str]) -> list[str]:
    """기존 리스트에 새 항목을 누적한다 (reducer)."""
    return existing + new


class AgentState(TypedDict, total=False):
    """지능형 커리어 로드맵 생성 에이전트의 상태 정의."""

    user_info: str
    skills: list[str]
    roadmap_draft: str
    user_feedback: str
    revision_history: Annotated[list[str], append_to_list]
