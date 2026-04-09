export const storage = {
  get<T>(key: string, fallback: T): T {
    const raw = window.localStorage.getItem(key)
    if (!raw) return fallback

    try {
      return JSON.parse(raw) as T
    } catch {
      return fallback
    }
  },
  set<T>(key: string, value: T) {
    window.localStorage.setItem(key, JSON.stringify(value))
  },
  remove(key: string) {
    window.localStorage.removeItem(key)
  }
}
