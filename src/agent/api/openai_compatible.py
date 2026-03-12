"""OpenAI 兼容接口 —— 让开源前端项目可以直接对接。

大多数开源 ChatGPT 前端都使用 OpenAI API 格式，
这里提供一个兼容层，将请求转发给 LangGraph Agent。

支持特性：
- 多模态消息（文本 + 图片）
- 上下文持久化（完整对话历史传递）
- 流式 / 非流式响应
"""

from __future__ import annotations

import json
import uuid
import time
import hashlib
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.graph import graph
from agent.utils.log_utils import log
from agent.env_utils import OLLAMA_MODEL_NAME

router = APIRouter(prefix="/v1", tags=["OpenAI 兼容接口"])


# ---- 多模态消息数据模型 ----

class ImageUrl(BaseModel):
    """图片 URL（支持 base64 data URI 和 http(s) 链接）。"""
    url: str
    detail: Optional[str] = None  # "auto" / "low" / "high"


class ContentPart(BaseModel):
    """OpenAI 多模态 content 的单个部分。"""
    type: str  # "text" | "image_url"
    text: Optional[str] = None
    image_url: Optional[ImageUrl] = None


class MessageItem(BaseModel):
    """兼容 OpenAI 消息格式，content 支持纯文本或多模态数组。"""
    role: str
    content: Union[str, List[ContentPart]]


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[MessageItem]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7


# ---- 消息转换工具函数 ----

def _convert_content(content: Union[str, List[ContentPart]]) -> Union[str, List[dict]]:
    """将 OpenAI 格式的 content 转换为 LangChain 格式。

    - 纯文本: 原样返回 str
    - 多模态: 转换为 LangChain 的 content list 格式
      [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]
    """
    if isinstance(content, str):
        return content

    lc_parts: List[dict] = []
    for part in content:
        if part.type == "text" and part.text is not None:
            lc_parts.append({"type": "text", "text": part.text})
        elif part.type == "image_url" and part.image_url is not None:
            img_data: Dict[str, str] = {"url": part.image_url.url}
            if part.image_url.detail:
                img_data["detail"] = part.image_url.detail
            lc_parts.append({"type": "image_url", "image_url": img_data})
    return lc_parts


def _convert_messages(messages: List[MessageItem]) -> List[Any]:
    """将 OpenAI 格式的完整对话历史转换为 LangChain 消息列表。

    支持角色: user → HumanMessage, assistant → AIMessage, system → SystemMessage
    支持内容: 纯文本 & 多模态（图片+文字）
    """
    lc_messages: List[Any] = []
    for msg in messages:
        converted = _convert_content(msg.content)
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=converted))
        elif msg.role == "assistant":
            # assistant 的 content 通常是纯文本
            text = converted if isinstance(converted, str) else str(converted)
            lc_messages.append(AIMessage(content=text))
        elif msg.role == "system":
            text = converted if isinstance(converted, str) else str(converted)
            lc_messages.append(SystemMessage(content=text))
        # tool 角色等其他角色暂不处理
    return lc_messages


def _generate_thread_id(messages: List[MessageItem]) -> str:
    """根据对话首条消息生成稳定的 thread_id。

    同一个对话（首条消息相同）会映射到同一 thread_id，
    确保 checkpointer 能正确关联上下文。
    """
    if not messages:
        return str(uuid.uuid4())
    # 用第一条消息的内容生成哈希作为稳定 ID
    first_content = messages[0].content
    if isinstance(first_content, list):
        # 多模态内容取文本部分
        text_parts = [p.text for p in first_content if p.type == "text" and p.text]
        hash_input = "|".join(text_parts) if text_parts else str(uuid.uuid4())
    else:
        hash_input = first_content
    return hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:16]


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """
    兼容 OpenAI /v1/chat/completions 接口。
    开源前端项目（Open WebUI、LobeChat、LibreChat 等）可直接对接。

    支持：
    - 多模态消息（图片 + 文字）
    - 完整上下文传递（前端发送全部历史，后端正确转发）
    - 流式 & 非流式响应
    """
    if not req.messages:
        return {"error": "消息列表不能为空"}

    # 将 OpenAI 格式消息转换为 LangChain 消息（保留完整对话历史）
    lc_messages = _convert_messages(req.messages)

    if not lc_messages:
        return {"error": "没有找到有效消息"}

    # 生成稳定的 thread_id（同一对话始终使用同一 ID）
    thread_id = _generate_thread_id(req.messages)
    input_messages = {"messages": lc_messages}
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


# ---- 模型列表接口（前端需要） ----

@router.get("/models")
async def list_models():
    """兼容 OpenAI /v1/models 接口。

    Open WebUI、LobeChat 等前端启动时会调用此接口获取可用模型列表。
    """
    return {
        "object": "list",
        "data": [
            {
                "id": OLLAMA_MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
                "permission": [],
                "root": OLLAMA_MODEL_NAME,
                "parent": None,
            }
        ],
    }