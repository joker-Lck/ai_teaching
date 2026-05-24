"""
智能答疑 API - SSE 流式输出 + 多轮对话
"""
import json
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Optional

from backend.schemas.models import QARequest, QAResponse, BaseResponse
from backend.dependencies import get_current_user, get_api_config
from services.qa_service import QAService
from data.qa_db_operations import qa_db
from data.rag_knowledge_base import rag_kb
from data.embedding_service import embedding_service
from core.logger import info, warning

router = APIRouter()


@router.post("/ask")
async def ask_question_stream(
    req: QARequest,
    user: dict = Depends(get_current_user),
):
    """智能答疑 - SSE 流式输出

    返回 Server-Sent Events 流, 前端可逐字显示 AI 回答。
    """
    config = get_api_config()

    async def generate_stream():
        qa_service = QAService()
        start_time = time.time()

        try:
            # 先发送状态
            yield f"data: {json.dumps({'type': 'status', 'message': '正在检索知识库...'}, ensure_ascii=False)}\n\n"

            # 调用 QA 服务处理问题
            result = qa_service.handle_text_question(
                question=req.question,
                scenario=req.scenario,
                api_key=config["api_key"],
                base_url=config["base_url"],
            )

            if result["success"]:
                answer = result["answer"]
                source_info = result.get("source_info", "")
                rag_docs = result.get("rag_docs_found", [])

                # 模拟流式输出 (将完整回答分段发送)
                chunk_size = 10  # 每次发送的字符数
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

                # 发送完成信息
                elapsed = (time.time() - start_time) * 1000
                yield f"data: {json.dumps({\
                    'type': 'done',\
                    'source_info': source_info,\
                    'rag_docs_found': [{'title': d.get('title', ''), 'subject': d.get('subject', '')} for d in rag_docs],\
                    'response_time_ms': round(elapsed, 1),\
                    'tokens_used': result.get('tokens_used'),\
                }, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', '请求失败')}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask-sync", response_model=QAResponse)
async def ask_question_sync(
    req: QARequest,
    user: dict = Depends(get_current_user),
):
    """智能答疑 - 同步返回 (非流式)"""
    config = get_api_config()

    qa_service = QAService()
    start_time = time.time()

    result = qa_service.handle_text_question(
        question=req.question,
        scenario=req.scenario,
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    elapsed = (time.time() - start_time) * 1000

    if result["success"]:
        rag_docs = result.get("rag_docs_found", [])
        return QAResponse(
            success=True,
            answer=result["answer"],
            source_info=result.get("source_info", ""),
            tokens_used=result.get("tokens_used"),
            response_time_ms=round(elapsed, 1),
            rag_docs_found=[
                {"title": d.get("title", ""), "subject": d.get("subject", "")}
                for d in rag_docs
            ],
        )
    else:
        return QAResponse(
            success=False,
            error=result.get("error", "请求失败"),
        )


@router.get("/history")
async def get_qa_history(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """获取问答历史"""
    try:
        records = qa_db.get_recent_records(limit=limit)
        return {
            "success": True,
            "records": records or [],
            "total": len(records) if records else 0,
        }
    except Exception as e:
        return {"success": False, "records": [], "error": str(e)}


@router.delete("/history", response_model=BaseResponse)
async def clear_qa_history(user: dict = Depends(get_current_user)):
    """清空问答历史"""
    try:
        qa_db.clear_all_records()
        return BaseResponse(success=True, message="问答历史已清空")
    except Exception as e:
        return BaseResponse(success=False, error=str(e))


@router.post("/search")
async def search_knowledge(
    req: QARequest,
    user: dict = Depends(get_current_user),
):
    """RAG 知识检索"""
    try:
        # 优先向量检索
        query_embedding = embedding_service.get_embedding(req.question)
        results = []

        if query_embedding:
            results = rag_kb.search_documents_by_vector(query_embedding, limit=3)

        if not results:
            results = rag_kb.search_documents(req.question, limit=3)

        return {
            "success": True,
            "results": [
                {
                    "title": r.get("title", ""),
                    "subject": r.get("subject", ""),
                    "content_preview": r.get("content_text", "")[:300],
                    "similarity": r.get("similarity", 0),
                }
                for r in (results or [])
            ],
        }
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}
