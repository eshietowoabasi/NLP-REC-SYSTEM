import { createContext } from 'react'

import type { User } from '@/types/api'

/**
 * The signed-in user, provided by <RequireAuth>. Components below it read the user from
 * here rather than from the query cache, so when the session ends (cache set to null) they
 * are unmounted by the redirect instead of re-rendering without a user.
 */
export const AuthUserContext = createContext<User | null>(null)
