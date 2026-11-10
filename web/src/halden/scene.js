/**
 * 场景引擎：碗状光效画布 + 滚动驱动的揭示动画。
 *
 * - `createAmbientScene`：全局常驻，只负责碗状光效与导航 CTA 的出现时机；
 * - `createRevealScene`：落地页专用，负责英雄区逐字显现、宣言上浮与逐字揭示、
 *   暗色分栏标题与图片缩放。
 */

import { paint, smoothstep, splitText } from './reveal.js'

const CANVAS_W = 96
const CANVAS_H = 60
const EDGE_POINTS = 48

const SCROLL_KEYS = [0, 0.03, 0.08, 0.18, 0.4, 0.66, 0.87, 1.15, 1.43, 1.8]
const SCROLL_TIPS = [0.3, 0.45, 0.65, 0.8, 0.95, 1.05, 1.05, 1.1, 1.3, 2.4]
const SCROLL_HALVES = [0.34, 0.38, 0.38, 0.38, 0.38, 0.46, 0.66, 0.9, 1.6, 3.0]
const SCROLL_SOFTS = [0.22, 0.26, 0.22, 0.22, 0.19, 0.16, 0.13, 0.1, 0.1, 0.1]

const INTRO_DELAY = 250
const INTRO_DURATION = 1050

function interp(arr, q) {
  if (q <= SCROLL_KEYS[0]) return arr[0]
  if (q >= SCROLL_KEYS[SCROLL_KEYS.length - 1]) return arr[arr.length - 1]
  for (let i = 0; i < SCROLL_KEYS.length - 1; i += 1) {
    if (q >= SCROLL_KEYS[i] && q <= SCROLL_KEYS[i + 1]) {
      const t = (q - SCROLL_KEYS[i]) / (SCROLL_KEYS[i + 1] - SCROLL_KEYS[i])
      return arr[i] + (arr[i + 1] - arr[i]) * t
    }
  }
  return arr[arr.length - 1]
}

function distToSeg(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1
  const dy = y2 - y1
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
  const cx = x1 + t * dx
  const cy = y1 + t * dy
  return Math.hypot(px - cx, py - cy)
}

/**
 * 创建全局场景：碗状光效 + 导航 CTA 出现时机。
 *
 * @param {{canvas: HTMLCanvasElement, nav?: HTMLElement, navCtaAt?: number}} options
 */
export function createAmbientScene({ canvas, nav = null, navCtaAt = 1.37 }) {
  const ctx = canvas.getContext('2d')
  let viewW = window.innerWidth
  let viewH = window.innerHeight
  let cur = { tip: -0.3, half: 0.3, soft: 0.1 }
  const tgt = { tip: 0.3, half: 0.34, soft: 0.22 }
  let introStart = null
  let frame = null
  let navOn = false
  let readyAdded = false

  function applyNav(state) {
    if (!nav || navOn === state) return
    navOn = state
    nav.classList.toggle('on', state)
  }

  function drawBowl(time) {
    const img = ctx.createImageData(CANVAS_W, CANVAS_H)
    const data = img.data
    const aspect = viewW / viewH
    const tip = cur.tip + Math.sin(time * 0.00033 + 1.3) * 0.02
    const half = cur.half + Math.sin(time * 0.0005) * 0.015
    const points = []
    for (let i = 0; i < EDGE_POINTS; i += 1) {
      const yy = -0.3 + (tip + 0.3) * (i / (EDGE_POINTS - 1))
      points.push([half * aspect * Math.pow(1 - yy / tip, 0.72), yy])
    }
    for (let y = 0; y < CANVAS_H; y += 1) {
      for (let x = 0; x < CANVAS_W; x += 1) {
        const px = Math.abs(x / CANVAS_W - 0.5) * aspect
        const py = y / CANVAS_H
        let dist = 1e9
        for (let i = 0; i < points.length - 1; i += 1) {
          const d = distToSeg(px, py, points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
          if (d < dist) dist = d
        }
        const inside = py < tip && px < half * aspect * Math.pow(1 - py / tip, 0.72)
        const sd = (inside ? -dist : dist) - 0.25
        const g = 1 - smoothstep((sd + cur.soft) / (2 * cur.soft))
        let r
        let g2
        let b
        if (g < 0.38) {
          const u = smoothstep(g / 0.38)
          r = Math.round(255 + (210 - 255) * u)
          g2 = Math.round(255 + (218 - 255) * u)
          b = 255
        } else {
          const u = smoothstep((g - 0.38) / 0.62)
          r = Math.round(210 + (143 - 210) * u)
          g2 = Math.round(218 + (213 - 218) * u)
          b = Math.round(255 + (241 - 255) * u)
        }
        const idx = (y * CANVAS_W + x) * 4
        data[idx] = r
        data[idx + 1] = g2
        data[idx + 2] = b
        data[idx + 3] = 255
      }
    }
    ctx.putImageData(img, 0, 0)
  }

  function onScroll() {
    const q = window.scrollY / window.innerHeight
    tgt.tip = interp(SCROLL_TIPS, q)
    tgt.half = interp(SCROLL_HALVES, q)
    tgt.soft = interp(SCROLL_SOFTS, q)
    applyNav(q > navCtaAt)
  }

  function onResize() {
    viewW = window.innerWidth
    viewH = window.innerHeight
    onScroll()
  }

  function loop(ts) {
    if (introStart === null) introStart = ts
    const elapsed = ts - introStart
    if (elapsed < INTRO_DELAY) {
      cur = { tip: -0.3, half: 0.3, soft: 0.1 }
    } else if (elapsed < INTRO_DELAY + INTRO_DURATION) {
      const t = Math.min(1, (elapsed - INTRO_DELAY) / INTRO_DURATION)
      const e = t * t * (3 - 2 * t)
      cur = {
        tip: -0.3 + e * 0.6,
        half: 0.3 + e * 0.04,
        soft: 0.1 + e * 0.12,
      }
    } else {
      cur = {
        tip: cur.tip + (tgt.tip - cur.tip) * 0.12,
        half: cur.half + (tgt.half - cur.half) * 0.12,
        soft: cur.soft + (tgt.soft - cur.soft) * 0.12,
      }
    }
    if (!readyAdded && elapsed >= INTRO_DELAY + INTRO_DURATION) {
      readyAdded = true
      document.body.classList.add('ready')
    }
    drawBowl(ts)
    frame = requestAnimationFrame(loop)
  }

  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onResize)
  frame = requestAnimationFrame(loop)
  onScroll()

  return {
    destroy() {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onResize)
      document.body.classList.remove('ready')
    },
  }
}

