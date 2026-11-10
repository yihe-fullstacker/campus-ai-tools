<template>
  <section class="module-page">
    <p class="module-page__eyebrow">CampusAI · {{ meta.eyebrow }}</p>
    <h1 class="module-page__title">{{ meta.title }}</h1>
    <p class="module-page__desc">{{ meta.desc }}</p>
    <span class="module-page__status">{{ meta.status }}</span>

    <div class="module-page__grid">
      <article v-for="card in meta.cards" :key="card.title" class="module-card">
        <h2 class="module-card__title">{{ card.title }}</h2>
        <p class="module-card__desc">{{ card.desc }}</p>
        <span class="module-card__tag">{{ card.tag }}</span>
      </article>
    </div>

    <p class="module-notice">{{ meta.notice }}</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { getModuleMeta } from '@/modules'

const route = useRoute()

const meta = computed(() => getModuleMeta(route.meta.module))
</script>
