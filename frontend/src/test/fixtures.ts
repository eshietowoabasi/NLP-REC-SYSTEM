/** Synthetic test data. Not real people or accounts. */
import type { HealthStatus, Paginated, User } from '@/types/api'

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    username: 'test.admin',
    email: 'test.admin@example.com',
    full_name: 'Test Admin',
    role: 'admin',
    is_active: true,
    created_at: '2026-01-15T09:00:00Z',
    last_login_at: '2026-09-20T08:30:00Z',
    ...overrides,
  }
}

export const adminUser = makeUser()
export const plannerUser = makeUser({
  id: 2,
  username: 'test.planner',
  email: 'test.planner@example.com',
  full_name: 'Test Planner',
  role: 'planner',
})
export const viewerUser = makeUser({
  id: 3,
  username: 'test.viewer',
  email: 'test.viewer@example.com',
  full_name: 'Test Viewer',
  role: 'viewer',
})

export function page<T>(items: T[], overrides: Partial<Paginated<T>['pagination']> = {}) {
  return {
    items,
    pagination: { page: 1, per_page: 20, total: items.length, pages: 1, ...overrides },
  }
}

export const healthyStatus: HealthStatus = {
  status: 'ok',
  version: '0.1.0',
  checks: { database: 'ok', redis: 'ok' },
}
