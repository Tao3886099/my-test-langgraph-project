/**
 * 多模态消息处理模块
 * 当消息包含图片时，直接调用 langgraph 后端的 OpenAI 兼容接口
 */
import * as dotenv from 'dotenv'
import fetch from 'node-fetch'
import { isNotEmptyString } from './utils/is'
import type { ImageItem } from './types'

dotenv.config()

const OPENAI_API_KEY = process.env.OPENAI_API_KEY ?? ''
const OPENAI_API_BASE_URL = process.env.OPENAI_API_BASE_URL ?? 'http://127.0.0.1:8000/v1'
const OPENAI_API_MODEL = process.env.OPENAI_API_MODEL ?? 'gpt-3.5-turbo'
const TIMEOUT_MS = !isNaN(+process.env.TIMEOUT_MS) ? +process.env.TIMEOUT_MS : 100000

interface MultimodalOptions {
  prompt: string
  images: ImageItem[]
  systemMessage?: string
  temperature?: number
  top_p?: number
  process: (text: string) => void
}

/**
 * 构建 OpenAI 多模态消息格式的 content 数组
 */
function buildMultimodalContent(prompt: string, images: ImageItem[]): any[] {
  const content: any[] = []

  // 添加图片
  for (const img of images) {
    content.push({
      type: 'image_url',
      image_url: { url: img.url },
    })
  }

  // 添加文本
  if (prompt) {
    content.push({
      type: 'text',
      text: prompt,
    })
  }

  return content
}

/**
 * 发送多模态消息到 langgraph OpenAI 兼容接口（流式）
 */
export async function sendMultimodalChat(options: MultimodalOptions): Promise<void> {
  const { prompt, images, systemMessage, temperature = 0.7, top_p = 1, process: onProcess } = options

  const apiUrl = OPENAI_API_BASE_URL.endsWith('/v1')
    ? `${OPENAI_API_BASE_URL}/chat/completions`
    : `${OPENAI_API_BASE_URL}/v1/chat/completions`

  const messages: any[] = []

  // 可选的系统消息
  if (isNotEmptyString(systemMessage)) {
    messages.push({
      role: 'system',
      content: systemMessage,
    })
  }

  // 用户消息（多模态）
  messages.push({
    role: 'user',
    content: buildMultimodalContent(prompt, images),
  })

  const body = {
    model: OPENAI_API_MODEL,
    messages,
    stream: true,
    temperature,
    top_p,
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal as any,
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API 请求失败 (${response.status}): ${errorText}`)
    }

    // 解析 SSE 流
    let fullText = ''
    const responseBody = response.body
    if (!responseBody)
      throw new Error('响应体为空')

    const decoder = new TextDecoder()
    let buffer = ''

    for await (const chunk of responseBody as any) {
      buffer += decoder.decode(chunk, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: '))
          continue

        const data = trimmed.slice(6)
        if (data === '[DONE]')
          continue

        try {
          const parsed = JSON.parse(data)
          const delta = parsed.choices?.[0]?.delta?.content
          if (delta) {
            fullText += delta
            // 按照原项目格式输出，前端通过 JSON.parse 解析最后一行
            const chatData = {
              id: parsed.id ?? '',
              conversationId: parsed.id ?? '',
              text: fullText,
              detail: {
                choices: [{ finish_reason: parsed.choices[0].finish_reason, index: 0, logprobs: null, text: '' }],
                created: parsed.created ?? Date.now(),
                id: parsed.id ?? '',
                model: parsed.model ?? OPENAI_API_MODEL,
                object: 'chat.completion.chunk',
                usage: { completion_tokens: 0, prompt_tokens: 0, total_tokens: 0 },
              },
              role: 'assistant',
              parentMessageId: '',
            }
            onProcess(`\n${JSON.stringify(chatData)}`)
          }
        }
        catch {
          // 忽略解析错误
        }
      }
    }
  }
  finally {
    clearTimeout(timeoutId)
  }
}
