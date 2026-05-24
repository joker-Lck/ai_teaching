"""
学情分析 API - 报告生成 + 数据管理
"""
import json
import time
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional

from backend.schemas.models import (
    AnalysisRequest, AnalysisReportResponse,
    DataManageRequest, BaseResponse,
)
from backend.dependencies import get_current_user, require_auth, get_api_config
from services.analysis_service import AnalysisService
from core.logger import info

router = APIRouter()


@router.post("/report", response_model=AnalysisReportResponse)
async def generate_report(
    req: AnalysisRequest,
    user: dict = Depends(get_current_user),
):
    """生成学情分析报告"""
    config = get_api_config()
    analysis_service = AnalysisService()

    try:
        student_info = {}
        if req.analysis_mode == "单个学生":
            student_info = {"name": req.student_name or "某同学"}
        else:
            student_info = {
                "class_name": req.class_name or "某班",
                "total_students": req.total_students,
            }

        result = analysis_service.generate_report(
            analysis_mode=req.analysis_mode,
            student_info=student_info,
            uploaded_files=None,
            questions_data=[],
            api_key=config["api_key"],
            base_url=config["base_url"],
        )

        if result["success"]:
            return AnalysisReportResponse(
                success=True,
                report=result["report"],
            )
        else:
            return AnalysisReportResponse(
                success=False,
                error=result.get("error", "生成失败"),
            )
    except Exception as e:
        return AnalysisReportResponse(success=False, error=str(e))


@router.post("/report-stream")
async def generate_report_stream(
    req: AnalysisRequest,
    user: dict = Depends(get_current_user),
):
    """生成学情分析报告 - SSE 流式输出"""
    config = get_api_config()

    async def stream_report():
        analysis_service = AnalysisService()

        try:
            student_info = {}
            if req.analysis_mode == "单个学生":
                student_info = {"name": req.student_name or "某同学"}
            else:
                student_info = {
                    "class_name": req.class_name or "某班",
                    "total_students": req.total_students,
                }

            yield f"data: {json.dumps({'type': 'status', 'message': '正在分析学习数据...'}, ensure_ascii=False)}\n\n"

            result = analysis_service.generate_report(
                analysis_mode=req.analysis_mode,
                student_info=student_info,
                uploaded_files=None,
                questions_data=[],
                api_key=config["api_key"],
                base_url=config["base_url"],
            )

            if result["success"]:
                report = result["report"]
                chunk_size = 20
                for i in range(0, len(report), chunk_size):
                    chunk = report[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', '生成失败')}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream_report(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload-data")
async def upload_analysis_data(
    files: List[UploadFile] = File(...),
    user: dict = Depends(require_auth),
):
    """上传学情分析数据文件"""
    uploaded = []
    for file in files:
        try:
            content = await file.read()
            uploaded.append({
                "filename": file.filename,
                "size": len(content),
                "status": "success",
            })
        except Exception as e:
            uploaded.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e),
            })

    return {
        "success": True,
        "uploaded": uploaded,
        "message": f"已上传 {len([u for u in uploaded if u['status'] == 'success'])} 个文件",
    }


@router.post("/data-manage")
async def manage_data(
    req: DataManageRequest,
    user: dict = Depends(require_auth),
):
    """数据管理操作 (备份/恢复/导出/清空/搜索)"""
    analysis_service = AnalysisService()

    result = analysis_service.manage_learning_data(req.action, keyword=req.keyword, format=req.format)

    return result


@router.get("/data")
async def get_analysis_data(
    user: dict = Depends(get_current_user),
):
    """获取学习数据统计"""
    analysis_service = AnalysisService()

    try:
        result = analysis_service.get_statistics()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}
