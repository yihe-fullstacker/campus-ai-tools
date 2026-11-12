/**
 * Vitest 初始化：Node 22+ 自带的 localStorage 需要 --localstorage-file 才可用，
 * 在未提供该参数时裸 `localStorage` 为 undefined（Node 26 更明显）。
 * 这里在缺少全局实现时补一个内存版，测试与源码都继续使用标准的 Web Storage 接口。
 */
const existing = (() => {
  try {
    return globalThis.localStorage
  } catch {
    return null
  }
})()

if (!existing) {
  const store = new Map()
  const storage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
    key: (index) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size
    },
  }
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
    writable: true,
  })
}
