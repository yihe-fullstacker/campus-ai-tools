<template>
  <section class="workspace">
    <header>
      <p class="workspace__eyebrow">CampusAI · 资源搜索</p>
      <h1 class="workspace__title">一次搜索，跨源查找</h1>
      <p class="workspace__desc">
        同时检索校园知识库、共享资料与我的资料。知识库只展示已核对本校官方资料的内容，
        未核实的候选条目不进入搜索结果。
      </p>
    </header>

    <form class="panel" style="margin-top: 26px" @submit.prevent="handleSearch(1)">
      <div class="toolbar">
        <input
          v-model="query"
          class="ui-input"
          style="flex: 1 1 280px"
          type="search"
          placeholder="输入关键词，例如：缓考、宿舍报修、奖学金"
        />
        <select v-model="scope" class="ui-select" style="width: auto">
          <option v-for="item in scopes" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
        <select v-model="type" class="ui-select" style="width: auto">
          <option value="">全部类型</option>
          <option v-for="item in types" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
        <button class="ui-btn ui-btn--primary" type="submit" :disabled="loading || !query.trim()">
          {{ loading ? '搜索中…' : '搜索' }}
        </button>
      </div>
    </form>

    <p v-if="error" class="alert alert--error" style="margin-top: 16px">{{ error }}</p>

    <div v-if="searched" class="panel" style="margin-top: 18px">
      <div class="panel__head">
        <h2 class="panel__title">搜索结果 · {{ total }} 条</h2>
        <span class="panel__hint">
          知识库 {{ counts.kb }} · 我的资料 {{ counts.mine }} · 共享资料 {{ counts.shared }}
        </span>
      </div>

      <p v-if="!results.length" class="empty">
        没有找到匹配内容。可以换一个关键词，或先在「资料解析」中上传自己的资料。
      </p>
      <div v-else class="results">
        <article v-for="item in results" :key="`${item.source}-${item.id}-${item.chunk_id || ''}`" class="result-card">
          <p class="result-card__meta">
            <span class="chip">{{ sourceLabel(item.source) }}</span>
            <span class="chip">{{ typeLabel(item.type) }}</span>
            <span v-if="item.evidence" class="chip chip--ok">{{ item.evidence }} 官方证据</span>
            <span v-if="item.page" class="chip">第 {{ item.page }} 页</span>
            <span v-if="item.section_title" class="chip">{{ item.section_title }}</span>
          </p>
          <h3 class="result-card__title">{{ item.title }}</h3>
          <p class="result-card__snippet">{{ item.snippet || '（无摘要片段）' }}</p>
        </article>
      </div>

      <div v-if="total > pageSize" class="toolbar" style="margin-top: 16px; justify-content: flex-end">
        <button class="ui-btn ui-btn--sm" type="button" :disabled="page <= 1 || loading" @click="handleSearch(page - 1)">
          上一页
        </button>
        <span class="panel__hint">第 {{ page }} / {{ Math.ceil(total / pageSize) }} 页</span>
        <button
          class="ui-btn ui-btn--sm"
          type="button"
          :disabled="page >= Math.ceil(total / pageSize) || loading"
          @click="handleSearch(page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

import { searchResources } from '@/api/search'

const scopes = [
  { value: 'all', label: '全部来源' },
  { value: 'kb', label: '校园知识库' },
  { value: 'mine', label: '我的资料' },
  { value: 'shared', label: '共享资料' },
]

const types = [
  { value: 'faq', label: '问答' },
  { value: 'doc', label: '文档' },
  { value: 'slide', label: '课件' },
]

const query = ref('')
const scope = ref('all')
const type = ref('')
const results = ref([])
const counts = ref({ kb: 0, mine: 0, shared: 0 })
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searched = ref(false)
const error = ref('')

const SOURCE_LABELS = { kb: '知识库', mine: '我的资料', shared: '共享资料' }
const TYPE_LABELS = { faq: '问答', doc: '文档', slide: '课件' }

function sourceLabel(value) {
  return SOURCE_LABELS[value] || value
}

function typeLabel(value) {
  return TYPE_LABELS[value] || value
}

async function handleSearch(targetPage = 1) {
  const text = query.value.trim()
  if (!text || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await searchResources({
      q: text,
      scope: scope.value,
      type: type.value,
      page: targetPage,
      pageSize: pageSize.value,
    })
    results.value = data.results
    counts.value = data.counts
    total.value = data.total
    page.value = data.page
    pageSize.value = data.page_size
    searched.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>
