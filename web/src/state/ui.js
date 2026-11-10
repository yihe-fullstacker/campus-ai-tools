/**
 * 界面级共享状态：登录模态框的开关与登录成功后的跳转目标。
 *
 * 不用 Pinia 是因为路由守卫里需要在 pinia 安装之前就能调用它。
 */
import { reactive } from 'vue'

export const ui = reactive({
  authOpen: false,
  authRedirect: '',
})

export function openAuth(redirect = '') {
  ui.authRedirect = redirect
  ui.authOpen = true
}

export function closeAuth() {
  ui.authOpen = false
  ui.authRedirect = ''
}
