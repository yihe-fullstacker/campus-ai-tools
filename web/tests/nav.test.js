import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import HaldenNav from '../src/components/HaldenNav.vue'
import { useAuthStore } from '../src/stores/auth'

function mountNav(pinia) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/qa', component: { template: '<div />' } },
      { path: '/chat', component: { template: '<div />' } },
      { path: '/documents', component: { template: '<div />' } },
      { path: '/search', component: { template: '<div />' } },
    ],
  })
  return mount(HaldenNav, { global: { plugins: [pinia, router] } })
}

describe('导航栏', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('未登录时展示登录入口且没有退出按钮', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mountNav(pinia)

    expect(wrapper.find('.who').exists()).toBe(false)
    expect(wrapper.findAll('.right .login')).toHaveLength(1)
    expect(wrapper.find('.right .login').text()).toBe('登录')
  })

  it('已登录时展示身份与退出按钮', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.user = { id: 1, identity: '20240101', role: 'student', created_at: '2026-11-10T00:00:00Z' }

    const wrapper = mountNav(pinia)

    expect(wrapper.find('.who').text()).toBe('20240101')
    expect(wrapper.find('.right .login').text()).toBe('退出')
  })

  it('点击退出后调用登出接口并清空本地会话', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204, text: async () => '' })
    vi.stubGlobal('fetch', fetchMock)
    localStorage.setItem('campus_ai_token', 'token-abc')

    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.user = { id: 1, identity: '20240101', role: 'student', created_at: '2026-11-10T00:00:00Z' }

    const wrapper = mountNav(pinia)
    await wrapper.find('.right .login').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalled()
    expect(String(fetchMock.mock.calls[0][0])).toContain('/auth/logout')
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('campus_ai_token')).toBeNull()
  })
})
