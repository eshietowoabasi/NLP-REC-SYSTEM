import type { UserRole } from '@/types/api'

export const ROLES: readonly UserRole[] = ['admin', 'planner', 'viewer']

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Admin',
  planner: 'Curriculum Planner',
  viewer: 'Viewer',
}

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: 'Everything, including users, settings, the NUC core reference and the audit log.',
  planner: 'Upload documents, run analyses, decide on recommendations, map courses, reports.',
  viewer: 'Read-only access to documents, analyses, recommendations and reports.',
}

/** Roles that can create and change data (uploads, sessions, decisions, mappings). */
export function canEdit(role: UserRole | undefined): boolean {
  return role === 'admin' || role === 'planner'
}
