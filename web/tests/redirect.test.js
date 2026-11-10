import { describe, expect, it } from 'vitest'

import { safeRedirect } from '../src/utils/redirect'

describe('safeRedirect', () => {
  it('接受同源相对路径', () => {
    expect(safeRedirect('/qa')).toBe('/qa')
    expect(safeRedirect('/qa?tab=1')).toBe('/qa?tab=1')
    expect(safeRedirect('  /qa  ')).toBe('/qa')
  })

  it('拒绝协议相对 URL（开放重定向）', () => {
    expect(safeRedirect('//evil.com')).toBe('/')
    expect(safeRedirect('//evil.com/path')).toBe('/')
  })

  it('拒绝站外绝对 URL', () => {
    expect(safeRedirect('https://evil.com')).toBe('/')
    expect(safeRedirect('http://evil.com/x')).toBe('/')
  })

  it('拒绝包含反斜杠的路径', () => {
    expect(safeRedirect('/\\evil.com')).toBe('/')
  })

  it('拒绝非字符串或空值', () => {
    expect(safeRedirect(undefined)).toBe('/')
    expect(safeRedirect(null)).toBe('/')
    expect(safeRedirect('')).toBe('/')
    expect(safeRedirect(123)).toBe('/')
  })
})
