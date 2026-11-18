/**
 * After a new version is published, a page opened earlier may ask for screen files that no
 * longer exist ("Failed to fetch dynamically imported module"). Instead of an error, reload the
 * page once so the browser picks up the new version. The reload is skipped if one happened in
 * the last 30 seconds, so a real network failure cannot cause a reload loop.
 */
const KEY = 'skillbridge:new-version-reload'
const WINDOW_MS = 30_000

export function isStaleScreenError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  return /dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i.test(
    message,
  )
}

/** Reload once for a new version; returns false when a reload just happened. */
export function reloadForNewVersion(): boolean {
  try {
    const last = Number(sessionStorage.getItem(KEY) ?? 0)
    if (Date.now() - last < WINDOW_MS) return false
    sessionStorage.setItem(KEY, String(Date.now()))
  } catch {
    // Storage unavailable: still reload once (this page load).
  }
  window.location.reload()
  return true
}

/** Wraps a screen import so a stale screen file reloads the page instead of failing. */
export function loadScreen<M>(load: () => Promise<M>): Promise<M> {
  return load().catch((error: unknown) => {
    if (isStaleScreenError(error) && reloadForNewVersion()) {
      return new Promise<M>(() => {}) // the page is reloading
    }
    throw error
  })
}

/** Vite reports failed preloads of a new version's files with this event. */
export function listenForNewVersion() {
  window.addEventListener('vite:preloadError', (event) => {
    if (reloadForNewVersion()) event.preventDefault()
  })
}
