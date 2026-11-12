<template>
  <section class="settings">
    <header class="settings__head">
      <p class="settings__eyebrow">CampusAI · 模型接入</p>
      <h1 class="settings__title">接入你自己的大模型 API</h1>
      <p class="settings__desc">
        把你在模型厂商控制台拿到的 API 密钥粘贴到下面，就能用自己的额度驱动校园问答与学习助手。
        密钥在服务端加密存储，页面只会显示掩码，任何时候都不回传明文。
      </p>
    </header>

    <div class="settings__body">
      <form class="form" @submit.prevent="handleSubmit">
        <h2 class="form__title">{{ editingId ? '编辑配置' : '新增配置' }}</h2>

        <label class="field">
          <span class="field__label">模型厂商</span>
          <select v-model="form.provider" class="field__input" @change="applyPreset">
            <option v-for="item in presets" :key="item.provider" :value="item.provider">
              {{ item.display_name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field__label">接口地址 base_url</span>
          <input
            v-model="form.base_url"
            class="field__input"
            type="text"
            :placeholder="currentPreset?.base_url || 'https://example.com/v1'"
          />
          <span class="field__hint">
            国内主流模型多为 OpenAI 兼容接口；本地 Ollama 可填 http://127.0.0.1:11434/v1
          </span>
        </label>

        <label class="field">
          <span class="field__label">模型名称</span>
          <input
            v-model="form.model"
            class="field__input"
            type="text"
            list="model-suggestions"
            :placeholder="currentPreset?.models?.[0] || 'deepseek-chat'"
          />
          <datalist id="model-suggestions">
            <option v-for="name in currentPreset?.models || []" :key="name" :value="name" />
          </datalist>
        </label>

        <label v-if="editingId" class="field">
          <span class="field__label">新的 API 密钥（留空则不修改）</span>
          <input v-model="form.api_key" class="field__input" type="password" autocomplete="off" />
        </label>

        <label v-else class="field">
          <span class="field__label">API 密钥</span>
          <input
            v-model="form.api_key"
            class="field__input"
            type="password"
            autocomplete="off"
            placeholder="粘贴你的 API Key，例如 sk-..."
          />
          <span class="field__hint">
            密钥仅用于你本人的调用，加密存放，其他账号无法读取，也不会显示在页面上。
          </span>
        </label>

        <label class="field">
          <span class="field__label">向量模型（可选）</span>
          <input
            v-model="form.embedding_model"
            class="field__input"
            type="text"
            :placeholder="currentPreset?.embedding_model || '暂不填写也可以'"
          />
        </label>

        <p v-if="message" class="form__message" :class="`form__message--${messageKind}`">
          {{ message }}
        </p>

        <div class="form__actions">
          <button class="btn btn--primary" type="submit" :disabled="busy">
            {{ editingId ? '保存修改' : '保存配置' }}
          </button>
          <button class="btn" type="button" :disabled="busy || !canTest" @click="handleTest">
            测试连通性
          </button>
          <button v-if="editingId" class="btn" type="button" @click="resetForm">取消编辑</button>
        </div>
      </form>

      <div class="list">
        <h2 class="list__title">已保存的配置</h2>
        <p v-if="!configs.length" class="list__empty">还没有配置。填入上面的表单即可开始。</p>
        <article v-for="item in configs" :key="item.id" class="card" :class="{ 'card--active': item.is_active }">
          <div class="card__main">
            <p class="card__name">
              {{ item.display_name }}
              <span v-if="item.is_active" class="card__badge">当前生效</span>
            </p>
            <p class="card__meta">{{ item.base_url }} · {{ item.model }}</p>
            <p class="card__key">密钥：{{ item.api_key_hint }}</p>
            <p v-if="item.last_error" class="card__error">上次测试失败：{{ item.last_error }}</p>
          </div>
          <div class="card__actions">
            <button
              v-if="!item.is_active"
              class="btn btn--sm"
              type="button"
              @click="handleActivate(item.id)"
            >
              设为生效
            </button>
            <button class="btn btn--sm" type="button" @click="startEdit(item)">编辑</button>
            <button class="btn btn--sm btn--danger" type="button" @click="handleDelete(item.id)">
              删除
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import {
  activateConfig,
  createConfig,
  deleteConfig,
  fetchConfigs,
  fetchPresets,
  testConfig,
  updateConfig,
} from '@/api/llmConfigs'

const presets = ref([])
const configs = ref([])
const editingId = ref(null)
const busy = ref(false)
const message = ref('')
const messageKind = ref('info')

const form = reactive({
  provider: 'deepseek',
  base_url: '',
  model: '',
  embedding_model: '',
  api_key: '',
})

const currentPreset = computed(() => presets.value.find((p) => p.provider === form.provider))
const canTest = computed(() => Boolean(form.api_key) || Boolean(editingId.value))

function applyPreset() {
  const preset = currentPreset.value
  if (!preset) return
  form.base_url = preset.base_url
  form.model = preset.models?.[0] || ''
  form.embedding_model = preset.embedding_model || ''
}

function say(text, kind = 'info') {
  message.value = text
  messageKind.value = kind
}

function resetForm() {
  editingId.value = null
  form.api_key = ''
  applyPreset()
  message.value = ''
}

function startEdit(item) {
  editingId.value = item.id
  form.provider = item.provider
  form.base_url = item.base_url
  form.model = item.model
  form.embedding_model = item.embedding_model || ''
  form.api_key = ''
  message.value = ''
}

async function load() {
  try {
    configs.value = await fetchConfigs()
  } catch (error) {
    say(error.message, 'error')
  }
}

async function handleSubmit() {
  busy.value = true
  try {
    if (editingId.value) {
      const payload = {
        provider: form.provider,
        base_url: form.base_url.trim() || undefined,
        model: form.model.trim(),
        embedding_model: form.embedding_model.trim() || undefined,
      }
      if (form.api_key.trim()) payload.api_key = form.api_key.trim()
      await updateConfig(editingId.value, payload)
      say('配置已更新。', 'ok')
    } else {
      await createConfig({
        provider: form.provider,
        base_url: form.base_url.trim() || undefined,
        model: form.model.trim(),
        embedding_model: form.embedding_model.trim() || undefined,
        api_key: form.api_key.trim(),
      })
      say('配置已保存。', 'ok')
    }
    editingId.value = null
    form.api_key = ''
    await load()
  } catch (error) {
    say(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function handleTest() {
  busy.value = true
  say('正在用一次极短对话测试…', 'info')
  try {
    const payload = {}
    if (form.api_key.trim()) {
      payload.provider = form.provider
      payload.base_url = form.base_url.trim()
      payload.model = form.model.trim()
      payload.api_key = form.api_key.trim()
    } else {
      payload.config_id = editingId.value
    }
    const result = await testConfig(payload)
    if (result.ok) {
      say(`连接成功，模型回复：${result.reply}`, 'ok')
      await load()
    } else {
      say(result.error, 'error')
    }
  } catch (error) {
    say(error.message, 'error')
  } finally {
    busy.value = false
  }
}

async function handleActivate(id) {
  try {
    await activateConfig(id)
    await load()
    say('已切换生效配置。', 'ok')
  } catch (error) {
    say(error.message, 'error')
  }
}

async function handleDelete(id) {
  if (!window.confirm('确定删除这份配置吗？删除后如需使用要重新填写密钥。')) return
  try {
    await deleteConfig(id)
    await load()
    say('配置已删除。', 'ok')
  } catch (error) {
    say(error.message, 'error')
  }
}

onMounted(async () => {
  try {
    presets.value = await fetchPresets()
  } catch {
    presets.value = []
  }
  applyPreset()
  await load()
})
</script>

<style scoped>
.settings {
  max-width: 1120px;
  margin: 0 auto;
  padding: 96px 24px 64px;
}
.settings__eyebrow {
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-3, #6b7280);
}
.settings__title {
  margin: 12px 0 10px;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.2;
}
.settings__desc {
  max-width: 720px;
  color: var(--ink-2, #4b5563);
  line-height: 1.7;
}
.settings__body {
  display: grid;
  gap: 32px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  margin-top: 36px;
}
@media (max-width: 900px) {
  .settings__body {
    grid-template-columns: 1fr;
  }
}
.form,
.list {
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 18px;
  padding: 24px;
  background: var(--card, #fff);
}
.form__title,
.list__title {
  margin: 0 0 18px;
  font-size: 18px;
}
.field {
  display: block;
  margin-bottom: 16px;
}
.field__label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-2, #374151);
}
.field__input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--line, #d1d5db);
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
  color: #111827;
}
.field__input:focus {
  outline: 2px solid #5b7cf0;
  outline-offset: 1px;
}
.field__hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ink-3, #6b7280);
}
.form__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}
.btn {
  padding: 9px 16px;
  border-radius: 999px;
  border: 1px solid var(--line, #d1d5db);
  background: #fff;
  font-size: 14px;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: #0b1d3a;
  border-color: #0b1d3a;
  color: #fff;
}
.btn--sm {
  padding: 6px 12px;
  font-size: 13px;
}
.btn--danger {
  color: #b91c1c;
  border-color: #fca5a5;
}
.form__message {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
  background: #f3f4f6;
}
.form__message--ok {
  background: #ecfdf5;
  color: #065f46;
}
.form__message--error {
  background: #fef2f2;
  color: #991b1b;
}
.list__empty {
  color: var(--ink-3, #6b7280);
  font-size: 14px;
}
.card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 14px;
  margin-bottom: 12px;
}
.card--active {
  border-color: #5b7cf0;
  background: #f5f7ff;
}
.card__name {
  margin: 0 0 6px;
  font-weight: 600;
}
.card__badge {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #5b7cf0;
  color: #fff;
  font-size: 11px;
}
.card__meta,
.card__key {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--ink-3, #6b7280);
  word-break: break-all;
}
.card__error {
  margin: 6px 0 0;
  font-size: 12px;
  color: #b91c1c;
}
.card__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
