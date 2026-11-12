<template>
  <section class="workspace">
    <header>
      <p class="workspace__eyebrow">CampusAI · 知识库</p>
      <h1 class="workspace__title">知识库由管理员维护</h1>
      <p class="workspace__desc">
        知识库是校园问答的唯一业务数据源。所有写入都要经过统一入口，
        证据等级 E3→E2→E1 的升级由人工触发，不会自动执行。
      </p>
    </header>

    <div v-if="!isAdmin" class="panel" style="margin-top: 26px">
      <p class="alert">
        该页面仅限管理员访问。当前账号为普通学生账号，可以正常使用校园问答、学习助手、
        资料解析与资源搜索。
      </p>
    </div>

    <template v-else>
      <p v-if="error" class="alert alert--error" style="margin-top: 22px">{{ error }}</p>
      <p v-if="notice" class="alert alert--ok" style="margin-top: 22px">{{ notice }}</p>

      <div class="workspace__body" style="margin-top: 22px">
        <aside class="panel">
          <div class="panel__head">
            <h2 class="panel__title">条目</h2>
            <button class="ui-btn ui-btn--sm" type="button" @click="startCreate">新增</button>
          </div>
          <label class="ui-field">
            <span class="ui-label">状态筛选</span>
            <select v-model="statusFilter" class="ui-select" @change="loadItems(1)">
              <option value="">全部状态</option>
              <option v-for="item in statuses" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>
          <p class="panel__hint">共 {{ total }} 条，按优先级排序。</p>
          <p v-if="!items.length && !loading" class="empty">当前筛选下没有条目。</p>
          <ul class="session-list" style="max-height: 52vh">
            <li v-for="item in items" :key="item.id">
              <button
                class="session-item"
                :class="{ 'is-active': item.id === editingId }"
                type="button"
                @click="startEdit(item)"
              >
                <span class="session-item__title">{{ item.question }}</span>
                <span class="session-item__time">
                  {{ item.category }} · {{ item.priority }} · {{ item.evidence }} · {{ statusLabel(item.status) }}
                </span>
              </button>
            </li>
          </ul>
          <div v-if="total > pageSize" class="toolbar" style="margin-top: 12px; justify-content: space-between">
            <button class="ui-btn ui-btn--sm" type="button" :disabled="page <= 1" @click="loadItems(page - 1)">
              上一页
            </button>
            <span class="panel__hint">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
            <button
              class="ui-btn ui-btn--sm"
              type="button"
              :disabled="page >= Math.ceil(total / pageSize)"
              @click="loadItems(page + 1)"
            >
              下一页
            </button>
          </div>
        </aside>

        <main>
          <section class="panel">
            <div class="panel__head">
              <h2 class="panel__title">{{ editingId ? `编辑条目 #${editingId}` : '录入新条目' }}</h2>
              <button v-if="editingId" class="ui-btn ui-btn--sm" type="button" @click="startCreate">
                取消编辑
              </button>
            </div>

            <form @submit.prevent="submitItem">
              <label class="ui-field">
                <span class="ui-label">标准问法 *</span>
                <input v-model="form.question" class="ui-input" required maxlength="500" />
              </label>

              <label class="ui-field">
                <span class="ui-label">同义问法（用逗号分隔）</span>
                <input v-model="form.aliases" class="ui-input" placeholder="怎么办理缓考，缓考流程" />
              </label>

              <label class="ui-field">
                <span class="ui-label">回答要点（Markdown）</span>
                <textarea v-model="form.answer" class="ui-textarea" rows="4" />
              </label>

              <div class="form-grid">
                <label class="ui-field">
                  <span class="ui-label">一级分类 *</span>
                  <input v-model="form.category" class="ui-input" required placeholder="S1–S5" />
                </label>
                <label class="ui-field">
                  <span class="ui-label">二级分类</span>
                  <input v-model="form.subcategory" class="ui-input" />
                </label>
                <label class="ui-field">
                  <span class="ui-label">优先级</span>
                  <select v-model="form.priority" class="ui-select">
                    <option v-for="value in ['P0', 'P1', 'P2']" :key="value" :value="value">{{ value }}</option>
                  </select>
                </label>
                <label class="ui-field">
                  <span class="ui-label">证据等级</span>
                  <select v-model="form.evidence" class="ui-select">
                    <option v-for="value in ['E1', 'E2', 'E3']" :key="value" :value="value">{{ value }}</option>
                  </select>
                </label>
                <label class="ui-field">
                  <span class="ui-label">状态</span>
                  <select v-model="form.status" class="ui-select">
                    <option v-for="item in statuses" :key="item.value" :value="item.value">{{ item.label }}</option>
                  </select>
                </label>
                <label class="ui-field">
                  <span class="ui-label">语料编号</span>
                  <input v-model="form.legacy_id" class="ui-input" placeholder="Q-S3-001" />
                </label>
              </div>

              <label class="ui-field">
                <span class="ui-label">证据来源 / 官方文件</span>
                <input v-model="form.source_doc" class="ui-input" placeholder="文件名或 URL（E2 升级时填写）" />
              </label>

              <p class="panel__hint">
                E3 为未核实通用建议，只能停留在候选状态；标记为已核实/已发布时必须使用 E1 或 E2。
              </p>

              <div class="toolbar" style="margin-top: 14px">
                <button class="ui-btn ui-btn--primary" type="submit" :disabled="saving">
                  {{ saving ? '保存中…' : editingId ? '保存修改' : '创建条目' }}
                </button>
                <button
                  v-if="editingId"
                  class="ui-btn ui-btn--danger"
                  type="button"
                  :disabled="saving"
                  @click="retireItem"
                >
                  下架条目
                </button>
              </div>
            </form>
          </section>

          <section class="panel">
            <div class="panel__head">
              <h2 class="panel__title">批量导入语料</h2>
              <span class="panel__hint">粘贴 JSON 数组；已存在的语料编号会自动跳过。</span>
            </div>
            <textarea
              v-model="importText"
              class="ui-textarea"
              rows="5"
              placeholder='[{"question":"缓考怎么申请","category":"S3","legacy_id":"Q-S3-001"}]'
            />
            <div class="toolbar" style="margin-top: 10px">
              <button class="ui-btn" type="button" :disabled="importing" @click="importItems">
                {{ importing ? '导入中…' : '导入' }}
              </button>
            </div>
          </section>
        </main>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import {
  createKbItem,
  fetchKbItems,
  importKbItems,
  retireKbItem,
  updateKbItem,
} from '@/api/kb'
import { useAuthStore } from '@/stores/auth'

