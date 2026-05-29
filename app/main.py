import logging
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.error")

load_dotenv()

from app.graph import DB_PATH, compiled_graph  # noqa: E402
from app.parsers import extract_resume_text  # noqa: E402
from app.schemas import RoadmapStep  # noqa: E402

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


class Progress(BaseModel):
    total: int
    done: int
    percent: int


class StartResponse(BaseModel):
    thread_id: str
    skills: list[str]
    roadmap: list[RoadmapStep]
    message: str


class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: str


class FeedbackResponse(BaseModel):
    status: str
    roadmap: list[RoadmapStep] = []
    approved: bool = False
    message: str


class ProgressRequest(BaseModel):
    thread_id: str
    step_id: str
    status: str  # "done" | "todo"


class ProgressResponse(BaseModel):
    roadmap: list[RoadmapStep]
    progress: Progress
    message: str


class ReplanRequest(BaseModel):
    thread_id: str


class ReplanResponse(BaseModel):
    roadmap: list[RoadmapStep]
    pace: str
    progress: Progress
    message: str


class RoadmapResponse(BaseModel):
    thread_id: str
    skills: list[str]
    roadmap: list[RoadmapStep]
    approved: bool
    progress: Progress


class HistoryResponse(BaseModel):
    thread_id: str
    revision_count: int
    revision_history: list[dict]


# ──────────────────────────── 헬퍼 ────────────────────────────


def _progress(roadmap: list[dict]) -> Progress:
    total = len(roadmap)
    done = sum(1 for s in roadmap if s.get("status") == "done")
    percent = round(done / total * 100) if total else 0
    return Progress(total=total, done=done, percent=percent)


def _compute_pace(roadmap: list[dict], started_at: str | None) -> tuple[str, str]:
    """완료 단계 수와 경과 시간을 비교해 진행 속도(ahead/behind/on_track)를 평가한다."""
    total = len(roadmap)
    done = sum(1 for s in roadmap if s.get("status") == "done")

    elapsed_weeks = 0.0
    if started_at:
        try:
            start = datetime.fromisoformat(started_at)
            elapsed_weeks = (
                datetime.now(timezone.utc) - start
            ).total_seconds() / (7 * 24 * 3600)
        except ValueError:
            elapsed_weeks = 0.0

    cumulative = 0
    expected_done = 0
    for step in roadmap:
        cumulative += step.get("duration_weeks", 0) or 0
        if cumulative <= elapsed_weeks:
            expected_done += 1

    if done > expected_done:
        status = "ahead"
    elif done < expected_done:
        status = "behind"
    else:
        status = "on_track"

    note = (
        f"전체 {total}단계 중 {done}단계 완료. "
        f"학습 시작 후 약 {elapsed_weeks:.1f}주 경과, 계획상 예상 완료는 {expected_done}단계. "
        f"진행 속도 평가: {status}."
    )
    return status, note


async def _require_active(config: dict):
    """재개 가능한(대기 중) 세션 스냅샷을 반환하거나 에러를 던진다."""
    snapshot = await career_agent.aget_state(config)
    if not snapshot.values:
        raise HTTPException(404, "해당 thread_id의 세션을 찾을 수 없습니다.")
    if not snapshot.next:
        raise HTTPException(400, "이미 종료된 세션입니다. 재개할 수 없습니다.")
    return snapshot


# ──────────────────────────── 엔드포인트 ────────────────────────────


async def _run_start(resume_text: str) -> StartResponse:
    """이력서 텍스트로 에이전트를 시작하고 interrupt 시점의 결과를 반환한다."""
    if not resume_text or not resume_text.strip():
        raise HTTPException(400, "이력서 내용이 비어 있습니다.")

    thread_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    await career_agent.ainvoke({"user_info": resume_text}, config=config)

    snapshot = await career_agent.aget_state(config)
    if not snapshot.next:
        raise HTTPException(500, "그래프가 interrupt 없이 종료되었습니다.")

    return StartResponse(
        thread_id=thread_id,
        skills=snapshot.values.get("skills", []),
        roadmap=snapshot.values.get("roadmap", []),
        message="로드맵을 검토해주세요. 승인('approve')하거나 수정 요청을 입력할 수 있습니다.",
    )


@app.post("/start", response_model=StartResponse)
async def start_agent(req: StartRequest):
    """이력서 텍스트를 받아 로드맵 생성 에이전트를 시작한다."""
    return await _run_start(req.resume_text)


