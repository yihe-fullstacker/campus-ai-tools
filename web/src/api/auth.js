/** 账户相关接口，对应后端 /api/v1/auth/* 与 /api/v1/users/me。 */
import { get, post } from './client'

export function register(identity, password) {
  return post('/auth/register', { identity, password })
}

export function login(identity, password) {
  return post('/auth/login', { identity, password })
}

export function logout() {
  return post('/auth/logout')
}

export function fetchCurrentUser() {
  return get('/users/me')
}
