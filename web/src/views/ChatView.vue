<template>
  <section class="workspace">
    <header>
      <p class="workspace__eyebrow">CampusAI · 学习助手</p>
      <h1 class="workspace__title">一个随时在学的 AI 队友</h1>
      <p class="workspace__desc">
        自由问答、复习计划、概念解释与思路点拨四种模式。未接入模型时会给出可执行的通用建议，
        接入模型后则以你自己的额度生成个性化回答。
      </p>
    </header>

    <div class="workspace__body">
      <aside class="panel">
        <div class="panel__head">
          <h2 class="panel__title">学习会话</h2>
          <button class="ui-btn ui-btn--sm" type="button" @click="startNew">新对话</button>
        </div>
        <p v-if="!sessions.length && !sessionsLoading" class="empty">
          还没有会话。发送第一条消息即可创建。
        </p>
        <ul v-else class="session-list">
          <li v-for="item in sessions" :key="item.id">
            <button
              class="session-item"
              :class="{ 'is-active': item.id === sessionId }"
              type="button"
              @click="openSession(item.id)"
            >
              <span class="session-item__title">{{ item.title || '未命名会话' }}</span>
              <span class="session-item__time">{{ formatTime(item.updated_at) }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <main class="panel">
        <div class="toolbar" style="margin-bottom: 14px">
          <label class="ui-label" for="chat-template" style="margin: 0">模式</label>
          <select id="chat-template" v-model="template" class="ui-select" style="width: auto">
            <option v-for="item in templates" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
          <span class="panel__hint">{{ currentTemplateHint }}</span>
        </div>

        <div ref="threadEl" class="chat-thread">
          <p v-if="!messages.length" class="empty">
            告诉小智你正在学什么、卡在哪里，它会按所选模式给出回答。
          </p>
          <article
            v-for="(item, index) in messages"
            :key="index"
            class="msg"
            :class="`msg--${item.role}`"
          >
            <p class="msg__meta">{{ item.role === 'user' ? '我' : '小智' }}</p>
            <p class="msg__body">{{ item.content }}</p>
          </article>
          <p v-if="loading" class="empty">小智正在思考…</p>
        </div>

        <p v-if="error" class="alert alert--error">{{ error }}</p>
        <p v-if="engineHint" class="alert" role="status">{{ engineHint }}</p>

        <form class="composer" @submit.prevent="send">
          <textarea
            v-model="content"
            class="ui-textarea"
            placeholder="例如：帮我排一份两周的高数复习计划"
            @keydown.enter.exact.prevent="send"
          />
          <div class="composer__actions">
            <span class="panel__hint">Enter 发送，Shift + Enter 换行</span>
            <button class="ui-btn ui-btn--primary" type="submit" :disabled="loading || !content.trim()">
              {{ loading ? '发送中…' : '发送' }}
            </button>
          </div>
        </form>
      </main>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

import {
  createChatSession,
  fetchChatMessages,
  fetchChatSessions,
  sendChatMessage,
} from '@/api/chat'

const templates = [
  { value: 'free', label: '自由问答', hint: '就学习中的疑问继续追问。' },
  { value: 'plan', label: '复习计划', hint: '按科目与时间生成可执行的复习节奏。' },
  { value: 'concept', label: '概念解释', hint: '用类比与分步解释讲清抽象概念。' },
  { value: 'hint', label: '思路点拨', hint: '给方向不给答案，保留思考过程。' },
]

const sessions = ref([])
const sessionId = ref(null)
const messages = ref([])
const content = ref('')
const template = ref('free')
const loading = ref(false)
const sessionsLoading = ref(true)
const error = ref('')
const engineHint = ref('')
const threadEl = ref(null)

const currentTemplateHint = computed(
  () => templates.find((item) => item.value === template.value)?.hint || '',
)

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

async function scrollToEnd() {
  await nextTick()
  if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
}

async function loadSessions() {
  sessionsLoading.value = true
  try {
    sessions.value = await fetchChatSessions()
  } catch (err) {
    error.value = err.message
  } finally {
    sessionsLoading.value = false
  }
}

async function openSession(id) {
  sessionId.value = id
  error.value = ''
  try {
    messages.value = await fetchChatMessages(id)
    await scrollToEnd()
  } catch (err) {
    error.value = err.message
  }
}

function startNew() {
  sessionId.value = null
  messages.value = []
  error.value = ''
  engineHint.value = ''
}

async function send() {
  const text = content.value.trim()
  if (!text || loading.value) return
  loading.value = true
  error.value = ''
  engineHint.value = ''
  try {
    if (!sessionId.value) {
      const session = await createChatSession()
      sessionId.value = session.id
    }
    const result = await sendChatMessage(sessionId.value, text, template.value)
    messages.value.push({ role: 'user', content: text })
    messages.value.push({ role: 'assistant', content: result.reply })
    if (result.engine === 'offline') {
      engineHint.value = '当前未接入大模型，以上为离线通用建议；在「模型接入」中配置后即可获得个性化回答。'
    }
    content.value = ''
    await Promise.all([loadSessions(), scrollToEnd()])
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length) await openSession(sessions.value[0].id)
})
</script>
