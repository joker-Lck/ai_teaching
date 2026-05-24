"""
FastAPI 应用入口
多模态 AI 教学智能体 - 后端 API 服务
"""
import sys
import os

# 将项目根目录添加到 Python 路径, 以便复用现有 services/data/core 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from backend.api.auth import router as auth_router
from backend.api.qa import router as qa_router
from backend.api.courseware import router as courseware_router
from backend.api.knowledge import router as knowledge_router
from backend.api.analysis import router as analysis_router
from backend.api.ws import router as ws_router

from core.logger import info, error as log_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    info("🚀 AI 教学智能体 API 服务启动")
    yield
    info("👋 AI 教学智能体 API 服务关闭")


app = FastAPI(
    title="多模态 AI 教学智能体 API",
    description="基于 Kimi 大模型的智能教学辅助系统后端 API",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 配置 - 允许 Next.js 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(qa_router, prefix="/api/qa", tags=["智能答疑"])
app.include_router(courseware_router, prefix="/api/courseware", tags=["课件生成"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["知识库管理"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["学情分析"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(f"未捕获的异常: {str(exc)}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "服务器内部错误",
            "detail": str(exc),
        },
    )


# 健康检查
@app.get("/api/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "6.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# 系统信息
@app.get("/api/info", tags=["系统"])
async def system_info():
    """系统信息"""
    from data.data_manager import CacheManager

    config = CacheManager.load_env_config()
    return {
        "name": "多模态 AI 教学智能体",
        "version": "6.0.0",
        "api_base": config.get("base_url", ""),
        "features": [
            "智能答疑 (SSE 流式输出)",
            "课件生成 (WebSocket 实时进度)",
            "学情分析 (动态可视化)",
            "知识库管理 (RAG 智能检索)",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