@app.post("/start/upload", response_model=StartResponse)
async def start_agent_from_file(file: UploadFile = File(...)):
    """이력서 파일(PDF/DOCX/TXT/MD)을 받아 텍스트 추출 후 에이전트를 시작한다."""
    data = await file.read()
    resume_text = extract_resume_text(file.filename, data)
    return await _run_start(resume_text)


@app.post("/feedback", response_model=FeedbackResponse)
async def send_feedback(req: FeedbackRequest):
    """로드맵을 승인하거나 수정 요청을 보내 그래프를 재개한다."""
    config = {"configurable": {"thread_id": req.thread_id}}
    await _require_active(config)

    is_approve = req.feedback.strip().lower() == "approve"

    if is_approve:
        snapshot = await career_agent.aget_state(config)
        update = {"action": "approve", "approved": True}
        if not snapshot.values.get("started_at"):
            update["started_at"] = datetime.now(timezone.utc).isoformat()
        await career_agent.aupdate_state(config, update)
    else:
        await career_agent.aupdate_state(
            config,
            {"action": "revise", "user_feedback": req.feedback},
        )

    await career_agent.ainvoke(None, config=config)
    updated = await career_agent.aget_state(config)
    roadmap = updated.values.get("roadmap", [])

    if is_approve:
        return FeedbackResponse(
            status="approved",
            roadmap=roadmap,
            approved=True,
            message="로드맵이 승인되었습니다. 이제 단계별로 학습을 진행하고 완료를 체크하세요.",
        )

    return FeedbackResponse(
        status="revision_requested",
        roadmap=roadmap,
        approved=updated.values.get("approved", False),
        message="피드백을 반영해 로드맵을 수정했습니다. 다시 검토해주세요.",
    )


@app.post("/progress", response_model=ProgressResponse)
async def update_progress(req: ProgressRequest):
    """특정 단계의 완료 여부를 갱신한다. (LLM 호출 없이 상태만 변경)"""
    if req.status not in ("done", "todo"):
        raise HTTPException(400, "status 는 'done' 또는 'todo' 여야 합니다.")

    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = await career_agent.aget_state(config)
    if not snapshot.values:
        raise HTTPException(404, "해당 thread_id의 세션을 찾을 수 없습니다.")

    roadmap = [dict(s) for s in snapshot.values.get("roadmap", [])]
    if not any(s.get("id") == req.step_id for s in roadmap):
        raise HTTPException(404, f"단계 '{req.step_id}'를 찾을 수 없습니다.")

    for step in roadmap:
        if step.get("id") == req.step_id:
            step["status"] = req.status

    await career_agent.aupdate_state(config, {"roadmap": roadmap})

    return ProgressResponse(
        roadmap=roadmap,
        progress=_progress(roadmap),
        message="진행 상황이 업데이트되었습니다.",
    )


@app.post("/replan", response_model=ReplanResponse)
async def replan(req: ReplanRequest):
    """진행 속도와 시장 트렌드를 반영해 남은 단계를 재조정한다."""
    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = await _require_active(config)

    roadmap = snapshot.values.get("roadmap", [])
    pace_status, pace_note = _compute_pace(
        roadmap, snapshot.values.get("started_at")
    )

    await career_agent.aupdate_state(
        config,
        {"action": "replan", "user_feedback": pace_note},
    )
    await career_agent.ainvoke(None, config=config)

    updated = await career_agent.aget_state(config)
    new_roadmap = updated.values.get("roadmap", [])

    return ReplanResponse(
        roadmap=new_roadmap,
        pace=pace_status,
        progress=_progress(new_roadmap),
        message="진행 속도와 시장 트렌드를 반영해 로드맵을 재조정했습니다.",
    )


@app.get("/roadmap/{thread_id}", response_model=RoadmapResponse)
async def get_roadmap(thread_id: str):
    """현재 구조화 로드맵과 진행률을 조회한다."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await career_agent.aget_state(config)
    if not snapshot.values:
        raise HTTPException(404, "해당 thread_id의 세션을 찾을 수 없습니다.")

    roadmap = snapshot.values.get("roadmap", [])
    return RoadmapResponse(
        thread_id=thread_id,
        skills=snapshot.values.get("skills", []),
        roadmap=roadmap,
        approved=snapshot.values.get("approved", False),
        progress=_progress(roadmap),
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
        revision_count=len(history),
        revision_history=history,
    )
