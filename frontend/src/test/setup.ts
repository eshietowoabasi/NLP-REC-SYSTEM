import '@testing-library/jest-dom/vitest'

import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

import { api, resetApiState } from '@/lib/api'

// findBy*/waitFor wait up to 3 s (default 1 s): whole-app renders with several queries can
// take longer than a second when the full suite runs in parallel on a slower machine.
configure({ asyncUtilTimeout: 3000 })

const realAdapter = api.defaults.adapter

afterEach(() => {
  cleanup()
  api.defaults.adapter = realAdapter
  resetApiState()
})

// jsdom lacks matchMedia, which the shadcn sidebar uses to detect mobile widths.
if (!window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })
}

// Radix menus, selects and dialogs use browser APIs that jsdom does not implement.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false
  Element.prototype.setPointerCapture = () => undefined
  Element.prototype.releasePointerCapture = () => undefined
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined
}
if (!('ResizeObserver' in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
