import { use } from 'react'

import { canEdit } from '@/lib/roles'
import type { User, UserRole } from '@/types/api'

import { AuthUserContext } from './context'

export interface AuthState {
  user: User
  isAdmin: boolean
  /** Admins and planners can create and change data; viewers are read-only. */
  canEdit: boolean
  hasRole: (...roles: UserRole[]) => boolean
}

/**
 * The signed-in user and role helpers. Only use below <RequireAuth>, which guarantees a
 * user is present. Role checks here only hide controls; the API enforces permissions.
 */
export function useAuth(): AuthState {
  const user = use(AuthUserContext)
  if (!user) throw new Error('useAuth must be used inside <RequireAuth>')
  return {
    user,
    isAdmin: user.role === 'admin',
    canEdit: canEdit(user.role),
    hasRole: (...roles) => roles.includes(user.role),
  }
}
