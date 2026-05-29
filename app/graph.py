from langgraph.graph import END, StateGraph

from app.nodes import analyzer, human_review, planner, replanner, reviser
from app.state import AgentState

DB_PATH = "checkpoints.db"


def route_after_review(state: AgentState) -> str:
    """human_review 이후 action 신호에 따라 분기한다.

    - revise : 사용자 피드백으로 로드맵 수정
    - replan : 진행 속도/트렌드 기반 재조정
    - finish : 세션 종료
    - 그 외(approve 포함) : 세션을 유지한 채 다시 대기
    """
    action = (state.get("action") or "").strip().lower()
    if action == "revise":
        return "revise"
    if action == "replan":
        return "replan"
    if action == "finish":
        return "finish"
    return "stay"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("analyzer", analyzer)
    graph.add_node("planner", planner)
    graph.add_node("human_review", human_review)
    graph.add_node("reviser", reviser)
    graph.add_node("replanner", replanner)

    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "planner")
    graph.add_edge("planner", "human_review")
    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "revise": "reviser",
            "replan": "replanner",
            "finish": END,
            # 승인 후에도 세션을 살려두어 지속적인 진행 추적/재조정을 가능하게 한다.
            "stay": "human_review",
        },
    )
    graph.add_edge("reviser", "human_review")
    graph.add_edge("replanner", "human_review")

    return graph


compiled_graph = build_graph()
