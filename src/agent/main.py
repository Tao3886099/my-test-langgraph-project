"""FastAPI 应用入口。

启动方式:
    uvicorn agent.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.api.openai_compatible import router as openai_router
from agent.utils.log_utils import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动与关闭时的初始化/清理逻辑。"""
    log.info("FastAPI 应用启动，Agent 已就绪")
    yield
    log.info("FastAPI 应用关闭")


app = FastAPI(
    title="LangGraph Agent API",
    description="基于 LangGraph 的多能力智能体 API，支持数据库查询等功能。",
    version="0.0.1",
    lifespan=lifespan,
)

# ---- 跨域配置 ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 生产环境请替换为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
# app.include_router(chat_router, prefix="/api")
app.include_router(openai_router)


# ---- 根路由 & 健康检查 ----
@app.get("/", summary="根路由")
async def root():
    """根路由，返回 API 基本信息。"""
    return {"message": "LangGraph Agent API", "docs": "/docs"}

