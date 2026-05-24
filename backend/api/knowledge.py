"""
知识库管理 API - 文档上传/搜索/管理
"""
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List, Optional

from backend.schemas.models import (
    KnowledgeSearchRequest, KnowledgeDocument,
    KnowledgeStatsResponse, BaseResponse,
)
from backend.dependencies import get_current_user, require_auth, get_api_config
from services.knowledge_service import KnowledgeService
from data.rag_knowledge_base import rag_kb
from data.document_parser import doc_parser
from data.embedding_service import embedding_service
from core.logger import info, warning

router = APIRouter()


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_stats(user: dict = Depends(get_current_user)):
    """获取知识库统计信息"""
    try:
        stats = rag_kb.get_statistics()
        return KnowledgeStatsResponse(
            success=True,
            total_documents=stats.get("total_documents", 0),
            total_knowledge_points=stats.get("total_knowledge_points", 0),
            average_usage=stats.get("average_usage", 0.0),
            subject_distribution=stats.get("subject_distribution", []),
        )
    except Exception as e:
        return KnowledgeStatsResponse(success=False, error=str(e))


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    category: str = "通用",
    user: dict = Depends(require_auth),
):
    """上传文档到知识库"""
    knowledge_service = KnowledgeService()
    uploaded_count = 0
    failed_files = []

    for file in files:
        try:
            content = await file.read()
            result = knowledge_service.upload_single_document(
                file_name=file.filename,
                file_content=content,
                file_type=file.filename.split(".")[-1] if "." in file.filename else "txt",
                category=category,
            )
            if result.get("success"):
                uploaded_count += 1
            else:
                failed_files.append(file.filename)
        except Exception as e:
            warning(f"上传文件失败: {file.filename} - {str(e)}")
            failed_files.append(file.filename)

    return {
        "success": uploaded_count > 0,
        "uploaded_count": uploaded_count,
        "failed_files": failed_files,
        "message": f"成功上传 {uploaded_count} 个文档",
    }


@router.get("/documents")
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    subject: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """获取知识库文档列表"""
    try:
        docs = rag_kb.get_all_documents(limit=limit, offset=offset)
        items = []
        for doc in (docs or []):
            doc_data = doc.get("document_data", {})
            metadata = doc_data.get("metadata", {})
            title = metadata.get("title", doc.get("title", "未知文档"))
            doc_subject = metadata.get("subject", doc.get("file_type", "通用"))

            # 学科筛选
            if subject and doc_subject != subject:
                continue

            items.append({
                "id": doc.get("id"),
                "title": title,
                "subject": doc_subject,
                "file_type": metadata.get("file_type", doc.get("file_type", "")),
                "file_size": doc.get("file_size", 0),
                "upload_time": str(metadata.get("upload_time", doc.get("upload_time", ""))),
            })

        return {"success": True, "documents": items, "total": len(items)}
    except Exception as e:
        return {"success": False, "documents": [], "error": str(e)}


@router.delete("/documents/{doc_id}", response_model=BaseResponse)
async def delete_document(
    doc_id: int,
    user: dict = Depends(require_auth),
):
    """删除知识库文档"""
    try:
        rag_kb.delete_document(doc_id)
        return BaseResponse(success=True, message="文档已删除")
    except Exception as e:
        return BaseResponse(success=False, error=str(e))


@router.delete("/documents", response_model=BaseResponse)
async def clear_all_documents(user: dict = Depends(require_auth)):
    """清空所有知识库文档"""
    try:
        docs = rag_kb.get_all_documents(limit=10000)
        count = 0
        for doc in (docs or []):
            try:
                rag_kb.delete_document(doc["id"])
                count += 1
            except Exception:
                pass
        return BaseResponse(success=True, message=f"已清空 {count} 个文档")
    except Exception as e:
        return BaseResponse(success=False, error=str(e))


@router.post("/search")
async def search_documents(
    req: KnowledgeSearchRequest,
    user: dict = Depends(get_current_user),
):
    """RAG 智能检索"""
    try:
        # 优先向量检索
        query_embedding = embedding_service.get_embedding(req.query)
        results = []

        if query_embedding:
            results = rag_kb.search_documents_by_vector(query_embedding, limit=req.limit)

        # 降级到全文搜索
        if not results:
            results = rag_kb.search_documents(req.query, limit=req.limit)

        # 学科筛选
        if req.subject and results:
            results = [r for r in results if r.get("subject") == req.subject]

        return {
            "success": True,
            "results": [
                {
                    "id": r.get("id"),
                    "title": r.get("title", ""),
                    "subject": r.get("subject", ""),
                    "content_text": r.get("content_text", "")[:500],
                    "similarity": r.get("similarity", 0),
                }
                for r in (results or [])
            ],
            "total": len(results) if results else 0,
        }
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}


@router.post("/analyze")
async def analyze_documents(
    user: dict = Depends(require_auth),
):
    """AI 智能解析知识库文档"""
    config = get_api_config()
    knowledge_service = KnowledgeService()

    try:
        docs = rag_kb.get_all_documents(limit=50)
        if not docs:
            return {"success": False, "error": "知识库中没有文档"}

        doc_list = [
            f"- {d.get('title', '未知')} ({d.get('file_type', '')})"
            for d in docs[:20]
        ]

        result = knowledge_service.analyze_documents(
            documents=[{"name": d.get("title", ""), "category": d.get("file_type", "")} for d in docs[:20]],
            api_key=config["api_key"],
            base_url=config["base_url"],
        )

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
