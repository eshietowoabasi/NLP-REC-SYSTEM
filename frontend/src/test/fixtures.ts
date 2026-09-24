/** Synthetic test data. Not real people or accounts. */
import type { DocumentDetail, DocumentSummary, HealthStatus, Paginated, User } from '@/types/api'

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

export function makeDocument(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: 10,
    title: 'Synthetic backend engineer advert',
    original_filename: 'synthetic-backend-ad.pdf',
    file_type: 'pdf',
    file_size: 48_213,
    source_category: 'job_market',
    processing_status: 'ready',
    error_message: null,
    page_count: 2,
    word_count: 812,
    uploaded_at: '2026-09-20T10:00:00Z',
    parsed_at: '2026-09-20T10:00:05Z',
    uploaded_by: { id: 2, full_name: 'Test Planner' },
    ...overrides,
  }
}

export function makeDocumentDetail(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    ...makeDocument(),
    passage_count: 2,
    preview: [],
    sessions: [],
    is_nuc_core: false,
    ...overrides,
  }
}

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
