<template>
  <div class="app">
    <AtmosphereCanvas ref="atmoRef" />
    <HaldenNav ref="navRef" />
    <div class="app__main">
      <RouterView />
    </div>
    <LoginModal />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'

import AtmosphereCanvas from '@/components/AtmosphereCanvas.vue'
import HaldenNav from '@/components/HaldenNav.vue'
import LoginModal from '@/components/LoginModal.vue'
import { createAmbientScene } from '@/halden/scene'

const atmoRef = ref(null)
const navRef = ref(null)

let scene = null

onMounted(() => {
  scene = createAmbientScene({
    canvas: atmoRef.value?.canvas,
    nav: navRef.value?.root,
  })
})

onBeforeUnmount(() => {
  scene?.destroy()
  scene = null
})
</script>
