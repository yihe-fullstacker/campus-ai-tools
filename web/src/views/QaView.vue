<template>
  <section class="workspace">
    <header>
      <p class="workspace__eyebrow">CampusAI · 校园问答</p>
      <h1 class="workspace__title">把校园问题交给小智</h1>
      <p class="workspace__desc">
        办事流程、教务规定、校园生活的问题都可以直接问。命中知识库时附上来源；
        尚未核实的条目会明确标注，并提醒以学校官方通知为准。
      </p>
    </header>

    <div class="workspace__body">
      <aside class="panel">
        <div class="panel__head">
          <h2 class="panel__title">问答会话</h2>
          <button class="ui-btn ui-btn--sm" type="button" @click="startNew">新对话</button>
        </div>
        <p v-if="!sessions.length && !sessionsLoading" class="empty">
          还没有会话。输入问题后会自动创建。
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
        <div ref="threadEl" class="chat-thread">
          <p v-if="!messages.length" class="empty">
            可以直接提问，例如「缓考怎么申请」「宿舍报修找哪个部门」。
          </p>
          <article
            v-for="(item, index) in messages"
            :key="index"
            class="msg"
            :class="`msg--${item.role}`"
          >
            <p class="msg__meta">{{ item.role === 'user' ? '我' : '小智' }}</p>
            <p class="msg__body">{{ item.content }}</p>
            <div v-if="item.verified !== undefined || item.sourceType" class="msg__sources">
              <span v-if="item.verified === true" class="chip chip--ok">已核实</span>
              <span v-else-if="item.verified === false" class="chip chip--warn">仅供参考</span>
              <span v-if="item.sourceType === 'general_fallback'" class="chip">通用回答</span>
              <span v-if="item.sourceType === 'refusal'" class="chip chip--warn">已拒答</span>
            </div>
            <div v-if="item.sources && item.sources.length" class="msg__sources">
              <span v-for="(source, sourceIndex) in item.sources" :key="sourceIndex" class="chip">
                {{ source.title || source.id }}
                <template v-if="source.evidence"> · {{ source.evidence }}</template>
              </span>
            </div>
          </article>
          <p v-if="loading" class="empty">小智正在整理答案…</p>
        </div>

        <p v-if="error" class="alert alert--error">{{ error }}</p>

        <form class="composer" @submit.prevent="send">
          <textarea
            v-model="question"
            class="ui-textarea"
            placeholder="例如：缓考怎么申请？"
            @keydown.enter.exact.prevent="send"
          />
          <div class="composer__actions">
            <span class="panel__hint">Enter 发送，Shift + Enter 换行</span>
            <button class="ui-btn ui-btn--primary" type="submit" :disabled="loading || !question.trim()">
              {{ loading ? '发送中…' : '发送' }}
            </button>
          </div>
        </form>
      </main>
    </div>
  </section>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'

import { askQuestion, fetchQaMessages, fetchQaSessions } from '@/api/qa'

const sessions = ref([])
const sessionId = ref(null)
const messages = ref([])
const question = ref('')
const loading = ref(false)
const sessionsLoading = ref(true)
const error = ref('')
const threadEl = ref(null)

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
    sessions.value = await fetchQaSessions()
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
    messages.value = await fetchQaMessages(id)
    await scrollToEnd()
  } catch (err) {
    error.value = err.message
  }
}

function startNew() {
  sessionId.value = null
  messages.value = []
  error.value = ''
}

async function send() {
  const text = question.value.trim()
  if (!text || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await askQuestion(text, sessionId.value)
    sessionId.value = result.session_id
    messages.value.push({ role: 'user', content: text })
    messages.value.push({
      role: 'assistant',
      content: result.answer,
      sources: result.sources || [],
      verified: result.verified,
      sourceType: result.source_type,
    })
    question.value = ''
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
