import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { nextTick } from 'vue'

import LoginModal from '../src/components/LoginModal.vue'
import { ui } from '../src/state/ui'

function mountModal() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  })
  return mount(LoginModal, {
    global: {
      plugins: [pinia, router],
      stubs: { teleport: true },
    },
  })
}

describe('登录模态框', () => {
  beforeEach(() => {
    localStorage.clear()
    ui.authOpen = false
    ui.authRedirect = ''
    vi.unstubAllGlobals()
  })

  it('未触发时不渲染任何内容', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.modal').exists()).toBe(false)
  })

  it('打开后展示登录与注册两个页签', async () => {
    const wrapper = mountModal()
    ui.authOpen = true
    await nextTick()
    expect(wrapper.find('.modal').exists()).toBe(true)
    expect(wrapper.findAll('.modal__tab')).toHaveLength(2)
  })

  it('注册时两次密码不一致给出提示且不提交', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mountModal()
    ui.authOpen = true
    await nextTick()

    await wrapper.find('.modal__tab:nth-child(2)').trigger('click')
    await wrapper.find('input[type="text"]').setValue('20240101')
    const passwordInputs = wrapper.findAll('input[type="password"]')
    await passwordInputs[0].setValue('campus2024')
    await passwordInputs[1].setValue('campus2025')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.modal__error').text()).toContain('两次输入的密码不一致')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('登录失败时展示后端返回的中文提示', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({ code: 'AUTH_CREDENTIALS_INVALID', message: '学号/邮箱或密码不正确。' }),
      }),
    )
    const wrapper = mountModal()
    ui.authOpen = true
    await nextTick()

    await wrapper.find('input[type="text"]').setValue('20240101')
    await wrapper.find('input[type="password"]').setValue('campus2024')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.modal__error').text()).toContain('学号/邮箱或密码不正确')
    expect(ui.authOpen).toBe(true)
  })

  it('登录成功后保存令牌并关闭模态框', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            token: 'token-xyz',
            token_type: 'bearer',
            expires_at: '2026-11-17T00:00:00Z',
            user: { id: 7, identity: '20240101', role: 'student', created_at: '2026-11-10T00:00:00Z' },
          }),
      }),
    )
    const wrapper = mountModal()
    ui.authOpen = true
    await nextTick()

    await wrapper.find('input[type="text"]').setValue('20240101')
    await wrapper.find('input[type="password"]').setValue('campus2024')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(localStorage.getItem('campus_ai_token')).toBe('token-xyz')
    expect(ui.authOpen).toBe(false)
  })
})
