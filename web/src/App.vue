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
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const atmoRef = ref(null)
const navRef = ref(null)

let scene = null

onMounted(() => {
  scene = createAmbientScene({
    canvas: atmoRef.value?.canvas,
    nav: navRef.value?.root,
  })
  // 刷新页面后用本地令牌恢复登录态；令牌失效时 store 会自行清除会话，
  // 网络异常等临时故障保留令牌，等下一次刷新或操作时再试。
  auth.restoreSession().catch(() => {})
})

onBeforeUnmount(() => {
  scene?.destroy()
  scene = null
})
</script>
