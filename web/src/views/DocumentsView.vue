<template>
  <section class="workspace">
    <header>
      <p class="workspace__eyebrow">CampusAI · 资料解析</p>
      <h1 class="workspace__title">把资料读成你能用的笔记</h1>
      <p class="workspace__desc">
        上传 PDF、Word 或 PPT，自动提取文本、生成摘要与提纲，并可以针对文档内容提问。
        原始文件按账号隔离存放，只有你自己能访问。
      </p>
    </header>

    <div class="workspace__body">
      <aside class="panel">
        <div class="panel__head">
          <h2 class="panel__title">我的资料</h2>
          <label class="ui-btn ui-btn--sm" :class="{ 'is-disabled': uploading }">
            {{ uploading ? '解析中…' : '上传文件' }}
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.docx,.pptx"
              hidden
              :disabled="uploading"
              @change="handleFileChange"
            />
          </label>
        </div>
        <p class="panel__hint">支持 PDF / Word(docx) / PPT(pptx)，单个不超过 30MB。</p>
        <p v-if="!documents.length && !listLoading" class="empty">
          还没有上传资料。点击右上角「上传文件」开始。
        </p>
        <div v-else class="doc-list">
          <button
            v-for="item in documents"
            :key="item.document_id"
            class="doc-item"
            :class="{ 'is-active': item.document_id === selectedId }"
            type="button"
            @click="selectDocument(item)"
          >
            <span>
              <span class="doc-item__name">{{ item.filename }}</span>
              <span class="doc-item__meta">{{ formatSize(item.size) }} · {{ formatTime(item.created_at) }}</span>
            </span>
            <span class="status-pill" :class="`status-pill--${item.status}`">
              {{ statusLabel(item.status) }}
            </span>
          </button>
        </div>
      </aside>

      <main>
        <p v-if="error" class="alert alert--error">{{ error }}</p>
        <p v-if="uploadMessage" class="alert" :class="uploadMessage.kind === 'error' ? 'alert--error' : 'alert--ok'">
          {{ uploadMessage.text }}
        </p>

        <section v-if="summary" class="panel">
          <div class="panel__head">
            <h2 class="panel__title">{{ summary.filename }}</h2>
            <div class="toolbar">
              <button
                v-if="summary.status === 'ready'"
                class="ui-btn ui-btn--sm"
                type="button"
                @click="handleExport"
              >
                导出摘要
              </button>
            </div>
          </div>

          <div class="progress" style="margin-bottom: 8px">
            <div class="progress__bar" :style="{ width: `${summary.progress ?? 0}%` }" />
          </div>
          <p class="panel__hint">
            解析进度 {{ summary.progress ?? 0 }}% · 状态 {{ statusLabel(summary.status) }}
          </p>

          <p v-if="summary.status_message" class="alert alert--error" style="margin-top: 12px">
            {{ summary.status_message }}
          </p>

          <template v-if="summary.status === 'ready'">
            <h3 class="ui-label" style="margin-top: 18px">摘要</h3>
            <p class="result-card__snippet">{{ summary.summary || '暂无摘要。' }}</p>

            <template v-if="summary.outline && summary.outline.length">
              <h3 class="ui-label" style="margin-top: 18px">提纲</h3>
              <ol class="outline-list">
                <li v-for="(item, index) in summary.outline" :key="index">
                  {{ item.title }}
                  <template v-if="item.page">（第 {{ item.page }} 页）</template>
                </li>
              </ol>
            </template>

            <h3 class="ui-label" style="margin-top: 22px">针对文档提问</h3>
            <form class="composer" @submit.prevent="handleAsk">
              <textarea
                v-model="question"
                class="ui-textarea"
                placeholder="例如：这份资料的核心结论是什么？"
                @keydown.enter.exact.prevent="handleAsk"
              />
              <div class="composer__actions">
                <span class="panel__hint">回答只依据本文档内容，并标注页码。</span>
                <button class="ui-btn ui-btn--primary" type="submit" :disabled="asking || !question.trim()">
                  {{ asking ? '查找中…' : '提问' }}
                </button>
              </div>
            </form>

            <div v-if="answer" class="alert" :class="answer.refusal ? 'alert--error' : 'alert--ok'" style="margin-top: 14px">
              <p style="white-space: pre-wrap; margin: 0">{{ answer.answer }}</p>
            </div>
            <div v-if="answer && answer.sources.length" class="msg__sources">
              <span v-for="(source, index) in answer.sources" :key="index" class="chip">
                {{ source.title }}
                <template v-if="source.page"> · 第 {{ source.page }} 页</template>
              </span>
            </div>
          </template>
        </section>

        <p v-else-if="!selectedId && !listLoading" class="empty">
          从左侧选择一份资料查看摘要，或先上传一份。
        </p>
      </main>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import {
  askDocument,
  downloadDocumentSummary,
  fetchDocumentSummary,
  fetchDocuments,
  uploadDocument,
} from '@/api/documents'

const documents = ref([])
const selectedId = ref(null)
const summary = ref(null)
const listLoading = ref(true)
const uploading = ref(false)
const asking = ref(false)
const question = ref('')
const answer = ref(null)
const error = ref('')
const uploadMessage = ref(null)
const fileInput = ref(null)

const STATUS_LABELS = {
  uploaded: '待解析',
  parsing: '解析中',
  ready: '可阅读',
  failed: '解析失败',
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatSize(size) {
  if (!size) return '0 B'
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
  if (size >= 1024) return `${Math.round(size / 1024)} KB`
  return `${size} B`
}

async function loadDocuments() {
  listLoading.value = true
  try {
    documents.value = await fetchDocuments()
  } catch (err) {
    error.value = err.message
  } finally {
    listLoading.value = false
  }
}

async function selectDocument(item) {
  selectedId.value = item.document_id
  answer.value = null
  question.value = ''
  error.value = ''
  try {
    summary.value = await fetchDocumentSummary(item.document_id)
  } catch (err) {
    error.value = err.message
    summary.value = null
  }
}

async function handleFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  uploading.value = true
  error.value = ''
  uploadMessage.value = null
  try {
    const result = await uploadDocument(file)
    await loadDocuments()
    if (result.status === 'failed') {
      uploadMessage.value = {
        kind: 'error',
        text: result.status_message || '文件解析失败，请检查文件后重试。',
      }
    } else {
      uploadMessage.value = {
        kind: 'ok',
        text: `《${result.filename}》解析完成，已生成摘要与 ${result.pages} 个页面的提纲。`,
      }
    }
    const item = documents.value.find((doc) => doc.document_id === result.document_id)
    if (item) await selectDocument(item)
  } catch (err) {
    uploadMessage.value = { kind: 'error', text: err.message }
  } finally {
    uploading.value = false
  }
}

async function handleExport() {
  if (!summary.value) return
  try {
    await downloadDocumentSummary(summary.value.document_id)
  } catch (err) {
    error.value = err.message
  }
}

async function handleAsk() {
  const text = question.value.trim()
  if (!text || asking.value || !selectedId.value) return
  asking.value = true
  error.value = ''
  answer.value = null
  try {
    answer.value = await askDocument(selectedId.value, text)
  } catch (err) {
    error.value = err.message
  } finally {
    asking.value = false
  }
}

onMounted(async () => {
  await loadDocuments()
  if (documents.value.length) await selectDocument(documents.value[0])
})
</script>
