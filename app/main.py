import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.error")

load_dotenv()

from app.graph import DB_PATH, compiled_graph  # noqa: E402

career_agent = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """서버 시작/종료 시 SQLite 체크포인터 연결을 관리한다."""
    global career_agent
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        await checkpointer.setup()
        career_agent = compiled_graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_review"],
        )
        yield
    career_agent = None


app = FastAPI(
    title="Career Roadmap Agent",
    description="주니어 개발자를 위한 지능형 커리어 로드맵 생성 에이전트",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """모든 미처리 예외를 잡아 상세 에러를 응답으로 반환한다."""
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    error_detail = "".join(tb)
    logger.error(f"Unhandled error:\n{error_detail}")
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "detail": error_detail,
        },
    )


# ──────────────────────────── Request / Response 모델 ────────────────────────────


class StartRequest(BaseModel):
    resume_text: str


class StartResponse(BaseModel):
    thread_id: str
    skills: list[str]
    roadmap_draft: str
    message: str


class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: str


class FeedbackResponse(BaseModel):
    status: str
    roadmap_draft: str | None = None
    message: str


class HistoryResponse(BaseModel):
    thread_id: str
    current_roadmap: str | None
    revision_count: int
    revision_history: list[str]


# ──────────────────────────── 엔드포인트 ────────────────────────────


@app.post("/start", response_model=StartResponse)
async def start_agent(req: StartRequest):
    """이력서 텍스트를 받아 로드맵 생성 에이전트를 시작한다."""
    thread_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    await career_agent.ainvoke(
        {"user_info": req.resume_text},
        config=config,
    )

    snapshot = await career_agent.aget_state(config)
    if not snapshot.next:
        raise HTTPException(500, "그래프가 interrupt 없이 종료되었습니다.")

    return StartResponse(
        thread_id=thread_id,
        skills=snapshot.values.get("skills", []),
        roadmap_draft=snapshot.values.get("roadmap_draft", ""),
        message="로드맵을 검토해주세요. 승인하려면 'approve'를, 수정이 필요하면 수정 요청 내용을 입력해주세요.",
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def send_feedback(req: FeedbackRequest):
    """사용자 피드백을 보내 그래프를 재개(resume)한다."""
    config = {"configurable": {"thread_id": req.thread_id}}

    snapshot = await career_agent.aget_state(config)
    if not snapshot.next:
        raise HTTPException(400, "재개할 수 있는 대기 중인 그래프가 없습니다.")

    await career_agent.aupdate_state(
        config,
        {"user_feedback": req.feedback},
    )

    await career_agent.ainvoke(None, config=config)

    updated_snapshot = await career_agent.aget_state(config)

    if not updated_snapshot.next:
        return FeedbackResponse(
            status="approved",
            roadmap_draft=updated_snapshot.values.get("roadmap_draft"),
            message="로드맵이 최종 승인되었습니다.",
        )

    return FeedbackResponse(
        status="revision_requested",
        roadmap_draft=updated_snapshot.values.get("roadmap_draft", ""),
        message="로드맵을 검토해주세요. 승인하려면 'approve'를, 수정이 필요하면 수정 요청 내용을 입력해주세요.",
    )


@app.get("/history/{thread_id}", response_model=HistoryResponse)
async def get_history(thread_id: str):
    """특정 세션의 로드맵 수정 이력을 조회한다."""
    config = {"configurable": {"thread_id": thread_id}}

    snapshot = await career_agent.aget_state(config)
    if not snapshot.values:
        raise HTTPException(404, "해당 thread_id의 세션을 찾을 수 없습니다.")

    history = snapshot.values.get("revision_history", [])
    return HistoryResponse(
        thread_id=thread_id,
        current_roadmap=snapshot.values.get("roadmap_draft"),
        revision_count=len(history),
        revision_history=history,
    )
