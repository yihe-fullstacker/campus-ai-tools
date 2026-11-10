<template>
  <div>
    <section class="hero" id="hero">
      <h1 id="h1" ref="heroEl">
        Meet <span class="hl">小智</span>, your AI teammate<br />for campus life
      </h1>
      <p class="trust fade-up" style="--d: 1.15s">高校学生信赖 CampusAI</p>
      <div class="cta fade-up" style="--d: 1.3s">
        <button class="btn lg" type="button" @click="startTrial">
          免费试用
          <span class="dot">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M5.5 3.5 10 8l-4.5 4.5"
                stroke="#0b1d3a"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </button>
      </div>

      <div class="logos">
        <div class="cell fade-up" style="--d: 1.25s">
          <div class="mark">
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M2 10c3-2 6-2 9 0s6 2 9 0" stroke="#3e4d68" stroke-width="2.4" stroke-linecap="round" />
              <path d="M2 14c3-2 6-2 9 0s6 2 9 0" stroke="#3e4d68" stroke-width="2.4" stroke-linecap="round" />
            </svg>
            OCEANEX
          </div>
        </div>
        <div class="cell fade-up" style="--d: 1.32s">
          <div class="mark nord">Nordhavn</div>
        </div>
        <div class="cell fade-up" style="--d: 1.39s">
          <div class="mark">
            <svg viewBox="0 0 20 20" fill="#3e4d68" aria-hidden="true">
              <rect x="2" y="6" width="4" height="10" />
              <rect x="8" y="2" width="4" height="14" />
              <rect x="14" y="4" width="4" height="12" />
            </svg>
            BLUEGATE
          </div>
        </div>
        <div class="cell fade-up" style="--d: 1.46s">
          <div class="mark kelp">
            <svg viewBox="0 0 20 20" fill="none" stroke="#3e4d68" stroke-width="1.5" aria-hidden="true">
              <polygon points="10,2 18,18 2,18" />
            </svg>
            KELPWAY
          </div>
        </div>
        <div class="cell fade-up" style="--d: 1.42s">
          <div class="mark tidel">TIDELINE</div>
        </div>
        <div class="cell fade-up" style="--d: 1.49s">
          <div class="mark">
            <svg viewBox="0 0 20 20" fill="none" stroke="#3e4d68" stroke-width="3" stroke-linecap="round" aria-hidden="true">
              <path d="M3 3v14M3 3h8M3 10h6" />
            </svg>
            HARBORIX
          </div>
        </div>
        <div class="cell fade-up" style="--d: 1.56s">
          <div class="mark sea">
            <svg viewBox="0 0 20 20" fill="none" stroke="#3e4d68" stroke-width="1.5" aria-hidden="true">
              <circle cx="10" cy="10" r="7" />
              <circle cx="10" cy="10" r="2" fill="#3e4d68" />
            </svg>
            seaflux
          </div>
        </div>
        <div class="cell fade-up" style="--d: 1.63s">
          <div class="mark port">
            <svg viewBox="0 0 20 20" fill="#3e4d68" aria-hidden="true">
              <polygon points="2,18 10,2 18,18" />
            </svg>
            PORTERRA
          </div>
        </div>
      </div>
    </section>

    <section class="statement" id="statement">
      <div class="pin">
        <p id="stmt" ref="stmtEl">
          小智是 AI 队友<br />
          它回答问题、解析资料、<br />
          搜索资源、协调安排、<br />
          从入学到毕业全程助力
        </p>
      </div>
    </section>

    <section class="split" id="split" ref="splitEl">
      <div class="l">
        <h2 id="h2" ref="headlineEl">AI 队友<br />像你一样工作</h2>
        <div id="row" ref="rowEl">
          <h3>高校学生</h3>
          <p>
            <strong>更快找到答案。更少切换工具。不再翻遍通知。</strong>
            小智运行问答、资料解析、资源搜索与更多——让你的团队专注于学习与成长。
          </p>
        </div>
      </div>
      <div class="r">
        <img
          id="ship"
          ref="imageEl"
          src="https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20261029_050506_a830ff21-4c71-4272-bc39-b61cacb54463.png&w=1400&q=85"
          alt="Aerial view of a container ship sailing up a misty fjord"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { createRevealScene } from '@/halden/scene'
import { openAuth } from '@/state/ui'

const heroEl = ref(null)
const stmtEl = ref(null)
const splitEl = ref(null)
const headlineEl = ref(null)
const rowEl = ref(null)
const imageEl = ref(null)

let scene = null

onMounted(() => {
  scene = createRevealScene({
    hero: heroEl.value,
    statement: stmtEl.value,
    split: splitEl.value,
    headline: headlineEl.value,
    row: rowEl.value,
    image: imageEl.value,
  })
})

onBeforeUnmount(() => {
  scene?.destroy()
  scene = null
})

function startTrial() {
  openAuth()
}
</script>
