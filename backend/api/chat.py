"""
对话 API 接口 - SSE 流式
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.models.schemas import ChatRequest, RouteRequest
from backend.services import chat_service
from backend.core.router import route_to_industry

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/route")
def route_chat(body: RouteRequest):
    """行业路由判断"""
    result = route_to_industry(body.query)
    return {"code": 0, "data": result, "message": "success"}


@router.post("/stream")
async def stream_chat(body: ChatRequest):
    """流式对话（SSE）"""
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=422, detail={"code": 1, "message": "问题不能为空"})

    async def generate():
        for chunk in chat_service.stream_chat(
            query=body.query,
            history=[h.model_dump() for h in body.history] if body.history else [],
            industry_slug=body.industry,
            session_id=body.session_id,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history")
def get_chat_history():
    """获取对话历史"""
    sessions = chat_service.list_sessions()
    return {"code": 0, "data": sessions, "message": "success"}


@router.get("/history/{session_id}")
def get_session_messages(session_id: str):
    """获取会话消息"""
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": 1, "message": "会话不存在"})
    messages = chat_service.get_session_messages(session_id)
    return {"code": 0, "data": {"session": session, "messages": messages}, "message": "success"}


@router.post("/history")
def create_chat_session():
    """创建新对话会话"""
    session = chat_service.create_session()
    return {"code": 0, "data": session, "message": "success"}


@router.delete("/history/{session_id}")
def delete_session(session_id: str):
    """删除对话会话"""
    chat_service.delete_session(session_id)
    return {"code": 0, "data": None, "message": "success"}