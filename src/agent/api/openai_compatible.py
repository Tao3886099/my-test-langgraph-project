"""OpenAI 兼容接口 —— 让开源前端项目可以直接对接。

大多数开源 ChatGPT 前端都使用 OpenAI API 格式，
这里提供一个兼容层，将请求转发给 LangGraph Agent。
"""

from __future__ import annotations

import json
import uuid
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent.graph import graph
from agent.utils.log_utils import log

router = APIRouter(prefix="/v1", tags=["OpenAI 兼容接口"])


class MessageItem(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[MessageItem]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """
    兼容 OpenAI /v1/chat/completions 接口。
    开源前端项目（chatgpt-web、NextChat 等）可直接对接。
    """
    # 提取最后一条用户消息
    user_message = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        return {"error": "没有找到用户消息"}

    thread_id = str(uuid.uuid4())
    input_messages = {"messages": [HumanMessage(content=user_message)]}
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    if req.stream:
        return StreamingResponse(
            _stream_generator(input_messages, config, req.model),
            media_type="text/event-stream",
        )
    else:
        return await _non_stream(input_messages, config, req.model)


async def _non_stream(
    input_messages: dict, config: dict, model: str
) -> dict:
    """非流式响应，返回完整结果。"""
    try:
        result = await graph.ainvoke(input_messages, config=config)
        # 提取最后一条 AI 消息
        ai_content = ""
        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                ai_content = msg.content
                break

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ai_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    except Exception as e:
        log.exception(e)
        return {"error": str(e)}


async def _stream_generator(input_messages: dict, config: dict, model: str):
    """流式响应，兼容 OpenAI SSE 格式。"""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

    try:
        async for event in graph.astream_events(
            input_messages, config=config, version="v2"
        ):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk.content},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 发送结束标记
        done_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        log.exception(e)
        error_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": f"\n\n❌ 出错: {str(e)}"},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"