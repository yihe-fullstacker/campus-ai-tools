/**
 * 逐字揭示引擎。
 *
 * 把标题按字符拆成 inline-block 的 span，再按滚动或时间进度给每个字符
 * 设置透明度、颜色与模糊度：不可见 → 模糊的 ghost 色 → accent 色 → 最终色。
 */

export function lerpColor(a, b, t) {
  const pa = parseInt(a.slice(1), 16)
  const pb = parseInt(b.slice(1), 16)
  const r = Math.round(((pa >> 16) & 255) + ((((pb >> 16) & 255) - ((pa >> 16) & 255)) * t))
  const g = Math.round(((pa >> 8) & 255) + ((((pb >> 8) & 255) - ((pa >> 8) & 255)) * t))
  const bl = Math.round((pa & 255) + (((pb & 255) - (pa & 255)) * t))
  return `rgb(${r},${g},${bl})`
}

export function smoothstep(x) {
  const v = Math.max(0, Math.min(1, x))
  return v * v * (3 - 2 * v)
}

/**
 * 把元素的文本拆成逐字符 span。
 *
 * 单词用 inline-block 包裹，避免换行从词中间断开；元素子节点（例如高亮的
 * `.hl`）里的字符会被标记为 hl，最终停在强调色而不是正文色。
 *
 * @param {HTMLElement} el 待拆分的元素
 * @returns {HTMLElement[]} 生成的字符 span
 */
export function splitText(el) {
  const nodes = [...el.childNodes]
  el.innerHTML = ''
  const chars = []

  const pushChar = (char, highlighted, parent) => {
    if (char === ' ') {
      parent.appendChild(document.createTextNode(' '))
      return
    }
    const span = document.createElement('span')
    span.textContent = char
    span.style.display = 'inline-block'
    span.style.whiteSpace = 'nowrap'
    if (highlighted) span.dataset.hl = '1'
    parent.appendChild(span)
    chars.push(span)
  }

  nodes.forEach((node) => {
    if (node.nodeType === 3) {
      for (const char of node.textContent) pushChar(char, false, el)
      return
    }
    if (node.nodeName === 'BR') {
      el.appendChild(document.createElement('br'))
      return
    }
    if (node.nodeType === 1) {
      const word = document.createElement('span')
      word.style.display = 'inline-block'
      word.style.whiteSpace = 'nowrap'
      el.appendChild(word)
      for (const child of [...node.childNodes]) {
        if (child.nodeType === 3) {
          for (const char of child.textContent) pushChar(char, true, word)
        } else if (child.nodeName === 'BR') {
          word.appendChild(document.createElement('br'))
        }
      }
    }
  })

  return chars
}

/**
 * 按进度绘制字符状态。
 *
 * 被标记为 hl 的字符最终停在强调色（accent），其余字符走到最终色。
 *
 * @param {HTMLElement[]} chars 字符数组
 * @param {number} p 全局进度 0–1
 * @param {number} spread 字符之间的错峰系数
 * @param {string} final 最终颜色
 * @param {string} accent 中途强调色
 * @param {string} ghost 起始颜色
 */
export function paint(chars, p, spread, final, accent, ghost) {
  const n = chars.length
  for (let i = 0; i < n; i += 1) {
    const t = Math.max(0, Math.min(1, (p * (1 + spread) - i / n) / spread))
    let opacity
    let blur
    let color
    if (t <= 0) {
      opacity = 0
      blur = 8
      color = ghost
    } else if (t < 0.35) {
      opacity = t / 0.35
      blur = 8 - 6.5 * (t / 0.35)
      color = ghost
    } else if (t < 0.7) {
      opacity = 1
      blur = 1.5 - 1.5 * ((t - 0.35) / 0.35)
      color = lerpColor(ghost, accent, (t - 0.35) / 0.35)
    } else {
      opacity = 1
      blur = 0
      const target = chars[i].dataset.hl === '1' ? accent : final
      color = lerpColor(accent, target, (t - 0.7) / 0.3)
    }
    const char = chars[i]
    char.style.opacity = opacity
    char.style.filter = `blur(${blur}px)`
    char.style.color = color
  }
}
