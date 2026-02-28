"""请求与响应数据模型。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---- 聊天相关 ----

class ChatRequest(BaseModel):
    """聊天请求体。"""

    message: str = Field(..., description="用户发送的消息内容", examples=["数据库里有多少张表？"])
    thread_id: Optional[str] = Field(None, description="会话线程 ID，不传则创建新会话")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文配置参数")


class ChatMessage(BaseModel):
    """单条消息。"""

    role: str = Field(..., description="消息角色: user / assistant / tool")
    content: str = Field(..., description="消息内容")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用信息（仅 assistant 角色可能有）")


class ChatResponse(BaseModel):
    """聊天响应体。"""

    thread_id: str = Field(..., description="会话线程 ID")
    messages: List[ChatMessage] = Field(..., description="本轮新增的消息列表")


# ---- 会话管理 ----

class ThreadInfo(BaseModel):
    """会话线程信息。"""

    thread_id: str = Field(..., description="会话线程 ID")
    created_at: str = Field(..., description="创建时间")
    message_count: int = Field(0, description="消息数量")


class ThreadListResponse(BaseModel):
    """会话列表响应。"""

    threads: List[ThreadInfo] = Field(..., description="会话线程列表")


class HistoryResponse(BaseModel):
    """历史消息响应。"""

    thread_id: str
    messages: List[ChatMessage]


# ---- 通用 ----

class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = "ok"
    version: str = "0.0.1"
