from langgraph.graph import END, StateGraph

from app.nodes import analyzer, human_review, planner, reviser
from app.state import AgentState

DB_PATH = "checkpoints.db"


def should_continue(state: AgentState) -> str:
    """사용자 피드백에 따라 종료 또는 수정 루프로 분기한다."""
    feedback = state.get("user_feedback", "")
    if feedback.strip().lower() == "approve":
        return "end"
    return "revise"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("analyzer", analyzer)
    graph.add_node("planner", planner)
    graph.add_node("human_review", human_review)
    graph.add_node("reviser", reviser)

    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "planner")
    graph.add_edge("planner", "human_review")
    graph.add_conditional_edges(
        "human_review",
        should_continue,
        {"end": END, "revise": "reviser"},
    )
    graph.add_edge("reviser", "human_review")

    return graph


compiled_graph = build_graph()
