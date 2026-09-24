import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { authGuard } from '../../src/router'
import { ROLES, useAuthStore } from '../../src/stores/auth'

describe('auth store and route guard', () => {
  let auth
  beforeEach(() => {
    setActivePinia(createPinia())
    auth = useAuthStore()
    auth.checked = true
  })

  it('applies the owner-or-admin review rule', () => {
    const session = { user_id: 7 }
    auth.user = { user_id: 7, role: ROLES.PLANNER }
    expect(auth.canReview(session)).toBe(true)
    auth.user = { user_id: 8, role: ROLES.PLANNER }
    expect(auth.canReview(session)).toBe(false)
    auth.user = { user_id: 8, role: ROLES.ADMIN }
    expect(auth.canReview(session)).toBe(true)
    auth.user = { user_id: 7, role: ROLES.VIEWER }
    expect(auth.canReview(session)).toBe(false)
    expect(auth.canWrite).toBe(false)
  })

  it('redirects anonymous users to login with the target page', async () => {
    expect(await authGuard({ meta: {}, fullPath: '/sessions/3' }, auth)).toEqual({ name: 'login', query: { next: '/sessions/3' } })
  })

  it('keeps non-admins out of admin pages and signed-in users off the login page', async () => {
    auth.user = { user_id: 1, role: ROLES.PLANNER }
    expect(await authGuard({ meta: { roles: ['Admin'] } }, auth)).toEqual({ name: 'dashboard' })
    expect(await authGuard({ meta: { public: true }, name: 'login' }, auth)).toEqual({ name: 'dashboard' })
    expect(await authGuard({ meta: {} }, auth)).toBe(true)
    auth.user.role = ROLES.ADMIN
    expect(await authGuard({ meta: { roles: ['Admin'] } }, auth)).toBe(true)
  })
})
