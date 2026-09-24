import { useEffect } from 'react'
import { useMatches } from 'react-router'

import { APP_NAME, type RouteHandle } from '@/routes/handle'

function hasTitle(handle: unknown): handle is RouteHandle {
  return typeof handle === 'object' && handle !== null && 'title' in handle
}

/**
 * Title of the deepest matched route (from its `handle.title`); also sets document.title.
 */
export function usePageTitle(): string {
  const matches = useMatches()
  const match = [...matches].reverse().find((m) => hasTitle(m.handle))
  const title = match && hasTitle(match.handle) ? match.handle.title : APP_NAME

  useEffect(() => {
    document.title = title === APP_NAME ? APP_NAME : `${title} · ${APP_NAME}`
  }, [title])

  return title
}
