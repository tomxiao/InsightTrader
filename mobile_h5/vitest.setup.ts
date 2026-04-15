import { beforeEach } from 'vitest'

beforeEach(() => {
  window.localStorage.clear()
})

if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => {}
}
