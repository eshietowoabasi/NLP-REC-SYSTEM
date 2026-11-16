import { useEffect } from 'react'
import { useMatches } from 'react-router'

import { APP_NAME, type RouteHandle } from '@/routes/handle'

function hasTitle(handle: unknown): handle is RouteHandle {
  return typeof handle === 'object' && handle !== null && 'title' in handle
}

/**
 * Title and breadcrumb of the deepest matched route (from its `handle`); also sets
 * document.title.
 */
export function usePageHeading(): { title: string; crumb: string } {
  const matches = useMatches()
  const match = [...matches].reverse().find((m) => hasTitle(m.handle))
  const handle = match && hasTitle(match.handle) ? match.handle : undefined
  const title = handle?.title ?? APP_NAME

  useEffect(() => {
    document.title = title === APP_NAME ? APP_NAME : `${title} · ${APP_NAME}`
  }, [title])

  return { title, crumb: handle?.crumb ?? 'Workspace' }
}

/** Title of the deepest matched route; also sets document.title. */
export function usePageTitle(): string {
  return usePageHeading().title
}
