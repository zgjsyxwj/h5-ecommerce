<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useChat } from '../composables/useChat.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  username: { type: String, default: '' },
  apiBase: { type: String, required: true },
})
const emit = defineEmits(['update:open'])

const { messages, sending, send, retry } = useChat({ apiBase: props.apiBase })

const inputText = ref('')
const messagesEl = ref(null)

const sessionId = computed(() => {
  let sid = sessionStorage.getItem('csr_session')
  if (!sid) {
    sid = crypto.randomUUID()
    sessionStorage.setItem('csr_session', sid)
  }
  return sid
})

function close() {
  emit('update:open', false)
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || sending.value) return
  inputText.value = ''
  await send(text, props.username, sessionId.value)
}

function handleRetry() {
  retry(props.username, sessionId.value)
}

function handleKeydown(e) {
  // Enter 发送、Shift+Enter 换行
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// 自动滚到底
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  },
)
</script>

<template>
  <transition name="panel">
    <aside v-if="open" class="csr-panel" role="dialog" aria-label="智能客服">
      <header class="csr-head">
        <span class="csr-title">智能客服</span>
        <button class="csr-close" aria-label="关闭" @click="close">×</button>
      </header>

      <div ref="messagesEl" class="csr-msgs">
        <p v-if="!messages.length" class="csr-empty">您好，请描述您的问题</p>
        <template v-for="m in messages" :key="m.id">
          <div v-if="m.role === 'user'" class="msg msg--user">
            <div class="bubble">{{ m.text }}</div>
          </div>
          <div v-else-if="m.role === 'assistant'" class="msg msg--assistant">
            <div class="bubble">{{ m.text }}</div>
          </div>
          <div v-else-if="m.role === 'tool'" class="msg msg--tool">
            <span class="tool-text">{{ m.text }}</span>
          </div>
          <div v-else-if="m.role === 'error'" class="msg msg--error">
            <span class="err-text">{{ m.text }}</span>
            <button class="err-retry" @click="handleRetry">重试</button>
          </div>
        </template>
      </div>

      <footer class="csr-foot">
        <textarea
          v-model="inputText"
          class="csr-input"
          rows="2"
          placeholder="输入消息，回车发送"
          :disabled="sending"
          @keydown="handleKeydown"
        />
        <button
          class="csr-send"
          :disabled="sending || !inputText.trim()"
          @click="handleSend"
        >
          {{ sending ? '发送中…' : '发送' }}
        </button>
      </footer>
    </aside>
  </transition>
</template>

<style scoped>
.csr-panel {
  position: fixed;
  top: 0; right: 0; bottom: 0;
  width: 360px;
  max-width: 100vw;
  background: var(--surface);
  border-left: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  z-index: 25;
  box-shadow: -16px 0 36px -16px rgba(20, 24, 32, 0.18);
}

.csr-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--rule);
}
.csr-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--ink);
  letter-spacing: -0.005em;
}
.csr-close {
  width: 28px; height: 28px;
  font-size: 18px;
  color: var(--ink-3);
  border-radius: 4px;
  transition: background 120ms var(--ease-out), color 120ms var(--ease-out);
}
.csr-close:hover { background: var(--paper); color: var(--ink); }

.csr-msgs {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex; flex-direction: column; gap: 10px;
  font-size: 13.5px;
  line-height: 1.55;
}
.csr-empty {
  color: var(--ink-3);
  text-align: center;
  padding: 32px 16px;
  font-size: 13px;
}

.msg { display: flex; }
.msg--user { justify-content: flex-end; }
.msg--assistant { justify-content: flex-start; }
.msg--tool, .msg--error {
  justify-content: center;
  font-size: 12px;
}

.bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg--user .bubble {
  background: var(--ink);
  color: var(--paper);
}
.msg--assistant .bubble {
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--rule);
}

.tool-text {
  color: var(--ink-3);
  font-style: italic;
}
.err-text {
  color: oklch(48% 0.16 25); /* 沉稳红 */
  margin-right: 8px;
}
.err-retry {
  font-size: 12px;
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.csr-foot {
  border-top: 1px solid var(--rule);
  padding: 12px 14px;
  display: flex; gap: 8px; align-items: stretch;
}
.csr-input {
  flex: 1;
  resize: none;
  border: 1px solid var(--rule);
  background: var(--paper);
  border-radius: 4px;
  padding: 8px 10px;
  color: var(--ink);
  outline: none;
  font: inherit;
  transition: border-color 120ms var(--ease-out);
}
.csr-input:focus { border-color: var(--accent); }
.csr-input:disabled { opacity: 0.6; }

.csr-send {
  background: var(--accent);
  color: var(--paper);
  font-size: 13px;
  font-weight: 500;
  padding: 0 14px;
  border-radius: 4px;
  transition: opacity 120ms var(--ease-out);
}
.csr-send:disabled { opacity: 0.4; cursor: not-allowed; }

.panel-enter-active, .panel-leave-active {
  transition: transform 260ms var(--ease-out);
}
.panel-enter-from, .panel-leave-to {
  transform: translateX(100%);
}

@media (max-width: 480px) {
  .csr-panel { width: 100%; }
}
</style>