/**
 * 创建落地页的滚动揭示场景。
 *
 * @param {{
 *   hero?: HTMLElement, statement?: HTMLElement, split?: HTMLElement,
 *   headline?: HTMLElement, row?: HTMLElement, image?: HTMLElement
 * }} elements
 */
export function createRevealScene({
  hero = null,
  statement = null,
  split = null,
  headline = null,
  row = null,
  image = null,
}) {
  const heroChars = hero ? splitText(hero) : []
  const stmtChars = statement ? splitText(statement) : []
  const headlineChars = headline ? splitText(headline) : []
  let heroStart = null
  let frame = null
  let rowOn = false

  function applyRow(state) {
    if (!row || rowOn === state) return
    rowOn = state
    row.classList.toggle('on', state)
  }

  function onScroll() {
    const q = window.scrollY / window.innerHeight
    const s = Math.max(0, Math.min(1, (q - 0.69) / 0.74))
    if (statement) {
      statement.style.transform = `translateY(${0.205 * Math.pow(1 - s, 2) * window.innerHeight}px)`
    }
    const pStmt = Math.max(0, Math.min(1, (q - 0.56) / 2.03))
    paint(stmtChars, pStmt, 0.16, '#0b1d3a', '#3f7cff', '#ffffff')

    if (split) {
      const splitTop = split.getBoundingClientRect().top
      const p2 = Math.max(0, Math.min(1, (0.8 - splitTop / window.innerHeight) / 0.65))
      paint(headlineChars, p2, 0.35, '#ffffff', '#8fe6f4', '#5c6f92')
      applyRow(p2 > 0.92)
      if (image) {
        const sc = 1.08 - 0.08 * Math.max(0, Math.min(1, 1 - splitTop / window.innerHeight))
        image.style.transform = `scale(${sc})`
      }
    }
  }

  function heroReveal(ts) {
    if (heroStart === null) heroStart = ts
    const p = Math.min(1, (ts - heroStart) / 1250)
    paint(heroChars, p, 0.35, '#0b1d3a', '#3f7cff', '#ffffff')
    if (p < 1) frame = requestAnimationFrame(heroReveal)
  }

  paint(heroChars, 0, 0.35, '#0b1d3a', '#3f7cff', '#ffffff')
  paint(stmtChars, 0, 0.16, '#0b1d3a', '#3f7cff', '#ffffff')
  paint(headlineChars, 0, 0.35, '#ffffff', '#8fe6f4', '#5c6f92')

  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
  frame = requestAnimationFrame(heroReveal)
  onScroll()

  return {
    destroy() {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    },
  }
}
