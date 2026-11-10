import { describe, expect, it } from 'vitest'

import { lerpColor, paint, smoothstep, splitText } from '../src/halden/reveal'

describe('逐字揭示引擎', () => {
  it('把标题拆成逐字符 span，并保留换行', () => {
    const el = document.createElement('h1')
    el.innerHTML = 'Meet <span class="hl">小智</span>, your AI teammate<br>for campus life'
    const chars = splitText(el)

    expect(chars.length).toBeGreaterThan(10)
    expect(el.querySelector('br')).not.toBeNull()
    expect(chars.every((c) => c.style.display === 'inline-block')).toBe(true)
  })

  it('高亮元素里的字符被标记，最终停在强调色', () => {
    const el = document.createElement('h1')
    el.innerHTML = 'Meet <span class="hl">小智</span>'
    const chars = splitText(el)
    const highlighted = chars.filter((c) => c.dataset.hl === '1')

    expect(highlighted).toHaveLength(2)
    expect(highlighted[0].textContent).toBe('小')

    paint(chars, 1, 0.35, '#0b1d3a', '#3f7cff', '#ffffff')
    expect(highlighted[0].style.color).toBe('rgb(63, 124, 255)')
    expect(chars[0].style.color).toBe('rgb(11, 29, 58)')
  })

  it('进度为 0 时字符不可见，为 1 时完全显现', () => {
    const el = document.createElement('h1')
    el.textContent = 'ABC'
    const chars = splitText(el)

    paint(chars, 0, 0.35, '#0b1d3a', '#3f7cff', '#ffffff')
    expect(chars[0].style.opacity).toBe('0')
    expect(chars[0].style.filter).toBe('blur(8px)')

    paint(chars, 1, 0.35, '#0b1d3a', '#3f7cff', '#ffffff')
    expect(chars[2].style.opacity).toBe('1')
    expect(chars[2].style.filter).toBe('blur(0px)')
  })

  it('颜色插值与平滑函数符合预期', () => {
    expect(lerpColor('#000000', '#ffffff', 0.5)).toBe('rgb(128,128,128)')
    expect(smoothstep(-1)).toBe(0)
    expect(smoothstep(2)).toBe(1)
    expect(smoothstep(0.5)).toBeCloseTo(0.5)
  })
})
