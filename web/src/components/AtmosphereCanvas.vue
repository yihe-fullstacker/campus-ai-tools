<template>
  <div class="atmo">
    <canvas ref="canvasEl" width="96" height="60"></canvas>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const canvasEl = ref(null)

defineExpose({ canvas: canvasEl })
</script>
