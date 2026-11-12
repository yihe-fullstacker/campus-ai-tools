import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ApiSettingsView from '../src/views/ApiSettingsView.vue'

vi.mock('../src/api/llmConfigs', () => ({
  fetchPresets: vi.fn(),
  fetchConfigs: vi.fn(),
  createConfig: vi.fn(),
  updateConfig: vi.fn(),
  activateConfig: vi.fn(),
  deleteConfig: vi.fn(),
  testConfig: vi.fn(),
}))

const api = await import('../src/api/llmConfigs')

const PRESETS = [
  {
    provider: 'deepseek',
    display_name: 'DeepSeek 深度求索',
    base_url: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat'],
    embedding_model: '',
  },
  {
    provider: 'openai-compatible',
    display_name: '自定义',
    base_url: '',
    models: [],
    embedding_model: '',
  },
]

describe('模型接入页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = vi.fn()
    api.fetchPresets.mockResolvedValue(PRESETS)
    api.fetchConfigs.mockResolvedValue([])
  })

  it('加载预设后自动填入接口地址与默认模型', async () => {
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    expect(wrapper.find('select').element.value).toBe('deepseek')
    const inputs = wrapper.findAll('input')
    expect(inputs[0].element.value).toBe('https://api.deepseek.com/v1')
    expect(inputs[1].element.value).toBe('deepseek-chat')
  })

  it('密钥输入框为密码类型，不显示明文', async () => {
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    const keyInput = wrapper.findAll('input').find((i) => i.attributes('type') === 'password')
    expect(keyInput).toBeTruthy()
    expect(wrapper.html()).not.toContain('type="text" autocomplete="off" placeholder="粘贴')
  })

  it('提交表单时把粘贴的密钥交给接口', async () => {
    api.createConfig.mockResolvedValue({ id: 1 })
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    const inputs = wrapper.findAll('input')
    const keyInput = inputs.find((i) => i.attributes('type') === 'password')
    await keyInput.setValue('sk-pasted-key-123456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.createConfig).toHaveBeenCalledTimes(1)
    const payload = api.createConfig.mock.calls[0][0]
    expect(payload.api_key).toBe('sk-pasted-key-123456')
    expect(payload.provider).toBe('deepseek')
    expect(payload.model).toBe('deepseek-chat')
  })

  it('测试连通性时展示成功回复', async () => {
    api.testConfig.mockResolvedValue({ ok: true, reply: '正常', model: 'deepseek-chat' })
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    const keyInput = wrapper.findAll('input').find((i) => i.attributes('type') === 'password')
    await keyInput.setValue('sk-pasted-key-123456')
    const buttons = wrapper.findAll('button')
    const testButton = buttons.find((b) => b.text().includes('测试连通性'))
    await testButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('连接成功')
  })

  it('测试失败时展示后端返回的错误原文', async () => {
    api.testConfig.mockResolvedValue({ ok: false, error: 'API 密钥无效或已过期，请检查后重新填写。' })
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    const keyInput = wrapper.findAll('input').find((i) => i.attributes('type') === 'password')
    await keyInput.setValue('sk-pasted-key-123456')
    const testButton = wrapper.findAll('button').find((b) => b.text().includes('测试连通性'))
    await testButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('API 密钥无效或已过期')
  })

  it('列出已保存配置时只显示掩码，不出现明文', async () => {
    api.fetchConfigs.mockResolvedValue([
      {
        id: 1,
        provider: 'deepseek',
        display_name: 'DeepSeek · deepseek-chat',
        base_url: 'https://api.deepseek.com/v1',
        model: 'deepseek-chat',
        api_key_hint: 'sk-a********7890',
        is_active: true,
        last_error: null,
      },
    ])
    const wrapper = mount(ApiSettingsView)
    await flushPromises()

    expect(wrapper.text()).toContain('sk-a********7890')
    expect(wrapper.text()).toContain('当前生效')
  })
})
