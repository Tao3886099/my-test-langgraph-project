"""聊天路由 —— 核心对话接口。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
)
from agent.graph import graph
from agent.utils.log_utils import log

router = APIRouter(prefix="/chat", tags=["聊天"])

# 简易内存会话存储（生产环境可替换为 Redis / 数据库）
_thread_store: Dict[str, Dict[str, Any]] = {}


def _get_or_create_thread(thread_id: str | None) -> str:
    """获取已有会话或创建新会话，返回 thread_id。"""
    if thread_id and thread_id in _thread_store:
        return thread_id
    new_id = thread_id or str(uuid.uuid4())
    _thread_store[new_id] = {
        "created_at": datetime.now().isoformat(),
        "messages": [],
    }
    return new_id


def _msg_to_schema(msg: Any) -> ChatMessage | None:
    """将 LangChain 消息对象转为响应模型。"""
    if isinstance(msg, HumanMessage):
        return ChatMessage(role="user", content=msg.content)
    if isinstance(msg, AIMessage):
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {"name": tc["name"], "args": tc["args"], "id": tc.get("id")}
                for tc in msg.tool_calls
            ]
        return ChatMessage(role="assistant", content=msg.content, tool_calls=tool_calls)
    if isinstance(msg, ToolMessage):
        return ChatMessage(role="tool", content=msg.content)
    return None


@router.post("", response_model=ChatResponse, summary="发送消息并获取回复")
async def chat(req: ChatRequest):
    """接收用户消息，调用 LangGraph Agent，返回完整回复。"""
    thread_id = _get_or_create_thread(req.thread_id)

    # 构建输入
    input_messages = {"messages": [HumanMessage(content=req.message)]}

    # 可选的上下文配置
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if req.context:
        config["configurable"]["my_configurable_param"] = req.context.get(
            "my_configurable_param", ""
        )

    try:
        # 调用图（异步）
        result = await graph.ainvoke(input_messages, config=config)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=f"Agent 调用失败: {str(e)}")

    # 从结果中提取新消息
    new_messages: list[ChatMessage] = []
    for msg in result.get("messages", []):
        schema_msg = _msg_to_schema(msg)
        if schema_msg:
            new_messages.append(schema_msg)

    # 保存到会话存储
    _thread_store[thread_id]["messages"].extend(new_messages)

    return ChatResponse(thread_id=thread_id, messages=new_messages)


@router.post("/stream", summary="流式发送消息并获取回复")
async def chat_stream(req: ChatRequest):
    """流式接口 —— 逐步返回 Agent 的响应（SSE 格式）。"""
    import json

    thread_id = _get_or_create_thread(req.thread_id)
    input_messages = {"messages": [HumanMessage(content=req.message)]}
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if req.context:
        config["configurable"]["my_configurable_param"] = req.context.get(
            "my_configurable_param", ""
        )

    async def event_generator():
        try:
            async for event in graph.astream_events(input_messages, config=config, version="v2"):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        payload = json.dumps(
                            {"type": "token", "content": chunk.content},
                            ensure_ascii=False,
                        )
                        yield f"data: {payload}\n\n"
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    payload = json.dumps(
                        {"type": "tool_start", "tool": tool_name},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = str(event.get("data", {}).get("output", ""))
                    payload = json.dumps(
                        {"type": "tool_end", "tool": tool_name, "output": output[:500]},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
            # 结束标记
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            log.exception(e)
            error_payload = json.dumps(
                {"type": "error", "message": str(e)}, ensure_ascii=False
            )
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/history/{thread_id}",
    response_model=HistoryResponse,
    summary="获取会话历史",
)
async def get_history(thread_id: str):
    """获取指定会话的历史消息。"""
    if thread_id not in _thread_store:
        raise HTTPException(status_code=404, detail="会话不存在")
    return HistoryResponse(
        thread_id=thread_id,
        messages=_thread_store[thread_id]["messages"],
    )


@router.get("/threads", summary="获取所有会话列表")
async def list_threads():
    """列出所有会话。"""
    from agent.api.schemas import ThreadInfo, ThreadListResponse

    threads = [
        ThreadInfo(
            thread_id=tid,
            created_at=data["created_at"],
            message_count=len(data["messages"]),
        )
        for tid, data in _thread_store.items()
    ]
    return ThreadListResponse(threads=threads)


@router.delete("/threads/{thread_id}", summary="删除会话")
async def delete_thread(thread_id: str):
    """删除指定会话。"""
    if thread_id not in _thread_store:
        raise HTTPException(status_code=404, detail="会话不存在")
    del _thread_store[thread_id]
    return {"message": "会话已删除", "thread_id": thread_id}