const statuses = [
  { value: 'candidate', label: '候选' },
  { value: 'verified', label: '已核实' },
  { value: 'published', label: '已发布' },
  { value: 'retired', label: '已下架' },
]

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const editingId = ref(null)
const importText = ref('')
const error = ref('')
const notice = ref('')

const form = reactive(blankForm())

function blankForm() {
  return {
    question: '',
    aliases: '',
    answer: '',
    category: '',
    subcategory: '',
    priority: 'P2',
    evidence: 'E3',
    status: 'candidate',
    legacy_id: '',
    source_doc: '',
  }
}

function statusLabel(value) {
  return statuses.find((item) => item.value === value)?.label || value
}

function applyForm(item) {
  form.question = item.question || ''
  form.aliases = (item.aliases || []).join('，')
  form.answer = item.answer || ''
  form.category = item.category || ''
  form.subcategory = item.subcategory || ''
  form.priority = item.priority || 'P2'
  form.evidence = item.evidence || 'E3'
  form.status = item.status || 'candidate'
  form.legacy_id = item.legacy_id || ''
  form.source_doc = item.source_doc || ''
}

function resetForm() {
  Object.assign(form, blankForm())
  editingId.value = null
  error.value = ''
}

function startCreate() {
  resetForm()
  notice.value = ''
}

function startEdit(item) {
  editingId.value = item.id
  applyForm(item)
  error.value = ''
  notice.value = ''
}

function splitAliases(value) {
  return value
    .split(/[,，\n]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

function buildPayload() {
  const payload = {
    question: form.question.trim(),
    aliases: splitAliases(form.aliases),
    answer: form.answer.trim(),
    category: form.category.trim(),
    priority: form.priority,
    evidence: form.evidence,
    status: form.status,
    subcategory: form.subcategory.trim() || null,
    legacy_id: form.legacy_id.trim() || null,
    source_doc: form.source_doc.trim() || null,
  }
  return payload
}

async function loadItems(targetPage = 1) {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchKbItems({
      status: statusFilter.value,
      page: targetPage,
      pageSize: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
    page.value = data.page
    pageSize.value = data.page_size
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function submitItem() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    if (editingId.value) {
      await updateKbItem(editingId.value, buildPayload())
      notice.value = '条目已更新。'
    } else {
      await createKbItem(buildPayload())
      notice.value = '条目已创建。'
    }
    resetForm()
    await loadItems(page.value)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function retireItem() {
  if (!editingId.value) return
  if (!window.confirm('确定下架该条目吗？下架后不会再被问答与搜索命中。')) return
  saving.value = true
  error.value = ''
  try {
    await retireKbItem(editingId.value)
    notice.value = '条目已下架。'
    await loadItems(page.value)
    resetForm()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function importItems() {
  importing.value = true
  error.value = ''
  notice.value = ''
  try {
    const parsed = JSON.parse(importText.value)
    if (!Array.isArray(parsed)) throw new Error('导入内容必须是 JSON 数组。')
    const result = await importKbItems(parsed)
    notice.value = `导入完成：新增 ${result.created_count} 条，跳过 ${result.skipped_count} 条。`
    importText.value = ''
    await loadItems(1)
  } catch (err) {
    error.value = err instanceof SyntaxError ? 'JSON 格式不正确，请检查后重试。' : err.message
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  if (!auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      // 未登录或令牌失效时由路由守卫与登录模态框处理
    }
  }
  if (isAdmin.value) await loadItems()
})
</script>
