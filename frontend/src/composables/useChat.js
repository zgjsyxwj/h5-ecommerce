import { ref } from 'vue'

/**
 * 客服对话状态机 + SSE 消费。
 *
 * messages 是 [{ id, role, text, status }] 的列表：
 *   role: 'user' | 'assistant' | 'tool' | 'error'
 *   status (tool): 工具名（如 'lookup_orders'），完成后变 null
 */
export function useChat({ apiBase }) {
  const messages = ref([])
  const sending = ref(false)
  let lastUserMessage = ''

  function _push(msg) {
    messages.value.push({ id: crypto.randomUUID(), ...msg })
  }

  function _appendToken(text) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.text += text
    } else {
      _push({ role: 'assistant', text })
    }
  }

  function _setToolStatus(name, phase) {
    if (phase === 'start') {
      _push({ role: 'tool', text: `正在调用 ${name}…`, status: name })
    } else {
      // phase === 'end'：把最后一条 tool 状态淡化掉（移除）
      const idx = [...messages.value].reverse().findIndex(m => m.role === 'tool' && m.status === name)
      if (idx >= 0) messages.value.splice(messages.value.length - 1 - idx, 1)
    }
  }

  function _showError(text) {
    _push({ role: 'error', text })
  }

  function _parseSseChunk(buffer) {
    // 按 \n\n 切块；返回 [parsedEvents, remainder]
    const blocks = buffer.split('\n\n')
    const remainder = blocks.pop() // 最后一段可能不完整
    const events = []
    for (const block of blocks) {
      if (!block.trim()) continue
      const lines = block.split('\n')
      let event = null
      let data = null
      for (const line of lines) {
        if (line.startsWith('event: ')) event = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (event && data) {
        try {
          events.push({ event, data: JSON.parse(data) })
        } catch (e) {
          // skip malformed
        }
      }
    }
    return [events, remainder]
  }

  async function send(text, username, sessionId) {
    if (sending.value) return
    if (!text.trim()) return
    sending.value = true
    lastUserMessage = text
    _push({ role: 'user', text })

    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, username, session_id: sessionId }),
      })
      if (!res.ok) {
        _showError('服务暂时不可用，请稍后再试')
        return
      }

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += value
        const [events, remainder] = _parseSseChunk(buffer)
        buffer = remainder
        for (const { event, data } of events) {
          if (event === 'token') _appendToken(data.text || '')
          else if (event === 'tool') _setToolStatus(data.name, data.phase)
          else if (event === 'error') _showError('服务暂时不可用，请稍后再试')
          else if (event === 'done') { /* 流结束 */ }
        }
      }
    } catch (e) {
      _showError('服务暂时不可用，请稍后再试')
    } finally {
      sending.value = false
    }
  }

  function retry(username, sessionId) {
    if (lastUserMessage) send(lastUserMessage, username, sessionId)
  }

  return { messages, sending, send, retry }
}
