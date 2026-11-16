export const APP_NAME = 'SkillBridge'

/** Data attached to a route via `handle`; read by the top bar. */
export interface RouteHandle {
  title: string
  /** The line above the title in the top bar, e.g. "Workspace" or "Administration". */
  crumb?: string
}
