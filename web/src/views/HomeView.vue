<template>
  <section class="home">
    <div class="home__hero">
      <h1 class="home__title">你好，{{ displayName }}</h1>
      <p class="home__subtitle">
        校园综合 AI 平台围绕你的学习与办事场景提供帮助。以下能力正在按批次上线。
      </p>
    </div>

    <ul class="module-grid">
      <li v-for="module in modules" :key="module.name" class="module-card">
        <h2 class="module-card__title">{{ module.name }}</h2>
        <p class="module-card__desc">{{ module.desc }}</p>
        <span class="module-card__status">{{ module.status }}</span>
      </li>
    </ul>

    <div class="notice">
      <h2 class="notice__title">关于尚未核对的内容</h2>
      <p class="notice__text">
        平台当前的校园语料基于全国高校通行做法整理，尚未逐条核对学校官方文件。
        命中这类条目时，回答会置顶显示"通用建议，尚未核对官方文件"的提示，
        涉及安全、紧急事件、重要办事期限与收费政策的信息，请以学校官方最新通知为准。
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const modules = [
  { name: '校园智能问答', desc: '面向办事流程、校园生活的问答', status: '开发中' },
  { name: 'AI 学习助手', desc: '自由问答、复习计划、概念解释、思路点拨', status: '开发中' },
  { name: '资料解析与总结', desc: '上传 PDF/Word/PPT，自动生成摘要与提纲', status: '开发中' },
  { name: '校园资源搜索', desc: '统一检索校园资料与学习资源', status: '开发中' },
]

const displayName = computed(() => (auth.user ? auth.user.identity : '同学'))

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.fetchUser()
    } catch {
      auth.resetSession()
    }
  }
})
</script>
